import Foundation
import Observation

/// The voice state machine:
///
///     idle ─"Hey Nova"→ listening ─turn end→ thinking ─audio→ speaking
///       ↑                  ↑                                    │
///       │                  └──────── reply played (follow-up) ──┘
///       └── follow_up_stopped / no_speech / listen timeout / error
///
/// A port of the parts of the web client's useNovaRuntime.ts that a screenless
/// client needs. While idle every utterance is captured locally (a "sentry"
/// capture) and only sent once the wake detector hears it open with
/// "Hey Nova", so the request said in the same breath is not lost. While Nova
/// is speaking the same happens, and a wake there is a barge-in: playback stops
/// and the late audio of the interrupted reply is dropped.
///
/// Everything audio- or network-shaped arrives through the ports in Ports.swift,
/// and the microphone arrives through `ingest(frame:at:)`.
@MainActor
@Observable
final class ConversationController {
    enum Phase: String, Equatable, Sendable {
        /// Listening is switched off.
        case off
        /// Waiting for "Hey Nova".
        case idle
        /// Woken: the next utterance is a request.
        case listening
        /// The request went to the server.
        case thinking
        /// Nova's reply is playing.
        case speaking
    }

    // MARK: Tunables (mirrors useNovaRuntime.ts where one exists)

    /// After an utterance ends, how long a late wake result may still promote it.
    static let wakeGraceSeconds = 0.9
    /// Woken (or done replying) with nothing said: stand down after this long.
    static let listenTimeoutSeconds = 8.0
    /// A request waiting for the socket gives up after this long.
    static let socketWaitSeconds = 8.0
    /// No answer at all from the server: stop waiting.
    static let thinkingTimeoutSeconds = 90.0
    /// Live audio goes out in pieces about this long.
    static let sendBatchMs = 200.0
    /// Held audio is sent in pieces no larger than this.
    static let maxMessageBytes = 32_000
    /// How long `stop` waits for a photo still on its way up.
    static let photoWaitSeconds: Double = 3

    // MARK: Observable state for the UI

    private(set) var phase: Phase = .off
    private(set) var connection: SocketConnectionState = .disconnected
    private(set) var statusMessage = "Off."
    private(set) var partialTranscript = ""
    private(set) var lastTranscript = ""
    private(set) var lastReply = ""
    private(set) var userSpeaking = false

    /// The server rejected our token; the app should show the login screen.
    var onUnauthorized: (() -> Void)?

    // MARK: Collaborators

    @ObservationIgnored private let socket: NovaSocketing
    @ObservationIgnored private let player: SpeechPlaying
    @ObservationIgnored private let earcons: EarconPlaying
    @ObservationIgnored private let wake: WakeDetecting
    @ObservationIgnored private let scheduler: Scheduling
    @ObservationIgnored private let conversationIds: ConversationIdStore
    @ObservationIgnored private let camera: GlassesCamera?
    @ObservationIgnored private let vision: VisionUploading?
    @ObservationIgnored let detector = TurnDetector()

    // MARK: Capture state

    private final class Capture {
        let purpose: CapturePurpose
        /// Audio stays on the phone (a sentry capture before the wake, or any
        /// capture while the socket is down).
        var held = true
        var heldData = Data()
        var promoted = false
        var discarded = false
        var utteranceEnded = false
        /// A stop was requested while still held; send it on delivery.
        var pendingStop = false
        var batch = Data()
        /// The glasses photo for this turn, taken when the caption asked to look.
        var photo: PhotoSlot?

        init(purpose: CapturePurpose) {
            self.purpose = purpose
        }
    }

    @MainActor
    private final class Once {
        private var done = false

        func run(_ body: () -> Void) {
            guard !done else { return }
            done = true
            body()
        }
    }

    /// A photo on its way to the server. `stop` waits for it, briefly.
    private final class PhotoSlot {
        var finished = false
        var imageId: String?
        var onFinish: (() -> Void)?

        func finish(_ imageId: String?) {
            guard !finished else { return }
            finished = true
            self.imageId = imageId
            onFinish?()
            onFinish = nil
        }
    }

    @ObservationIgnored private var capture: Capture?
    /// A promoted capture waiting for the socket to (re)open.
    @ObservationIgnored private var awaitingSocket: Capture?
    @ObservationIgnored private var preRoll = PreRollBuffer()
    @ObservationIgnored private var smoother = LevelSmoother()
    @ObservationIgnored private var wakeUtteranceOpen = false
    /// Drop the interrupted reply's late events until the server acknowledges
    /// our next `start` with `listening` (events are processed in order, so
    /// anything before that ack belongs to the old turn).
    @ObservationIgnored private var suppressAssistantAudio = false
    @ObservationIgnored private var awaitingListeningAck = false
    @ObservationIgnored private var pendingFollowUp = false
    /// The socket dropped mid-reply: once what already arrived has played, stand down.
    @ObservationIgnored private var turnLost = false

    @ObservationIgnored private var wakeGraceTimer: Cancellable?
    @ObservationIgnored private var listenTimer: Cancellable?
    @ObservationIgnored private var socketWaitTimer: Cancellable?
    @ObservationIgnored private var thinkingTimer: Cancellable?

    init(
        socket: NovaSocketing,
        player: SpeechPlaying,
        earcons: EarconPlaying,
        wake: WakeDetecting,
        scheduler: Scheduling,
        conversationIds: ConversationIdStore,
        camera: GlassesCamera? = nil,
        vision: VisionUploading? = nil
    ) {
        self.socket = socket
        self.player = player
        self.earcons = earcons
        self.wake = wake
        self.scheduler = scheduler
        self.conversationIds = conversationIds
        self.camera = camera
        self.vision = vision

        socket.onEvent = { [weak self] event in self?.handle(event) }
        socket.onStateChange = { [weak self] state in self?.handleConnection(state) }
        player.onDrained = { [weak self] in self?.playbackDrained() }
        wake.onWake = { [weak self] in self?.handleWake() }

        detector.onSpeechOnset = { [weak self] in self?.speechOnset() }
        detector.onSpeechStart = { [weak self] in self?.speechOnset() }
        detector.onSpeechAbort = { [weak self] in self?.speechAbort() }
        detector.onSpeechPause = { [weak self] in self?.speechPause() }
        detector.onSpeechResume = { [weak self] in self?.speechResume() }
        detector.onTurnEnd = { [weak self] _ in self?.turnEnd() }
        detector.onSpeakingChange = { [weak self] speaking in self?.userSpeaking = speaking }
    }

    // MARK: - Power

    var isEnabled: Bool { phase != .off }

    func setEnabled(_ enabled: Bool) {
        if enabled {
            guard phase == .off else { return }
            setPhase(.idle, "Say \"Hey Nova\".")
            socket.connect()
        } else {
            guard phase != .off else { return }
            dropCapture(sendAbort: true)
            discardAwaitingSocket()
            wake.cancel()
            wakeUtteranceOpen = false
            player.stopAll()
            pendingFollowUp = false
            cancelTimers()
            detector.reset()
            setPhase(.off, "Off.")
            socket.disconnect()
        }
    }

    // MARK: - Microphone

    /// One frame of microphone audio: 16 kHz mono Int16 PCM. `now` in ms on a
    /// monotonic clock.
    func ingest(frame: Data, at now: Double) {
        guard phase != .off else { return }
        let level = smoother.apply(rms: PCMFormat.rms(frame), now: now)
        // Onset handlers seed a new capture from the pre-roll, which must not
        // yet contain this frame; the frame is appended right after.
        detector.push(level: level, now: now)
        preRoll.append(frame)
        if let capture, !capture.discarded {
            append(frame, to: capture)
        }
        if wakeUtteranceOpen {
            wake.feed(frame)
        }
    }

    // MARK: - Turn detector handlers

    /// Phases where an utterance might be "Hey Nova": waiting, or talking over Nova.
    private var wakeWatching: Bool { phase == .idle || phase == .speaking }

    private func speechOnset() {
        if wakeWatching {
            if capture == nil {
                startCapture(.sentry)
            }
            if !wakeUtteranceOpen {
                wakeUtteranceOpen = true
                wake.beginUtterance(seed: preRoll.snapshot())
            }
            return
        }
        guard phase == .listening else { return }
        listenTimer?.cancel()
        if capture == nil {
            startCapture(.turn)
        }
    }

    private func speechAbort() {
        if let capture, capture.purpose == .sentry, !capture.promoted {
            discardSentryCapture()
            return
        }
        abortCapture()
        if phase == .listening {
            armListenTimeout(cue: .cancel)
        }
    }

    private func speechPause() {
        guard phase == .listening, let capture, isLive(capture) else { return }
        // The server starts transcribing on the chunk that follows the pause,
        // so the work happens during the silence window.
        socket.send(.speechPause)
        flushBatch(capture)
    }

    private func speechResume() {
        guard phase == .listening, let capture, isLive(capture) else { return }
        socket.send(.speechResume)
    }

    private func turnEnd() {
        if let capture, capture.purpose == .sentry, !capture.promoted {
            // Over before the recognizer ruled: give a late result a moment.
            capture.utteranceEnded = true
            if wakeUtteranceOpen {
                wake.endUtterance()
            }
            wakeGraceTimer?.cancel()
            wakeGraceTimer = scheduler.after(Self.wakeGraceSeconds) { [weak self] in
                self?.discardSentryCapture()
            }
            return
        }
        guard phase == .listening, let capture, capture.promoted, !capture.discarded else { return }
        earcons.play(.thinking)
        setPhase(.thinking, "Thinking…")
        armThinkingTimeout()
        stopCapture()
    }

    // MARK: - Wake

    private func handleWake() {
        wakeUtteranceOpen = false
        wake.cancel()
        switch phase {
        case .speaking:
            bargeIn()
        case .idle:
            earcons.play(.wake)
            promoteSentryOrListen()
        default:
            break
        }
    }

    /// Promote the utterance that held the wake phrase, or (if the detector
    /// missed its start) just listen for the request.
    private func promoteSentryOrListen() {
        wakeGraceTimer?.cancel()
        if let capture, capture.purpose == .sentry, !capture.promoted, !capture.discarded {
            setPhase(.listening, "Listening…")
            promote(capture)
            if capture.utteranceEnded {
                // "Hey Nova." and a pause, before the recognizer caught up.
                earcons.play(.thinking)
                setPhase(.thinking, "Thinking…")
                armThinkingTimeout()
                stopCapture()
            }
            return
        }
        setPhase(.listening, "Listening…")
        armListenTimeout(cue: .cancel)
        if !socket.isOpen {
            socket.connect()
        }
    }

    /// "Hey Nova" while Nova is talking: stop her, drop the rest of the reply,
    /// and take the new request. Client-side only, like the web's
    /// triggerWakeBargeIn — the server finishes the old turn regardless.
    private func bargeIn() {
        earcons.play(.wake)
        suppressAssistantAudio = true
        awaitingListeningAck = false
        pendingFollowUp = false
        thinkingTimer?.cancel()
        player.stopAll()
        promoteSentryOrListen()
    }

    // MARK: - Capture

    private func isLive(_ capture: Capture) -> Bool {
        !capture.discarded && capture.promoted
    }

    private func startCapture(_ purpose: CapturePurpose) {
        let capture = Capture(purpose: purpose)
        capture.heldData = preRoll.snapshot()
        self.capture = capture
        if purpose == .turn {
            promote(capture)
        }
    }

    private func append(_ frame: Data, to capture: Capture) {
        if capture.held {
            capture.heldData.append(frame)
            return
        }
        capture.batch.append(frame)
        if capture.batch.count >= PCMFormat.bytes(forMs: Self.sendBatchMs) {
            flushBatch(capture)
        }
    }

    private func flushBatch(_ capture: Capture) {
        guard !capture.held, !capture.batch.isEmpty else { return }
        socket.sendAudio(capture.batch)
        capture.batch = Data()
    }

    /// Tell the server about a capture: `start`, then everything held so far.
    /// Waits for the socket if it is down.
    private func promote(_ capture: Capture) {
        guard !capture.promoted, !capture.discarded else { return }
        capture.promoted = true
        partialTranscript = ""
        if socket.isOpen {
            deliver(capture)
        } else {
            awaitingSocket = capture
            socketWaitTimer?.cancel()
            socketWaitTimer = scheduler.after(Self.socketWaitSeconds) { [weak self] in
                self?.abandonAwaitingSocket()
            }
            socket.connect()
        }
    }

    private func deliver(_ capture: Capture) {
        guard capture.held, !capture.discarded else { return }
        if awaitingSocket === capture {
            awaitingSocket = nil
            socketWaitTimer?.cancel()
        }
        // A new turn: the interrupted reply's audio is fair game to drop until
        // the server acknowledges this start.
        if suppressAssistantAudio {
            awaitingListeningAck = true
        }
        socket.send(.start(StartEvent(purpose: capture.purpose, conversationId: conversationIds.load())))
        let held = capture.heldData
        var offset = held.startIndex
        while offset < held.endIndex {
            let end = min(held.endIndex, offset + Self.maxMessageBytes)
            socket.sendAudio(Data(held[offset..<end]))
            offset = end
        }
        capture.heldData = Data()
        capture.held = false
        if capture.pendingStop {
            sendStop(capture)
        }
    }

    /// The utterance is over: send it for an answer.
    private func stopCapture() {
        guard let capture else { return }
        self.capture = nil
        if capture.held {
            // Still waiting on the socket; the stop goes out on delivery.
            capture.pendingStop = true
            return
        }
        flushBatch(capture)
        sendStop(capture)
    }

    /// `stop`, carrying the turn's photo. A photo still uploading gets up to
    /// `photoWaitSeconds`; after that the turn goes without it (Nova can
    /// still look for itself).
    private func sendStop(_ capture: Capture) {
        let purpose = capture.purpose
        guard let photo = capture.photo, !photo.finished else {
            emitStop(purpose, imageId: capture.photo?.imageId)
            return
        }
        // Whichever comes first, the photo or the deadline, sends the stop.
        let once = Once()
        let timer = scheduler.after(Self.photoWaitSeconds) { [weak self] in
            once.run {
                AudioLog.shared.add("Photo not ready in time; sending the turn without it")
                self?.emitStop(purpose, imageId: nil)
            }
        }
        photo.onFinish = { [weak self, weak photo] in
            timer.cancel()
            once.run { self?.emitStop(purpose, imageId: photo?.imageId) }
        }
    }

    private func emitStop(_ purpose: CapturePurpose, imageId: String?) {
        socket.send(.stop(
            purpose: purpose,
            conversationId: conversationIds.load(),
            imageIds: imageId.map { [$0] } ?? []
        ))
    }

    // MARK: - Vision

    /// The caption asks to look: take the photo now, while the user is still
    /// talking, so it is on the server by the time the turn ends.
    private func maybeTakePhoto(for caption: String) {
        guard let capture, capture.photo == nil, let camera, let vision,
              camera.state.canCapture, VisionIntent.wantsToSee(caption) else { return }
        let slot = PhotoSlot()
        capture.photo = slot
        Task { @MainActor [weak self] in
            do {
                let jpeg = try await camera.capturePhoto()
                self?.earcons.play(.shutter)
                slot.finish(try await vision.upload(jpeg, requestId: nil))
            } catch {
                AudioLog.shared.add("Photo for the turn failed: \(error.localizedDescription)")
                slot.finish(nil)
            }
        }
    }

    /// Nova's `look` tool asked for a photo mid-turn.
    private func serveCaptureRequest(_ requestId: String) {
        guard let vision else { return }
        guard let camera, camera.state.canCapture else {
            Task { await vision.reportCaptureFailed(requestId: requestId, reason: "The glasses camera isn't connected.") }
            return
        }
        Task { @MainActor [weak self] in
            do {
                let jpeg = try await camera.capturePhoto()
                self?.earcons.play(.shutter)
                _ = try await vision.upload(jpeg, requestId: requestId)
            } catch {
                await vision.reportCaptureFailed(requestId: requestId, reason: error.localizedDescription)
            }
        }
    }

    /// A click, not speech: tell the server to drop what it buffered.
    private func abortCapture() {
        dropCapture(sendAbort: true)
    }

    private func dropCapture(sendAbort: Bool) {
        guard let capture else { return }
        self.capture = nil
        let wasSent = capture.promoted && !capture.held
        capture.discarded = true
        if awaitingSocket === capture {
            discardAwaitingSocket()
        }
        if sendAbort && wasSent {
            socket.send(.abort)
        }
    }

    /// Forget a sentry utterance that never woke anything. Nothing was sent.
    private func discardSentryCapture() {
        wakeGraceTimer?.cancel()
        if let capture, capture.purpose == .sentry, !capture.promoted {
            capture.discarded = true
            self.capture = nil
        }
        if wakeUtteranceOpen {
            wakeUtteranceOpen = false
            wake.cancel()
        }
    }

    private func discardAwaitingSocket() {
        awaitingSocket?.discarded = true
        awaitingSocket = nil
        socketWaitTimer?.cancel()
    }

    /// The socket never came back for this request: stand down audibly.
    private func abandonAwaitingSocket() {
        guard let pending = awaitingSocket else { return }
        pending.discarded = true
        awaitingSocket = nil
        if capture === pending {
            capture = nil
        }
        goIdle(cue: .error, message: "Couldn't reach Nova.")
    }

    // MARK: - Timers

    private func armListenTimeout(cue: Earcon) {
        listenTimer?.cancel()
        listenTimer = scheduler.after(Self.listenTimeoutSeconds) { [weak self] in
            guard let self, self.phase == .listening, self.capture == nil else { return }
            self.goIdle(cue: cue)
        }
    }

    private func armThinkingTimeout() {
        thinkingTimer?.cancel()
        thinkingTimer = scheduler.after(Self.thinkingTimeoutSeconds) { [weak self] in
            guard let self, self.phase == .thinking else { return }
            self.goIdle(cue: .error, message: "Nova didn't answer.")
        }
    }

    private func cancelTimers() {
        wakeGraceTimer?.cancel()
        listenTimer?.cancel()
        socketWaitTimer?.cancel()
        thinkingTimer?.cancel()
    }

    // MARK: - Phase

    private func setPhase(_ phase: Phase, _ message: String) {
        self.phase = phase
        statusMessage = message
    }

    private func goIdle(cue: Earcon?, message: String = "Say \"Hey Nova\".") {
        guard phase != .off else { return }
        if let capture, capture.promoted {
            // A request in progress is abandoned; a sentry utterance is kept.
            dropCapture(sendAbort: true)
        }
        listenTimer?.cancel()
        thinkingTimer?.cancel()
        pendingFollowUp = false
        turnLost = false
        partialTranscript = ""
        if let cue {
            earcons.play(cue)
        }
        setPhase(.idle, message)
    }

    private func playbackDrained() {
        if turnLost {
            goIdle(cue: .error, message: "Connection lost.")
            return
        }
        guard pendingFollowUp else { return }
        pendingFollowUp = false
        // Conversation continues: listen for a follow-up, but not forever.
        guard phase == .speaking || phase == .thinking else { return }
        setPhase(.listening, "Listening for a follow-up…")
        armListenTimeout(cue: .done)
    }

    // MARK: - Socket

    private func handleConnection(_ state: SocketConnectionState) {
        connection = state
        switch state {
        case .connected:
            if let pending = awaitingSocket {
                deliver(pending)
            }
        case .unauthorized:
            setEnabled(false)
            statusMessage = "Signed out. Log in again."
            onUnauthorized?()
        case .disconnected:
            // A request or reply in flight is lost with the socket. (A capture
            // still held on the phone survives: it waits for the reconnect.)
            if let capture, capture.promoted, !capture.held {
                dropCapture(sendAbort: false)
                goIdle(cue: .error, message: "Connection lost.")
            } else if phase == .thinking {
                goIdle(cue: .error, message: "Connection lost.")
            } else if phase == .speaking, !pendingFollowUp {
                if player.isBusy {
                    turnLost = true
                } else {
                    goIdle(cue: .error, message: "Connection lost.")
                }
            }
        case .connecting:
            break
        }
    }

    func handle(_ event: ServerEvent) {
        guard phase != .off else { return }
        switch event {
        case .ready, .pong, .chunkReceived, .other:
            break

        case .listening(_, let endpointMs):
            if awaitingListeningAck {
                awaitingListeningAck = false
                suppressAssistantAudio = false
            }
            if let endpointMs, let capture, isLive(capture) {
                detector.setSilenceWindow(endpointMs)
            }

        case .partialTranscript(let text, _, let endpointMs):
            guard phase == .listening else { return }
            partialTranscript = text
            if let endpointMs {
                detector.setSilenceWindow(endpointMs)
            }
            maybeTakePhoto(for: text)

        case .captureRequest(let requestId, _):
            serveCaptureRequest(requestId)

        case .userTranscript(let text, let conversationId):
            conversationIds.save(conversationId)
            partialTranscript = ""
            lastTranscript = text
            lastReply = ""

        case .speechText(let text, _, let conversationId):
            guard !suppressAssistantAudio else { return }
            conversationIds.save(conversationId)
            lastReply = lastReply.isEmpty ? text : "\(lastReply) \(text)"

        case .audioStreamStart(let streamId, _, _):
            guard !suppressAssistantAudio, phase == .thinking || phase == .speaking else { return }
            player.beginStream(streamId)
            if phase == .thinking {
                thinkingTimer?.cancel()
                setPhase(.speaking, "Speaking…")
            }

        case .audioStreamChunk(let streamId, let chunkBase64, _):
            guard !suppressAssistantAudio, let data = Data(base64Encoded: chunkBase64) else { return }
            player.appendChunk(streamId, data: data)

        case .audioStreamEnd(let streamId):
            guard !suppressAssistantAudio else { return }
            player.endStream(streamId)

        case .done(_, let conversationId, _):
            guard !suppressAssistantAudio else { return }
            conversationIds.save(conversationId)
            thinkingTimer?.cancel()
            pendingFollowUp = true
            if phase == .thinking {
                // A reply with nothing spoken still ends the turn.
                setPhase(.speaking, "Speaking…")
            }
            if !player.isBusy {
                playbackDrained()
            }

        case .wakeOnly:
            // "Hey Nova" on its own: the chime already played, take the request.
            partialTranscript = ""
            thinkingTimer?.cancel()
            setPhase(.listening, "Listening…")
            armListenTimeout(cue: .cancel)

        case .wakeNotDetected, .noSpeech:
            goIdle(cue: .cancel)

        case .followUpStopped:
            goIdle(cue: .done)

        case .meetingMode(let message):
            goIdle(cue: .cancel, message: message)

        case .error(let message, let code):
            if code == "conversation_closed" || message.contains("Invalid conversationId") {
                conversationIds.clear()
            }
            dropCapture(sendAbort: false)
            goIdle(cue: .error, message: message)
        }
    }
}
