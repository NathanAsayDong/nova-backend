import AudioToolbox
@preconcurrency import AVFoundation
import Foundation

/// Decodes an MP3 byte stream incrementally, as the server's base64 chunks
/// arrive, so Nova starts talking before the whole sentence has downloaded.
///
/// AudioFileStream finds the MP3 frames in arbitrary byte splits;
/// AVAudioConverter turns each batch of frames into PCM in `outputFormat`.
final class MP3StreamDecoder {
    let outputFormat: AVAudioFormat
    private var streamID: AudioFileStreamID?
    private var inputFormat: AVAudioFormat?
    private var converter: AVAudioConverter?
    private var decoded: [AVAudioPCMBuffer] = []

    init(outputFormat: AVAudioFormat) {
        self.outputFormat = outputFormat
        let context = Unmanaged.passUnretained(self).toOpaque()
        AudioFileStreamOpen(context, { context, stream, property, _ in
            let decoder = Unmanaged<MP3StreamDecoder>.fromOpaque(context).takeUnretainedValue()
            decoder.propertyChanged(stream, property)
        }, { context, byteCount, packetCount, data, descriptions in
            let decoder = Unmanaged<MP3StreamDecoder>.fromOpaque(context).takeUnretainedValue()
            decoder.packetsArrived(byteCount, packetCount, data, descriptions)
        }, kAudioFileMP3Type, &streamID)
    }

    deinit {
        if let streamID {
            AudioFileStreamClose(streamID)
        }
    }

    /// Feed the next bytes; returns whatever PCM they completed.
    func decode(_ data: Data) -> [AVAudioPCMBuffer] {
        guard let streamID, !data.isEmpty else { return [] }
        decoded = []
        data.withUnsafeBytes { raw in
            guard let base = raw.baseAddress else { return }
            _ = AudioFileStreamParseBytes(streamID, UInt32(raw.count), base, [])
        }
        let result = decoded
        decoded = []
        return result
    }

    private func propertyChanged(_ stream: AudioFileStreamID, _ property: AudioFileStreamPropertyID) {
        guard property == kAudioFileStreamProperty_ReadyToProducePackets else { return }
        var description = AudioStreamBasicDescription()
        var size = UInt32(MemoryLayout<AudioStreamBasicDescription>.size)
        guard AudioFileStreamGetProperty(stream, kAudioFileStreamProperty_DataFormat, &size, &description) == noErr,
              let format = AVAudioFormat(streamDescription: &description) else { return }
        inputFormat = format
        converter = AVAudioConverter(from: format, to: outputFormat)
    }

    private func packetsArrived(
        _ byteCount: UInt32,
        _ packetCount: UInt32,
        _ data: UnsafeRawPointer,
        _ descriptions: UnsafeMutablePointer<AudioStreamPacketDescription>?
    ) {
        guard let inputFormat, let converter, let descriptions, packetCount > 0 else { return }
        var maxPacket: UInt32 = 0
        for i in 0..<Int(packetCount) {
            maxPacket = max(maxPacket, descriptions[i].mDataByteSize)
        }
        let compressed = AVAudioCompressedBuffer(
            format: inputFormat, packetCapacity: packetCount, maximumPacketSize: Int(maxPacket)
        )
        compressed.data.copyMemory(from: data, byteCount: Int(byteCount))
        compressed.byteLength = byteCount
        compressed.packetCount = packetCount
        if let target = compressed.packetDescriptions {
            target.update(from: descriptions, count: Int(packetCount))
        }

        let framesPerPacket = max(1, Double(inputFormat.streamDescription.pointee.mFramesPerPacket))
        let ratio = outputFormat.sampleRate / inputFormat.sampleRate
        let capacity = AVAudioFrameCount(Double(packetCount) * framesPerPacket * ratio) + 2048
        var consumed = false
        while true {
            guard let out = AVAudioPCMBuffer(pcmFormat: outputFormat, frameCapacity: capacity) else { return }
            var error: NSError?
            let status = converter.convert(to: out, error: &error) { _, inputStatus in
                if consumed {
                    inputStatus.pointee = .noDataNow
                    return nil
                }
                consumed = true
                inputStatus.pointee = .haveData
                return compressed
            }
            if out.frameLength > 0 {
                decoded.append(out)
            }
            // A full buffer means the converter may still hold more output.
            if status != .haveData || out.frameLength < out.frameCapacity {
                return
            }
        }
    }
}
