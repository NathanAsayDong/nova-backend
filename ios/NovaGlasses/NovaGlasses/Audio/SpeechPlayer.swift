@preconcurrency import AVFoundation
import Foundation

/// Plays Nova's voice: the server's `assistant_audio_stream_*` events, each a
/// base64 MP3 stream, strictly in the order the streams started.
///
/// A stream's audio is decoded as it arrives and scheduled on the player node
/// once every earlier stream has been fully scheduled, so the node's own queue
/// keeps the order. Plays on the capture engine, never a separate
/// AVAudioPlayer, so the glasses stay in HFP.
@MainActor
final class SpeechPlayer: SpeechPlaying {
    let node = AVAudioPlayerNode()
    var onDrained: (() -> Void)?

    private final class Stream {
        let id: String
        let decoder = MP3StreamDecoder(outputFormat: CaptureEngine.playbackFormat)
        var ended = false
        var pending: [AVAudioPCMBuffer] = []

        init(id: String) {
            self.id = id
        }
    }

    /// Streams not yet fully scheduled, oldest first. Only the head schedules.
    private var streams: [Stream] = []
    /// Buffers handed to the node that have not finished playing, in order.
    /// Kept so they can be replayed if the engine restarts under them.
    private var inFlight: [(id: Int, buffer: AVAudioPCMBuffer)] = []
    /// Buffers decoded while the engine was down, played once it is back.
    private var held: [AVAudioPCMBuffer] = []
    private var nextBufferId = 0
    /// Bumped by `stopAll`/`engineRestarted` so stale completions are ignored.
    private var generation = 0
    private var watchdog = PlaybackWatchdog()
    private var watchdogTask: Task<Void, Never>?

    var isBusy: Bool { !streams.isEmpty || !inFlight.isEmpty || !held.isEmpty }

    func beginStream(_ streamId: String) {
        guard !streams.contains(where: { $0.id == streamId }) else { return }
        streams.append(Stream(id: streamId))
    }

    func appendChunk(_ streamId: String, data: Data) {
        guard let index = streams.firstIndex(where: { $0.id == streamId }) else { return }
        let stream = streams[index]
        let buffers = stream.decoder.decode(data)
        if index == 0 {
            schedule(buffers)
        } else {
            stream.pending.append(contentsOf: buffers)
        }
    }

    func endStream(_ streamId: String) {
        guard let stream = streams.first(where: { $0.id == streamId }) else { return }
        stream.ended = true
        pump()
    }

    func stopAll() {
        generation += 1
        streams.removeAll()
        inFlight.removeAll()
        held.removeAll()
        watchdogTask?.cancel()
        watchdogTask = nil
        node.stop()
        if node.engine?.isRunning == true {
            node.play()
        }
    }

    /// The engine stopped and started again (route change, interruption,
    /// media reset). Whatever was scheduled on the node is gone without its
    /// completions firing, so play it again from the buffer that was playing.
    func engineRestarted() {
        guard node.engine?.isRunning == true else { return }
        let replay = inFlight.map(\.buffer) + held
        generation += 1
        inFlight.removeAll()
        held.removeAll()
        node.stop()
        node.play()
        guard !replay.isEmpty else { return }
        AudioLog.shared.add("Replaying \(replay.count) buffer(s) after an engine restart")
        schedule(replay)
    }

    private func pump() {
        while let head = streams.first {
            schedule(head.pending)
            head.pending = []
            guard head.ended else { break }
            streams.removeFirst()
        }
        checkDrained()
    }

    private func schedule(_ buffers: [AVAudioPCMBuffer]) {
        guard !buffers.isEmpty else { return }
        guard node.engine?.isRunning == true else {
            held.append(contentsOf: buffers)
            armWatchdog()
            return
        }
        if inFlight.isEmpty {
            // Starting again after a gap (the next sentence arriving), which
            // is waiting on the server, not a stall.
            watchdog.progressed(at: Self.now)
        }
        let generation = generation
        for buffer in buffers {
            let id = nextBufferId
            nextBufferId += 1
            inFlight.append((id, buffer))
            node.scheduleBuffer(buffer, completionCallbackType: .dataPlayedBack) { @Sendable [weak self] _ in
                DispatchQueue.main.async {
                    MainActor.assumeIsolated { self?.bufferPlayed(id, generation) }
                }
            }
        }
        if !node.isPlaying {
            node.play()
        }
        armWatchdog()
    }

    private func bufferPlayed(_ id: Int, _ generation: Int) {
        guard generation == self.generation else { return }
        inFlight.removeAll { $0.id == id }
        watchdog.progressed(at: Self.now)
        checkDrained()
    }

    private func checkDrained() {
        if !isBusy {
            watchdogTask?.cancel()
            watchdogTask = nil
            onDrained?()
        }
    }

    // MARK: - Watchdog

    private static var now: Double { ProcessInfo.processInfo.systemUptime }

    private func armWatchdog() {
        guard watchdogTask == nil else { return }
        watchdog.progressed(at: Self.now)
        watchdogTask = Task { @MainActor [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                guard let self, !Task.isCancelled else { return }
                self.checkStall()
            }
        }
    }

    private func checkStall() {
        let head = inFlight.first?.buffer
        let headDuration = head.map { Double($0.frameLength) / $0.format.sampleRate } ?? 0
        let stalled = watchdog.isStalled(
            now: Self.now,
            waiting: !inFlight.isEmpty || !held.isEmpty,
            engineRunning: node.engine?.isRunning == true,
            headDuration: headDuration
        )
        guard stalled else { return }
        AudioLog.shared.add("Playback stalled; dropping the audio that was stuck")
        stopAll()
        onDrained?()
    }
}
