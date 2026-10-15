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
    /// Buffers handed to the node that have not finished playing.
    private var outstanding = 0
    /// Bumped by `stopAll` so completions of dropped buffers are ignored.
    private var generation = 0

    var isBusy: Bool { !streams.isEmpty || outstanding > 0 }

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
        outstanding = 0
        node.stop()
        if node.engine?.isRunning == true {
            node.play()
        }
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
        guard !buffers.isEmpty, node.engine?.isRunning == true else { return }
        let generation = generation
        for buffer in buffers {
            outstanding += 1
            node.scheduleBuffer(buffer, completionCallbackType: .dataPlayedBack) { @Sendable [weak self] _ in
                DispatchQueue.main.async {
                    MainActor.assumeIsolated { self?.bufferPlayed(generation) }
                }
            }
        }
        if !node.isPlaying {
            node.play()
        }
    }

    private func bufferPlayed(_ generation: Int) {
        guard generation == self.generation else { return }
        outstanding = max(0, outstanding - 1)
        checkDrained()
    }

    private func checkDrained() {
        if !isBusy {
            onDrained?()
        }
    }
}
