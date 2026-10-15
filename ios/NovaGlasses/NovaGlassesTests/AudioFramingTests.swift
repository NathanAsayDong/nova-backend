@preconcurrency import AVFoundation
import XCTest
@testable import NovaGlasses

final class AudioFramingTests: XCTestCase {
    func testWavHeaderDescribes16kMonoInt16() {
        let header = PCMFormat.wavHeader(dataLength: 32_000)
        XCTAssertEqual(header.count, 44)
        func u32(_ at: Int) -> UInt32 { header.subdata(in: at..<at + 4).withUnsafeBytes { $0.loadUnaligned(as: UInt32.self) } }
        func u16(_ at: Int) -> UInt16 { header.subdata(in: at..<at + 2).withUnsafeBytes { $0.loadUnaligned(as: UInt16.self) } }
        XCTAssertEqual(String(data: header.prefix(4), encoding: .ascii), "RIFF")
        XCTAssertEqual(u32(4), 36 + 32_000)
        XCTAssertEqual(String(data: header.subdata(in: 8..<12), encoding: .ascii), "WAVE")
        XCTAssertEqual(u16(20), 1, "PCM")
        XCTAssertEqual(u16(22), 1, "mono")
        XCTAssertEqual(u32(24), 16_000)
        XCTAssertEqual(u32(28), 32_000, "byte rate")
        XCTAssertEqual(u16(34), 16)
        XCTAssertEqual(u32(40), 32_000)
    }

    func testByteDurationMath() {
        XCTAssertEqual(PCMFormat.bytes(forMs: 500), 16_000)
        XCTAssertEqual(PCMFormat.durationMs(ofBytes: 32_000), 1000)
    }

    func testRMSOfFullScaleSquareAndSilence() {
        let loud = Data(repeating: 0, count: 0) + (0..<160).flatMap { i -> [UInt8] in
            let v: Int16 = i % 2 == 0 ? Int16.max : Int16.min + 1
            return withUnsafeBytes(of: v.littleEndian) { Array($0) }
        }
        XCTAssertEqual(PCMFormat.rms(loud), 1, accuracy: 0.001)
        XCTAssertEqual(PCMFormat.rms(Data(count: 320)), 0)
        XCTAssertEqual(PCMFormat.rms(Data()), 0)
    }

    func testPreRollKeepsTheLast500msSampleAligned() {
        var ring = PreRollBuffer(ms: 500)
        XCTAssertEqual(ring.capacity, 16_000)
        for i in 0..<100 {
            ring.append(Data(repeating: UInt8(i), count: 320))
        }
        XCTAssertEqual(ring.count, 16_000)
        XCTAssertEqual(ring.snapshot().first, 50, "oldest kept frame is 50 of 0…99")
        XCTAssertEqual(ring.snapshot().last, 99)
        ring.append(Data(repeating: 7, count: 3))
        XCTAssertEqual(ring.count % 2, 1, "an odd append is kept whole")
        ring.clear()
        XCTAssertEqual(ring.count, 0)
    }

    func testFrameConverterResamplesToSixteenKMonoInt16() throws {
        let input = try XCTUnwrap(AVAudioFormat(standardFormatWithSampleRate: 48_000, channels: 1))
        let buffer = try XCTUnwrap(AVAudioPCMBuffer(pcmFormat: input, frameCapacity: 4800))
        buffer.frameLength = 4800
        for i in 0..<4800 {
            buffer.floatChannelData![0][i] = Float(0.5 * sin(2 * Double.pi * 440 * Double(i) / 48_000))
        }
        let converter = FrameConverter(input: input)
        var total = Data()
        for _ in 0..<5 {
            total.append(try XCTUnwrap(converter.convert(buffer)))
        }
        // 5 × 100 ms at 16 kHz × 2 bytes, less the resampler's ~20 ms latency
        // (held inside the converter for the next buffer, not lost).
        XCTAssertEqual(Double(total.count), 16_000, accuracy: 800)
        XCTAssertEqual(PCMFormat.rms(total.suffix(3200)), 0.5 / 2.0.squareRoot(), accuracy: 0.03)
    }

    func testEarconsRenderEveryCue() throws {
        for earcon in Earcon.allCases {
            let buffer = try XCTUnwrap(
                Earcons.render(Earcons.notes[earcon] ?? [], format: CaptureEngine.playbackFormat), "\(earcon)"
            )
            XCTAssertGreaterThan(buffer.frameLength, 1000)
            let samples = UnsafeBufferPointer(start: buffer.floatChannelData![0], count: Int(buffer.frameLength))
            XCTAssertLessThan(samples.map(abs).max() ?? 1, 0.5, "\(earcon) stays soft")
        }
    }

    func testMP3DecoderHandlesArbitraryChunkSplits() throws {
        let url = try XCTUnwrap(Bundle(for: Self.self).url(forResource: "tone_1s_22050", withExtension: "mp3"))
        let mp3 = try Data(contentsOf: url)
        let decoder = MP3StreamDecoder(outputFormat: CaptureEngine.playbackFormat)
        var frames: AVAudioFrameCount = 0
        var offset = 0
        var sizes = [7, 113, 1, 400, 1024, 333]
        while offset < mp3.count {
            let size = sizes.removeFirst()
            sizes.append(size)
            let end = min(mp3.count, offset + size)
            for buffer in decoder.decode(mp3.subdata(in: offset..<end)) {
                XCTAssertEqual(buffer.format.sampleRate, 24_000)
                frames += buffer.frameLength
            }
            offset = end
        }
        // One second of tone at 24 kHz; MP3 framing pads by up to ~2 frames.
        XCTAssertEqual(Double(frames), 24_000, accuracy: 2_600)
    }
}
