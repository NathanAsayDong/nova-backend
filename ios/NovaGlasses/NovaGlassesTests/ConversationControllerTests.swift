import XCTest
@testable import NovaGlasses

// MARK: - Fakes

@MainActor
final class FakeSocket: NovaSocketing {
    var isOpen = true
    var onEvent: ((ServerEvent) -> Void)?
    var onStateChange: ((SocketConnectionState) -> Void)?
    var connectCalls = 0
    var disconnectCalls = 0
    /// Everything sent, in order: control events and audio byte counts.
    var log: [String] = []
    var events: [ClientEvent] = []
    var audio = Data()

    func connect() { connectCalls += 1 }
    func disconnect() { disconnectCalls += 1; isOpen = false }

    func send(_ event: ClientEvent) -> Bool {
        guard isOpen else { return false }
        events.append(event)
        log.append(event.name)
        return true
    }

    func sendAudio(_ data: Data) -> Bool {
        guard isOpen else { return false }
        audio.append(data)
        if log.last != "audio" { log.append("audio") }
        return true
    }

    func emit(_ event: ServerEvent) { onEvent?(event) }

    func open() {
        isOpen = true
        onStateChange?(.connected)
    }

    var starts: [StartEvent] {
        events.compactMap { if case .start(let s) = $0 { return s } else { return nil } }
    }
}

@MainActor
final class FakePlayer: SpeechPlaying {
    var onDrained: (() -> Void)?
    var active: Set<String> = []
    var ended: Set<String> = []
    var chunks: [String: Data] = [:]
    var stopAllCalls = 0
    var isBusy: Bool { !active.isEmpty }

    func beginStream(_ id: String) { active.insert(id) }
    func appendChunk(_ id: String, data: Data) { chunks[id, default: Data()].append(data) }
    func endStream(_ id: String) { ended.insert(id) }
    func stopAll() { stopAllCalls += 1; active.removeAll() }

    /// Everything ended has finished playing.
    func finishPlaying() {
        active.subtract(ended)
        if active.isEmpty { onDrained?() }
    }
}

@MainActor
final class FakeEarcons: EarconPlaying {
    var played: [Earcon] = []
    func play(_ earcon: Earcon) { played.append(earcon) }
}

@MainActor
final class FakeWake: WakeDetecting {
    var onWake: (() -> Void)?
    var onTranscript: ((String) -> Void)?
    var utterances = 0
    var seedBytes = 0
    var fedBytes = 0
    var ended = 0
    var cancels = 0
    func beginUtterance(seed: Data) { utterances += 1; seedBytes = seed.count; fedBytes = 0 }
    func feed(_ pcm: Data) { fedBytes += pcm.count }
    func endUtterance() { ended += 1 }
    func cancel() { cancels += 1 }
    func hear() { onWake?() }
    func caption(_ text: String) { onTranscript?(text) }
}

@MainActor
final class ManualScheduler: Scheduling {
    final class Item: Cancellable {
        let at: Double
        let block: @MainActor @Sendable () -> Void
        var cancelled = false
        init(at: Double, block: @escaping @MainActor @Sendable () -> Void) { self.at = at; self.block = block }
        func cancel() { cancelled = true }
    }

    var now: Double = 0
    var items: [Item] = []

    func after(_ seconds: Double, _ block: @escaping @MainActor @Sendable () -> Void) -> Cancellable {
        let item = Item(at: now + seconds, block: block)
        items.append(item)
        return item
    }

    func advance(_ seconds: Double) {
        let target = now + seconds
        while let next = items.filter({ !$0.cancelled && $0.at <= target }).min(by: { $0.at < $1.at }) {
            next.cancelled = true
            now = next.at
            next.block()
        }
        now = target
    }
}

// MARK: - Tests

@MainActor
final class ConversationControllerTests: XCTestCase {
    @MainActor
    final class Rig {
        let socket = FakeSocket()
        let player = FakePlayer()
        let earcons = FakeEarcons()
        let wake = FakeWake()
        let scheduler = ManualScheduler()
        let ids: ConversationIdStore
        let controller: ConversationController
        var ms: Double = 0
        /// Utterances forwarded to `onAmbientUtterance` (Sidekick, in the app).
        var ambientUtterances: [Data] = []

        init(camera: GlassesCamera? = nil, vision: VisionUploading? = nil) {
            let defaults = UserDefaults(suiteName: "test.\(UUID().uuidString)")!
            ids = ConversationIdStore(defaults: defaults)
            controller = ConversationController(
                socket: socket, player: player, earcons: earcons, wake: wake,
                scheduler: scheduler, conversationIds: ids,
                camera: camera, vision: vision
            )
            controller.onAmbientUtterance = { [weak self] pcm in self?.ambientUtterances.append(pcm) }
        }

        /// 20 ms frames of a 440 Hz tone at `amplitude` (0…1).
        func frame(amplitude: Double) -> Data {
            var data = Data(capacity: 640)
            for i in 0..<320 {
                let t = (ms + Double(i) / 16) / 1000
                let v = Int16(max(-32767, min(32767, amplitude * 32767 * sin(2 * .pi * 440 * t))))
                withUnsafeBytes(of: v.littleEndian) { data.append(contentsOf: $0) }
            }
            return data
        }

        func silence(_ duration: Double) {
            feed(duration) { _ in 0.0005 }
        }

        /// Speech-like: amplitude modulated at syllable rate.
        func speak(_ duration: Double) {
            feed(duration) { t in 0.1 + 0.05 * sin(2 * .pi * 5 * t / 1000) }
        }

        private func feed(_ duration: Double, amplitude: (Double) -> Double) {
            let end = ms + duration
            while ms < end {
                let data = frame(amplitude: amplitude(ms))
                ms += 20
                controller.ingest(frame: data, at: ms)
                // Keep scheduled timers on the same clock.
                scheduler.advance(0.02)
            }
        }

        /// Enabled, calibrated, waiting for the wake phrase.
        static func idle(camera: GlassesCamera? = nil, vision: VisionUploading? = nil) -> Rig {
            let rig = Rig(camera: camera, vision: vision)
            rig.controller.setEnabled(true)
            rig.silence(800)
            return rig
        }

        /// Woken and the request sent: waiting on the server.
        static func thinking() -> Rig {
            let rig = idle()
            rig.speak(600)
            rig.wake.hear()
            rig.speak(400)
            rig.silence(1500)
            return rig
        }

        /// Reply arriving and playing.
        static func speaking() -> Rig {
            let rig = thinking()
            rig.socket.emit(.userTranscript(text: "what time is it", conversationId: "conv-1"))
            rig.socket.emit(.speechText(text: "It's noon.", role: "final", conversationId: "conv-1"))
            rig.socket.emit(.audioStreamStart(streamId: "s1", mimeType: "audio/mpeg", role: .final))
            rig.socket.emit(.audioStreamChunk(streamId: "s1", chunkBase64: Data([1, 2, 3]).base64EncodedString(), seq: 0))
            return rig
        }
    }

    func testEnablingConnectsAndWaitsForTheWakePhrase() {
        let rig = Rig()
        XCTAssertEqual(rig.controller.phase, .off)
        rig.controller.setEnabled(true)
        XCTAssertEqual(rig.controller.phase, .idle)
        XCTAssertEqual(rig.socket.connectCalls, 1)
    }

    func testIdleSpeechIsHeldOnThePhoneAndOpensAWakeUtterance() {
        let rig = Rig.idle()
        rig.speak(500)
        XCTAssertEqual(rig.wake.utterances, 1)
        XCTAssertGreaterThan(rig.wake.seedBytes, 0, "seeded with the pre-roll")
        XCTAssertGreaterThan(rig.wake.fedBytes, 0)
        XCTAssertTrue(rig.socket.log.isEmpty, "nothing leaves the phone before the wake")
    }

    func testAnUtteranceWithoutTheWakePhraseIsForgotten() {
        let rig = Rig.idle()
        rig.speak(600)
        rig.silence(1500)
        XCTAssertEqual(rig.wake.ended, 1, "late results get a grace period")
        rig.silence(1000)
        XCTAssertGreaterThan(rig.wake.cancels, 0)
        XCTAssertTrue(rig.socket.log.isEmpty)
        XCTAssertEqual(rig.controller.phase, .idle)
        XCTAssertTrue(rig.earcons.played.isEmpty)
    }

    func testWakeMidUtterancePromotesItWithItsPreRoll() throws {
        let rig = Rig.idle()
        rig.speak(600)
        rig.wake.hear()
        XCTAssertEqual(rig.earcons.played, [.wake])
        XCTAssertEqual(rig.controller.phase, .listening)
        let start = try XCTUnwrap(rig.socket.starts.first)
        XCTAssertEqual(start.purpose, .sentry)
        XCTAssertEqual(start.client, "glasses")
        XCTAssertEqual(start.mimeType, "audio/pcm;rate=16000;channels=1")
        // The held audio: ~600 ms of speech plus up to 500 ms of pre-roll.
        XCTAssertGreaterThanOrEqual(rig.socket.audio.count, PCMFormat.bytes(forMs: 600))
        XCTAssertEqual(Array(rig.socket.log.prefix(2)), ["start", "audio"])

        rig.speak(400)
        rig.silence(1500)
        XCTAssertEqual(rig.controller.phase, .thinking)
        XCTAssertEqual(rig.earcons.played, [.wake, .thinking])
        XCTAssertEqual(rig.socket.log.filter { $0 != "audio" }, ["start", "speech_pause", "stop"])
        XCTAssertEqual(rig.socket.events.last, .stop(purpose: .sentry, conversationId: nil))
        // Everything after the wake went out live, and the total is the utterance.
        XCTAssertGreaterThanOrEqual(PCMFormat.durationMs(ofBytes: rig.socket.audio.count), 2000)
    }

    func testALateWakeGoesStraightToListeningThenSettlesToThinking() {
        let rig = Rig.idle()
        rig.speak(600)
        rig.silence(1500) // turn over, inside the grace period
        rig.wake.hear()
        // Straight to listening — no "thinking" flash — with the sentry
        // capture already sent and the mic still open for a continuation.
        XCTAssertEqual(rig.socket.log.filter { $0 != "audio" }, ["start"])
        XCTAssertEqual(rig.controller.phase, .listening)
        XCTAssertEqual(rig.earcons.played, [.wake])

        // Nothing more comes: once the settle window closes, the turn is
        // treated as request-only and sent off for a reply.
        rig.silence(ConversationController.wakeGraceSeconds * 1000 + 100)
        XCTAssertEqual(rig.socket.log.filter { $0 != "audio" }, ["start", "stop"])
        XCTAssertEqual(rig.controller.phase, .thinking)
        XCTAssertEqual(rig.earcons.played, [.wake, .thinking])
    }

    func testContinuingToTalkInTheSettleWindowKeepsTheSameTurnOpen() {
        let rig = Rig.idle()
        rig.speak(600)
        rig.silence(1500) // detector thought the utterance ended here
        rig.wake.hear() // the on-device recognizer only now confirms "Hey Nova"
        XCTAssertEqual(rig.controller.phase, .listening)

        // Nate keeps talking — a continuous thought — well inside the settle
        // window. The resumed speech must not be clipped or start a new turn.
        rig.silence(200)
        rig.speak(600)
        XCTAssertEqual(rig.controller.phase, .listening, "resumed speech cancels the settle timeout")

        rig.silence(1500)
        XCTAssertEqual(rig.controller.phase, .thinking)
        XCTAssertEqual(rig.socket.starts.count, 1, "one turn, not a second one after the pause")
        // The 200 ms silence inside the settle window is itself reported as a
        // live pause on the one ongoing turn; there is still only one "start".
        XCTAssertEqual(rig.socket.log.filter { $0 != "audio" }, ["start", "speech_pause", "stop"])
        // The whole utterance — "Hey Nova" and the continuation — went out.
        XCTAssertGreaterThanOrEqual(PCMFormat.durationMs(ofBytes: rig.socket.audio.count), 600 + 600)
    }

    func testWakeWithNoUtteranceListensThenStandsDown() {
        let rig = Rig.idle()
        rig.wake.hear()
        XCTAssertEqual(rig.controller.phase, .listening)
        rig.silence(ConversationController.listenTimeoutSeconds * 1000 + 100)
        XCTAssertEqual(rig.controller.phase, .idle)
        XCTAssertEqual(rig.earcons.played, [.wake, .cancel])
    }

    func testWakeOnlyListensForTheRequestAsATurn() {
        let rig = Rig.thinking()
        rig.socket.emit(.wakeOnly(message: "Listening for the request."))
        XCTAssertEqual(rig.controller.phase, .listening)
        rig.socket.events.removeAll()
        rig.speak(500)
        XCTAssertEqual(rig.socket.starts.first?.purpose, .turn, "a request after a bare wake is a plain turn")
        rig.silence(1500)
        XCTAssertEqual(rig.controller.phase, .thinking)
        XCTAssertEqual(rig.socket.events.last, .stop(purpose: .turn, conversationId: nil))
    }

    func testReplyPlaysThenListensForAFollowUp() {
        let rig = Rig.speaking()
        XCTAssertEqual(rig.controller.phase, .speaking)
        XCTAssertEqual(rig.controller.lastTranscript, "what time is it")
        XCTAssertEqual(rig.controller.lastReply, "It's noon.")
        XCTAssertEqual(rig.player.chunks["s1"], Data([1, 2, 3]))
        XCTAssertEqual(rig.ids.load(), "conv-1")

        rig.socket.emit(.audioStreamEnd(streamId: "s1"))
        rig.socket.emit(.done(message: "Done", conversationId: "conv-1", assistantText: "It's noon."))
        XCTAssertEqual(rig.controller.phase, .speaking, "waits for playback to finish")
        rig.player.finishPlaying()
        XCTAssertEqual(rig.controller.phase, .listening)

        // The follow-up reuses the conversation and is a plain turn.
        rig.socket.events.removeAll()
        rig.speak(500)
        XCTAssertEqual(rig.socket.starts.first?.purpose, .turn)
        XCTAssertEqual(rig.socket.starts.first?.conversationId, "conv-1")
    }

    func testFollowUpTimesOutBackToIdle() {
        let rig = Rig.speaking()
        rig.socket.emit(.audioStreamEnd(streamId: "s1"))
        rig.socket.emit(.done(message: "Done", conversationId: "conv-1", assistantText: ""))
        rig.player.finishPlaying()
        rig.silence(ConversationController.listenTimeoutSeconds * 1000 + 100)
        XCTAssertEqual(rig.controller.phase, .idle)
        XCTAssertEqual(rig.earcons.played.last, .done)
    }

    func testSidekickFollowUpOpensListeningThenSettlesQuietlyToIdle() {
        let rig = Rig.idle()
        rig.earcons.played.removeAll()
        rig.controller.expectSidekickFollowUp()
        XCTAssertEqual(rig.controller.phase, .listening)

        // Nobody answers: standing down is quiet — Sidekick's remark was
        // already the cue, a timeout earcon on top would be noise.
        rig.silence(ConversationController.sidekickFollowUpSeconds * 1000 + 100)
        XCTAssertEqual(rig.controller.phase, .idle)
        XCTAssertTrue(rig.earcons.played.isEmpty)
        XCTAssertTrue(rig.ambientUtterances.isEmpty)
        XCTAssertTrue(rig.socket.log.isEmpty, "never reaches the main conversation socket")
    }

    func testSpeakingInTheSidekickFollowUpWindowIsForwardedAsAmbient() {
        let rig = Rig.idle()
        rig.controller.expectSidekickFollowUp()
        XCTAssertEqual(rig.controller.phase, .listening)

        // "Yes" — well inside the window, no wake phrase.
        rig.speak(300)
        XCTAssertEqual(rig.controller.phase, .listening, "still listening while the answer is spoken")
        rig.silence(1500) // a real pause ends the utterance
        rig.silence(1000) // past wakeGraceSeconds: the grace timer flushes it

        XCTAssertEqual(rig.ambientUtterances.count, 1, "the answer reaches Sidekick")
        XCTAssertTrue(rig.socket.log.isEmpty, "never promoted as a direct-conversation turn")
        XCTAssertEqual(rig.controller.phase, .idle, "back to idle once the answer is handled")
    }

    func testSidekickFollowUpIsANoOpOutsideIdle() {
        let rig = Rig.thinking()
        rig.controller.expectSidekickFollowUp()
        XCTAssertEqual(rig.controller.phase, .thinking, "Sidekick never speaks over a direct conversation")
    }

    func testStopPhraseEndsTheConversation() {
        let rig = Rig.thinking()
        rig.socket.emit(.followUpStopped(message: "Okay."))
        XCTAssertEqual(rig.controller.phase, .idle)
        XCTAssertEqual(rig.earcons.played.last, .done)
    }

    func testNoSpeechAndWakeNotDetectedStandDownQuietly() {
        let a = Rig.thinking()
        a.socket.emit(.noSpeech(message: "No speech"))
        XCTAssertEqual(a.controller.phase, .idle)
        XCTAssertEqual(a.earcons.played.last, .cancel)

        let b = Rig.thinking()
        b.socket.emit(.wakeNotDetected(message: "No wake"))
        XCTAssertEqual(b.controller.phase, .idle)
        XCTAssertEqual(b.earcons.played.last, .cancel)
    }

    func testBargeInStopsPlaybackAndDropsTheOldReply() {
        let rig = Rig.speaking()
        rig.socket.events.removeAll()
        rig.speak(400)
        XCTAssertEqual(rig.wake.utterances, 2, "talking over Nova opens a wake utterance")
        XCTAssertTrue(rig.socket.events.isEmpty)

        rig.wake.hear()
        XCTAssertEqual(rig.player.stopAllCalls, 1)
        XCTAssertEqual(rig.earcons.played.last, .wake)
        XCTAssertEqual(rig.controller.phase, .listening)
        XCTAssertEqual(rig.socket.starts.first?.purpose, .sentry)

        // The interrupted turn's late audio and `done` are ignored…
        rig.socket.emit(.audioStreamChunk(streamId: "s1", chunkBase64: Data([9]).base64EncodedString(), seq: 1))
        rig.socket.emit(.audioStreamStart(streamId: "s2", mimeType: "audio/mpeg", role: .final))
        rig.socket.emit(.done(message: "Done", conversationId: "conv-1", assistantText: ""))
        XCTAssertEqual(rig.player.chunks["s1"], Data([1, 2, 3]))
        XCTAssertFalse(rig.player.active.contains("s2"))
        XCTAssertEqual(rig.controller.phase, .listening)

        // …until the server acknowledges the new start.
        rig.socket.emit(.listening(message: "Streaming", endpointMs: 1000))
        rig.speak(300)
        rig.silence(1500)
        XCTAssertEqual(rig.controller.phase, .thinking)
        rig.socket.emit(.audioStreamStart(streamId: "s3", mimeType: "audio/mpeg", role: .final))
        XCTAssertTrue(rig.player.active.contains("s3"))
        XCTAssertEqual(rig.controller.phase, .speaking)
    }

    func testThinkingIgnoresSpeech() {
        let rig = Rig.thinking()
        let sent = rig.socket.log
        rig.speak(500)
        rig.silence(1500)
        XCTAssertEqual(rig.socket.log, sent)
        XCTAssertEqual(rig.controller.phase, .thinking)
    }

    func testAClickWhileListeningIsAborted() {
        let rig = Rig.idle()
        rig.wake.hear()
        rig.feedClick()
        XCTAssertEqual(rig.socket.log.filter { $0 != "audio" }, ["start", "abort"])
        XCTAssertEqual(rig.controller.phase, .listening)
    }

    func testPartialTranscriptsDriveTheSilenceWindow() {
        let rig = Rig.idle()
        rig.wake.hear()
        rig.speak(300)
        rig.socket.emit(.partialTranscript(text: "what's the", seq: 1, endpointMs: 2500))
        XCTAssertEqual(rig.controller.partialTranscript, "what's the")
        rig.silence(1500)
        XCTAssertEqual(rig.controller.phase, .listening, "a dangling sentence gets patience")
        rig.silence(1500)
        XCTAssertEqual(rig.controller.phase, .thinking)
    }

    func testClosedConversationIsForgotten() {
        let rig = Rig.speaking()
        XCTAssertEqual(rig.ids.load(), "conv-1")
        rig.socket.emit(.error(message: "Conversation is closed.", code: "conversation_closed"))
        XCTAssertNil(rig.ids.load())
        XCTAssertEqual(rig.controller.phase, .idle)
        XCTAssertEqual(rig.earcons.played.last, .error)
    }

    func testARequestWaitsForTheSocketToReconnect() {
        let rig = Rig.idle()
        rig.socket.isOpen = false
        rig.speak(500)
        rig.wake.hear()
        XCTAssertTrue(rig.socket.log.isEmpty)
        XCTAssertEqual(rig.socket.connectCalls, 2)
        rig.speak(200)
        rig.silence(1500)
        XCTAssertEqual(rig.controller.phase, .thinking)
        rig.socket.open()
        XCTAssertEqual(rig.socket.log.filter { $0 != "audio" }, ["start", "stop"])
        XCTAssertGreaterThanOrEqual(PCMFormat.durationMs(ofBytes: rig.socket.audio.count), 700)
    }

    func testARequestGivesUpIfTheSocketNeverReturns() {
        let rig = Rig.idle()
        rig.socket.isOpen = false
        rig.speak(500)
        rig.wake.hear()
        rig.silence(ConversationController.socketWaitSeconds * 1000 + 100)
        XCTAssertEqual(rig.controller.phase, .idle)
        XCTAssertEqual(rig.earcons.played.last, .error)
        rig.socket.open()
        XCTAssertTrue(rig.socket.log.isEmpty, "an abandoned request is never sent late")
    }

    func testLosingTheSocketMidTurnStandsDown() {
        let rig = Rig.thinking()
        rig.socket.isOpen = false
        rig.socket.onStateChange?(.disconnected)
        XCTAssertEqual(rig.controller.phase, .idle)
        XCTAssertEqual(rig.earcons.played.last, .error)
    }

    func testUnauthorizedSwitchesOffAndAsksForALogin() {
        let rig = Rig.idle()
        var asked = false
        rig.controller.onUnauthorized = { asked = true }
        rig.socket.onStateChange?(.unauthorized)
        XCTAssertTrue(asked)
        XCTAssertEqual(rig.controller.phase, .off)
    }

    func testSwitchingOffStopsEverything() {
        let rig = Rig.speaking()
        rig.controller.setEnabled(false)
        XCTAssertEqual(rig.controller.phase, .off)
        XCTAssertEqual(rig.socket.disconnectCalls, 1)
        XCTAssertEqual(rig.player.stopAllCalls, 1)
        let sent = rig.socket.log
        rig.speak(500)
        XCTAssertEqual(rig.socket.log, sent, "the mic is ignored while off")
    }
}

extension ConversationControllerTests.Rig {
    /// A knock: above the open threshold for under the 120 ms onset hold.
    func feedClick() {
        // Short and soft enough that the smoothed level is back under the
        // close threshold before the onset hold confirms it.
        speakBurst(20, amplitude: 0.06)
        silence(200)
    }

    private func speakBurst(_ duration: Double, amplitude: Double) {
        let end = ms + duration
        while ms < end {
            let data = frame(amplitude: amplitude)
            ms += 20
            controller.ingest(frame: data, at: ms)
            scheduler.advance(0.02)
        }
    }
}
