@preconcurrency import AVFoundation
import Foundation

/// The one AVAudioEngine the app runs: the microphone tap (converted to the
/// 16 kHz mono Int16 the server takes) and the player nodes for Nova's voice
/// and the earcons. Playing on the same engine as the capture keeps the
/// session in HFP instead of bouncing the glasses between HFP and A2DP.
@MainActor
final class CaptureEngine {
    /// The format Nova's voice and the earcons are rendered in. The main mixer
    /// converts it to whatever the output (8/16 kHz HFP) runs at.
    nonisolated(unsafe) static let playbackFormat = AVAudioFormat(standardFormatWithSampleRate: 24_000, channels: 1)!

    /// One frame of 16 kHz mono Int16 PCM and its capture time in ms
    /// (monotonic). Delivered on the main actor, in order.
    var onFrame: (@MainActor (Data, Double) -> Void)?

    let engine = AVAudioEngine()
    private(set) var isRunning = false
    private var attachedPlayers: [AVAudioPlayerNode] = []
    private var configObserver: NSObjectProtocol?

    init() {
        configObserver = NotificationCenter.default.addObserver(
            forName: .AVAudioEngineConfigurationChange, object: engine, queue: .main
        ) { [weak self] _ in
            // The route (and so the input format) changed under the engine,
            // which stops it. Rebuild the tap for the new format and go on.
            MainActor.assumeIsolated {
                guard let self, self.isRunning else { return }
                self.isRunning = false
                try? self.start()
            }
        }
    }

    /// Attach a player node that renders `playbackFormat`. Call before `start()`.
    func attach(_ player: AVAudioPlayerNode) {
        engine.attach(player)
        engine.connect(player, to: engine.mainMixerNode, format: Self.playbackFormat)
        attachedPlayers.append(player)
    }

    func start() throws {
        guard !isRunning else { return }
        let input = engine.inputNode
        // Echo cancellation, so Nova's voice from the speaker is not heard as
        // the user. Harmless over HFP, where the headset does its own.
        if !input.isVoiceProcessingEnabled {
            try? input.setVoiceProcessingEnabled(true)
        }
        input.removeTap(onBus: 0)
        let inputFormat = input.outputFormat(forBus: 0)
        guard inputFormat.sampleRate > 0, inputFormat.channelCount > 0 else {
            throw NSError(domain: "NovaGlasses", code: 1, userInfo: [
                NSLocalizedDescriptionKey: "No microphone input is available.",
            ])
        }
        let converter = FrameConverter(input: inputFormat)
        let deliver = onFrame
        // @Sendable: this runs on the audio thread, and a closure formed in a
        // main-actor method would otherwise assert it is on the main thread.
        input.installTap(onBus: 0, bufferSize: 1024, format: inputFormat) { @Sendable buffer, _ in
            let now = ProcessInfo.processInfo.systemUptime * 1000
            guard let frame = converter.convert(buffer), !frame.isEmpty else { return }
            DispatchQueue.main.async {
                MainActor.assumeIsolated { deliver?(frame, now) }
            }
        }
        engine.prepare()
        try engine.start()
        for player in attachedPlayers {
            player.play()
        }
        isRunning = true
    }

    func stop() {
        guard isRunning else { return }
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        isRunning = false
    }
}

/// Converts tap buffers (whatever the route gives: 8 kHz HFP, 48 kHz built-in)
/// to 16 kHz mono Int16. Used only on the audio thread, one buffer at a time.
final class FrameConverter: @unchecked Sendable {
    let output = AVAudioFormat(
        commonFormat: .pcmFormatInt16, sampleRate: PCMFormat.sampleRate, channels: 1, interleaved: true
    )!
    private let converter: AVAudioConverter?

    init(input: AVAudioFormat) {
        converter = AVAudioConverter(from: input, to: output)
        // Voice processing can hand over several channels; take the first.
        if input.channelCount > 1 {
            converter?.channelMap = [0]
        }
    }

    func convert(_ buffer: AVAudioPCMBuffer) -> Data? {
        guard let converter, buffer.frameLength > 0 else { return nil }
        let ratio = output.sampleRate / buffer.format.sampleRate
        let capacity = AVAudioFrameCount(Double(buffer.frameLength) * ratio) + 64
        guard let out = AVAudioPCMBuffer(pcmFormat: output, frameCapacity: capacity) else { return nil }
        var consumed = false
        var error: NSError?
        let status = converter.convert(to: out, error: &error) { _, inputStatus in
            if consumed {
                inputStatus.pointee = .noDataNow
                return nil
            }
            consumed = true
            inputStatus.pointee = .haveData
            return buffer
        }
        guard status != .error, out.frameLength > 0, let samples = out.int16ChannelData else { return nil }
        return Data(bytes: samples[0], count: Int(out.frameLength) * PCMFormat.bytesPerSample)
    }
}
