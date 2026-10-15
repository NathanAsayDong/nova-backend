@preconcurrency import AVFoundation
import Foundation

/// Nova's interface sounds, synthesized rather than shipped as files — the
/// same soft bells as the web client's earcons.ts (a sine with a faint octave
/// overtone, fast attack, exponential tail). With no screen they are the only
/// state feedback, so each one means one thing:
///
///  - wake:     rising fifth. "I heard you, go ahead."
///  - thinking: one short high tick. "Got it, working on it."
///  - done:     falling fifth. "Finished, back to waiting."
///  - cancel:   one low, quiet note. "Never mind."
///  - error:    two low notes, a little louder. "That failed."
@MainActor
final class Earcons: EarconPlaying {
    struct Note: Equatable, Sendable {
        var freq: Double
        var at: Double
        var length: Double
        var gain: Double
    }

    nonisolated static let notes: [Earcon: [Note]] = {
        let e5 = 659.25, b5 = 987.77, a4 = 440.0, e4 = 329.63, c4 = 261.63
        return [
            .wake: [Note(freq: e5, at: 0, length: 0.32, gain: 0.16), Note(freq: b5, at: 0.085, length: 0.42, gain: 0.14)],
            .thinking: [Note(freq: b5, at: 0, length: 0.14, gain: 0.07)],
            .done: [Note(freq: b5, at: 0, length: 0.3, gain: 0.11), Note(freq: e5, at: 0.11, length: 0.5, gain: 0.12)],
            .cancel: [Note(freq: a4, at: 0, length: 0.22, gain: 0.08), Note(freq: e4, at: 0.09, length: 0.38, gain: 0.08)],
            .error: [Note(freq: e4, at: 0, length: 0.25, gain: 0.14), Note(freq: c4, at: 0.18, length: 0.45, gain: 0.14)],
        ]
    }()

    let node = AVAudioPlayerNode()
    private var cache: [Earcon: AVAudioPCMBuffer] = [:]

    func play(_ earcon: Earcon) {
        guard node.engine?.isRunning == true, let buffer = buffer(for: earcon) else { return }
        node.scheduleBuffer(buffer, at: nil, options: [], completionHandler: nil)
        if !node.isPlaying {
            node.play()
        }
    }

    private func buffer(for earcon: Earcon) -> AVAudioPCMBuffer? {
        if let cached = cache[earcon] { return cached }
        let rendered = Self.render(Self.notes[earcon] ?? [], format: CaptureEngine.playbackFormat)
        cache[earcon] = rendered
        return rendered
    }

    /// Render notes to a mono float buffer.
    nonisolated static func render(_ notes: [Note], format: AVAudioFormat) -> AVAudioPCMBuffer? {
        let rate = format.sampleRate
        let duration = (notes.map { $0.at + $0.length }.max() ?? 0) + 0.05
        let frames = AVAudioFrameCount(duration * rate)
        guard frames > 0,
              let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frames),
              let channel = buffer.floatChannelData?[0] else { return nil }
        buffer.frameLength = frames
        for i in 0..<Int(frames) { channel[i] = 0 }
        for note in notes {
            let start = Int(note.at * rate)
            let count = Int(note.length * rate)
            let attack = 0.012 * rate
            // Exponential tail from the peak down to -80 dB over the note.
            let decay = log(note.gain / 0.0001) / (note.length * rate - attack)
            for n in 0..<count where start + n < Int(frames) {
                let t = Double(n)
                let envelope = t < attack ? note.gain * t / attack : note.gain * exp(-(t - attack) * decay)
                let phase = 2 * Double.pi * note.freq * t / rate
                let sample = (sin(phase) + 0.18 * sin(2 * phase)) * envelope
                channel[start + n] += Float(sample)
            }
        }
        return buffer
    }
}
