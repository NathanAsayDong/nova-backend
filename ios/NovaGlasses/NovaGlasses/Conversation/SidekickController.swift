import Foundation
import Observation

/// Sidekick mode: Nova listens to everything around the glasses and chimes
/// in on its own when it has something worth saying.
///
/// Every utterance that was not for Nova (no "Hey Nova") goes, whole, to
/// /ws/sidekick, where the server keeps a rolling transcript and decides when
/// to speak. "Hey Nova" still works as usual through the main controller.
/// Interjections play through the shared speech player, but only while the
/// main conversation is idle: one arriving during a direct turn is dropped,
/// and "Hey Nova" during an interjection cuts it off.
@MainActor
@Observable
final class SidekickController {
    static let autoOffSeconds: Double = 60 * 60
    /// Utterances kept while the socket (re)connects; older ones are stale.
    static let maxQueued = 4

    private(set) var isOn = false
    private(set) var lastHeard = ""
    private(set) var lastRemark = ""
    /// Sidekick ended on its own: "be_quiet", "timeout", "error", or "stopped".
    var onEnded: ((String) -> Void)?

    @ObservationIgnored private let socket: NovaSocketing
    @ObservationIgnored private let player: SpeechPlaying
    @ObservationIgnored private let earcons: EarconPlaying
    @ObservationIgnored private let camera: GlassesCamera?
    @ObservationIgnored private let vision: VisionUploading?
    @ObservationIgnored private let scheduler: Scheduling
    @ObservationIgnored private let mainIsIdle: () -> Bool

    @ObservationIgnored private var conversationId: String?
    @ObservationIgnored private var started = false
    @ObservationIgnored private var queued: [Data] = []
    @ObservationIgnored private var autoOff: Cancellable?
    /// Streams of the interjection being played, and of ones dropped.
    @ObservationIgnored private var playing: Set<String> = []
    @ObservationIgnored private var dropped: Set<String> = []
    /// An interjection is under way (from its first audio to `done`).
    @ObservationIgnored private var speaking = false

    init(
        socket: NovaSocketing,
        player: SpeechPlaying,
        earcons: EarconPlaying,
        camera: GlassesCamera?,
        vision: VisionUploading?,
        scheduler: Scheduling,
        mainIsIdle: @escaping () -> Bool
    ) {
        self.socket = socket
        self.player = player
        self.earcons = earcons
        self.camera = camera
        self.vision = vision
        self.scheduler = scheduler
        self.mainIsIdle = mainIsIdle
        socket.onEvent = { [weak self] event in self?.handle(event) }
        socket.onStateChange = { [weak self] state in self?.connectionChanged(state) }
    }

    // MARK: - On and off

    func start() {
        guard !isOn else { return }
        isOn = true
        started = false
        lastHeard = ""
        lastRemark = ""
        earcons.play(.sidekickOn)
        AudioLog.shared.add("Sidekick on")
        autoOff = scheduler.after(Self.autoOffSeconds) { [weak self] in
            self?.socket.send(.sidekickStop)
            self?.finish("timeout")
        }
        socket.connect()
    }

    func stop() {
        guard isOn else { return }
        socket.send(.sidekickStop)
        finish("stopped")
    }

    private func finish(_ reason: String) {
        guard isOn else { return }
        isOn = false
        started = false
        queued.removeAll()
        autoOff?.cancel()
        autoOff = nil
        if speaking {
            player.stopAll()
        }
        speaking = false
        playing.removeAll()
        dropped.removeAll()
        socket.disconnect()
        earcons.play(.sidekickOff)
        AudioLog.shared.add("Sidekick off (\(reason))")
        onEnded?(reason)
    }

    // MARK: - From the main controller

    /// A finished utterance that was not for Nova.
    func ambient(_ pcm: Data) {
        guard isOn else { return }
        if started && socket.isOpen {
            send(pcm)
        } else {
            queued.append(pcm)
            if queued.count > Self.maxQueued {
                queued.removeFirst(queued.count - Self.maxQueued)
            }
        }
    }

    /// "Hey Nova": the user wants Nova directly, so stop talking over them.
    func userWoke() {
        guard isOn, speaking else { return }
        AudioLog.shared.add("Sidekick interrupted by \"Hey Nova\"")
        player.stopAll()
        dropped.formUnion(playing)
        playing.removeAll()
        speaking = false
        socket.send(.interrupted)
    }

    private func send(_ pcm: Data) {
        socket.send(.utteranceStart)
        var offset = pcm.startIndex
        while offset < pcm.endIndex {
            let end = min(pcm.endIndex, offset + ConversationController.maxMessageBytes)
            socket.sendAudio(Data(pcm[offset..<end]))
            offset = end
        }
        socket.send(.utteranceEnd)
    }

    // MARK: - Socket

    private func connectionChanged(_ state: SocketConnectionState) {
        switch state {
        case .connected:
            guard isOn else { return }
            started = false
            socket.send(.sidekickStart(conversationId: conversationId))
        case .unauthorized:
            finish("error")
        case .disconnected, .connecting:
            started = false
        }
    }

    func handle(_ event: ServerEvent) {
        guard isOn else { return }
        switch event {
        case .sidekickStarted(let id):
            conversationId = id
            started = true
            let backlog = queued
            queued.removeAll()
            backlog.forEach(send)

        case .heard(let text):
            lastHeard = text
            AudioLog.shared.add("Sidekick heard: \"\(text.prefix(120))\"")

        case .speechText(let text, _, _):
            guard speaking || mainIsIdle() else { return }
            lastRemark = lastRemark.isEmpty || !speaking ? text : "\(lastRemark) \(text)"

        case .audioStreamStart(let streamId, _, _):
            guard mainIsIdle(), !dropped.contains(streamId) else {
                // A direct turn is under way: never talk over it.
                dropped.insert(streamId)
                if !speaking {
                    socket.send(.interrupted)
                }
                return
            }
            if !speaking {
                speaking = true
                earcons.play(.sidekickCue)
            }
            playing.insert(streamId)
            player.beginStream(streamId)

        case .audioStreamChunk(let streamId, let chunkBase64, _):
            guard playing.contains(streamId), let data = Data(base64Encoded: chunkBase64) else { return }
            player.appendChunk(streamId, data: data)

        case .audioStreamEnd(let streamId):
            guard playing.remove(streamId) != nil else { return }
            player.endStream(streamId)

        case .done(_, _, let assistantText):
            speaking = false
            dropped.removeAll()
            AudioLog.shared.add("Sidekick said: \"\(assistantText.prefix(160))\"")

        case .silent:
            AudioLog.shared.add("Sidekick chose to stay quiet")

        case .captureRequest(let requestId, _):
            serveCaptureRequest(requestId)

        case .sidekickEnded(let reason):
            finish(reason)

        case .error(let message, _):
            AudioLog.shared.add("Sidekick error: \(message)")

        default:
            break
        }
    }

    private func serveCaptureRequest(_ requestId: String) {
        guard let vision else { return }
        guard let camera, camera.state.canCapture else {
            Task { await vision.reportCaptureFailed(requestId: requestId, reason: "The glasses camera isn't connected.") }
            return
        }
        AudioLog.shared.add("Sidekick wants to look (\(requestId))")
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
}
