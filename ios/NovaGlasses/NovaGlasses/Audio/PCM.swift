import Foundation

/// The wire format the backend expects for glasses audio: 16 kHz mono
/// little-endian Int16, announced as this mime type on `start`. The server
/// wraps the buffered bytes in a WAV header before transcribing.
enum PCMFormat {
    static let sampleRate: Double = 16_000
    static let bytesPerSample = 2
    static let mimeType = "audio/pcm;rate=16000;channels=1"

    static func bytes(forMs ms: Double) -> Int {
        let samples = Int((sampleRate * ms / 1000).rounded())
        return samples * bytesPerSample
    }

    static func durationMs(ofBytes count: Int) -> Double {
        Double(count / bytesPerSample) / sampleRate * 1000
    }

    /// RMS of Int16 PCM, normalized to 0...1.
    static func rms(_ data: Data) -> Double {
        let count = data.count / bytesPerSample
        guard count > 0 else { return 0 }
        var sum: Double = 0
        data.withUnsafeBytes { raw in
            let samples = raw.bindMemory(to: Int16.self)
            for i in 0..<count {
                let v = Double(Int16(littleEndian: samples[i])) / 32768
                sum += v * v
            }
        }
        return (sum / Double(count)).squareRoot()
    }

    /// A 44-byte RIFF/WAVE header for `dataLength` bytes of this format.
    /// The server builds its own; this exists for local debugging dumps and
    /// to pin the framing in tests.
    static func wavHeader(dataLength: Int) -> Data {
        var header = Data()
        func append32(_ v: UInt32) { withUnsafeBytes(of: v.littleEndian) { header.append(contentsOf: $0) } }
        func append16(_ v: UInt16) { withUnsafeBytes(of: v.littleEndian) { header.append(contentsOf: $0) } }
        let rate = UInt32(sampleRate)
        header.append(contentsOf: Array("RIFF".utf8))
        append32(UInt32(36 + dataLength))
        header.append(contentsOf: Array("WAVE".utf8))
        header.append(contentsOf: Array("fmt ".utf8))
        append32(16)
        append16(1) // PCM
        append16(1) // mono
        append32(rate)
        append32(rate * UInt32(bytesPerSample))
        append16(UInt16(bytesPerSample))
        append16(16)
        header.append(contentsOf: Array("data".utf8))
        append32(UInt32(dataLength))
        return header
    }
}

/// The last `capacity` bytes of microphone audio, so a capture that starts at
/// the detector's onset still holds the syllable before it.
///
/// The web client gets the same effect from a 500 ms delay line in front of
/// its recorder, which makes the recording lag the mic. A ring buffer has no
/// lag: the capture is seeded with what is here and then streams live.
struct PreRollBuffer {
    let capacity: Int
    private var storage = Data()

    init(ms: Double = 500) {
        capacity = PCMFormat.bytes(forMs: ms)
    }

    var count: Int { storage.count }

    mutating func append(_ data: Data) {
        storage.append(data)
        let overflow = storage.count - capacity
        if overflow > 0 {
            // Keep sample alignment: drop whole samples only.
            let drop = min(storage.count, overflow + (overflow % PCMFormat.bytesPerSample))
            storage = Data(storage.dropFirst(drop))
        }
    }

    /// A copy indexed from zero (Data slices keep their parent's indices).
    func snapshot() -> Data { Data(storage) }

    mutating func clear() { storage.removeAll(keepingCapacity: true) }
}
