@preconcurrency import AVFoundation
import Foundation
import Speech

/// "Hey Nova" on the phone, with Apple's on-device recognizer.
///
/// One recognition task per utterance: the controller opens it at the turn
/// detector's onset, seeded with the pre-roll, so the transcript starts where
/// the utterance does and "opens with the wake phrase" means something. That
/// also keeps each task far below the recognizer's ~1 minute limit.
///
/// On-device only (`requiresOnDeviceRecognition`): idle audio never leaves the
/// phone. If the device has no on-device English model the detector reports
/// itself unavailable rather than falling back to Apple's servers.
@MainActor
final class SpeechWakeDetector: WakeDetecting {
    var onWake: (() -> Void)?

    private let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private let format = AVAudioFormat(
        commonFormat: .pcmFormatInt16, sampleRate: PCMFormat.sampleRate, channels: 1, interleaved: true
    )!
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?
    /// Bumped per utterance so a late result from an old task is ignored.
    private var generation = 0

    var isAvailable: Bool {
        guard let recognizer else { return false }
        return recognizer.isAvailable && recognizer.supportsOnDeviceRecognition
            && SFSpeechRecognizer.authorizationStatus() == .authorized
    }

    // nonisolated + @Sendable: TCC answers on a background queue, and a
    // closure formed in a main-actor method would assert it is on the main
    // thread and trap.
    nonisolated static func requestAuthorization() async -> Bool {
        await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { @Sendable status in
                continuation.resume(returning: status == .authorized)
            }
        }
    }

    func beginUtterance(seed: Data) {
        cancel()
        guard isAvailable, let recognizer else { return }
        let request = SFSpeechAudioBufferRecognitionRequest()
        request.shouldReportPartialResults = true
        request.requiresOnDeviceRecognition = true
        request.taskHint = .search
        request.contextualStrings = ["Nova", "Hey Nova", "OK Nova"]
        self.request = request
        generation += 1
        let generation = generation
        task = recognizer.recognitionTask(with: request) { @Sendable [weak self] result, _ in
            guard let text = result?.bestTranscription.formattedString else { return }
            let woke = WakePhrase.startsWithWakePhrase(text)
            guard woke else { return }
            DispatchQueue.main.async {
                MainActor.assumeIsolated {
                    guard let self, self.generation == generation else { return }
                    self.cancel()
                    self.onWake?()
                }
            }
        }
        feed(seed)
    }

    func feed(_ pcm: Data) {
        guard let request, !pcm.isEmpty else { return }
        let frames = AVAudioFrameCount(pcm.count / PCMFormat.bytesPerSample)
        guard let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frames),
              let channel = buffer.int16ChannelData?[0] else { return }
        buffer.frameLength = frames
        pcm.withUnsafeBytes { raw in
            guard let base = raw.baseAddress else { return }
            channel.update(from: base.assumingMemoryBound(to: Int16.self), count: Int(frames))
        }
        request.append(buffer)
    }

    func endUtterance() {
        request?.endAudio()
        request = nil
    }

    func cancel() {
        generation += 1
        task?.cancel()
        task = nil
        request?.endAudio()
        request = nil
    }
}
