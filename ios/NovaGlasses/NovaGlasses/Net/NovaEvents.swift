import Foundation

/// What a capture is for. Mirrors `CapturePurpose` in the web client's types.ts.
enum CapturePurpose: String, Codable, Equatable, Sendable {
    /// A request, while Nova is already listening.
    case turn
    /// An utterance that opens with the wake phrase, sent whole so the request
    /// said in the same breath is not lost. The server strips the wake phrase.
    case sentry
    /// Legacy wake check; the glasses client does not send it.
    case wakeCheck = "wake_check"
}

// MARK: - Client → server

struct StartEvent: Codable, Equatable, Sendable {
    var mimeType: String = PCMFormat.mimeType
    var language: String = "en"
    var purpose: CapturePurpose
    var conversationId: String?
    /// Selects GLASSES_PROMPT on the server: no screen, everything is heard.
    var client: String = "glasses"
}

/// JSON control messages on /ws/transcribe, keyed by `event`.
enum ClientEvent: Equatable, Sendable {
    case start(StartEvent)
    case speechPause
    case speechResume
    case abort
    /// `imageIds`: glasses photos uploaded for this turn (POST /vision/images).
    case stop(purpose: CapturePurpose, conversationId: String?, imageIds: [String] = [])
    case ping

    // Sidekick (/ws/sidekick)
    case sidekickStart(conversationId: String?)
    case utteranceStart
    case utteranceEnd
    /// "Hey Nova" cut into an interjection.
    case interrupted
    case sidekickStop

    var name: String {
        switch self {
        case .start: "start"
        case .speechPause: "speech_pause"
        case .speechResume: "speech_resume"
        case .abort: "abort"
        case .stop: "stop"
        case .ping: "ping"
        case .sidekickStart: "start"
        case .utteranceStart: "utterance_start"
        case .utteranceEnd: "utterance_end"
        case .interrupted: "interrupted"
        case .sidekickStop: "stop"
        }
    }
}

extension ClientEvent: Codable {
    private enum Keys: String, CodingKey {
        case event, mimeType, language, purpose, conversationId, client, imageIds
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: Keys.self)
        try c.encode(name, forKey: .event)
        switch self {
        case .start(let start):
            try c.encode(start.mimeType, forKey: .mimeType)
            try c.encode(start.language, forKey: .language)
            try c.encode(start.purpose, forKey: .purpose)
            try c.encodeIfPresent(start.conversationId, forKey: .conversationId)
            try c.encode(start.client, forKey: .client)
        case .stop(let purpose, let conversationId, let imageIds):
            try c.encode(purpose, forKey: .purpose)
            try c.encodeIfPresent(conversationId, forKey: .conversationId)
            if !imageIds.isEmpty {
                try c.encode(imageIds, forKey: .imageIds)
            }
        case .sidekickStart(let conversationId):
            try c.encodeIfPresent(conversationId, forKey: .conversationId)
        case .speechPause, .speechResume, .abort, .ping,
             .utteranceStart, .utteranceEnd, .interrupted, .sidekickStop:
            break
        }
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: Keys.self)
        let event = try c.decode(String.self, forKey: .event)
        switch event {
        case "start" where !c.contains(.mimeType):
            self = .sidekickStart(conversationId: try c.decodeIfPresent(String.self, forKey: .conversationId))
        case "utterance_start": self = .utteranceStart
        case "utterance_end": self = .utteranceEnd
        case "interrupted": self = .interrupted
        case "start":
            self = .start(StartEvent(
                mimeType: try c.decode(String.self, forKey: .mimeType),
                language: try c.decode(String.self, forKey: .language),
                purpose: try c.decode(CapturePurpose.self, forKey: .purpose),
                conversationId: try c.decodeIfPresent(String.self, forKey: .conversationId),
                client: try c.decodeIfPresent(String.self, forKey: .client) ?? "web"
            ))
        case "speech_pause": self = .speechPause
        case "speech_resume": self = .speechResume
        case "abort": self = .abort
        case "ping": self = .ping
        case "stop":
            self = .stop(
                purpose: try c.decodeIfPresent(CapturePurpose.self, forKey: .purpose) ?? .turn,
                conversationId: try c.decodeIfPresent(String.self, forKey: .conversationId),
                imageIds: try c.decodeIfPresent([String].self, forKey: .imageIds) ?? []
            )
        default:
            throw DecodingError.dataCorruptedError(forKey: .event, in: c, debugDescription: "Unknown event \(event)")
        }
    }
}

// MARK: - Server → client

enum AudioRole: String, Codable, Equatable, Sendable {
    case progress, status, final, wake
}

/// Events the server sends on /ws/transcribe, keyed by `type`. Only the
/// fields this client uses are modelled; screen-only events (assistant_text,
/// tool_call, artifact, …) decode as `.other` and are ignored.
enum ServerEvent: Equatable, Sendable {
    case ready(message: String)
    case listening(message: String, endpointMs: Double?)
    case chunkReceived(count: Int, bytes: Int)
    case partialTranscript(text: String, seq: Int, endpointMs: Double?)
    case userTranscript(text: String, conversationId: String)
    case speechText(text: String, role: String, conversationId: String)
    case audioStreamStart(streamId: String, mimeType: String, role: AudioRole)
    case audioStreamChunk(streamId: String, chunkBase64: String, seq: Int)
    case audioStreamEnd(streamId: String)
    case done(message: String, conversationId: String, assistantText: String)
    case noSpeech(message: String)
    case wakeOnly(message: String)
    case wakeNotDetected(message: String)
    case followUpStopped(message: String)
    case meetingMode(message: String)
    case error(message: String, code: String?)
    /// Nova started a tool (a step of the work), so it is still thinking.
    case toolCall(tool: String)

    // Sidekick (/ws/sidekick)
    case sidekickStarted(conversationId: String)
    /// One overheard utterance, transcribed.
    case heard(text: String)
    /// Nova considered chiming in and chose not to.
    case silent
    /// be_quiet, timeout, stopped or error.
    case sidekickEnded(reason: String)
    /// Nova's `look` tool wants a photo right now; upload it with this id.
    case captureRequest(requestId: String, conversationId: String?)
    case pong
    case other(type: String)
}

extension ServerEvent: Codable {
    private enum Keys: String, CodingKey {
        case type, message, endpointMs, count, bytes, text, seq, conversationId
        case role, streamId, mimeType, chunkBase64, assistantText, code, requestId, tool, reason
    }

    var type: String {
        switch self {
        case .ready: "ready"
        case .listening: "listening"
        case .chunkReceived: "chunk_received"
        case .partialTranscript: "partial_transcript"
        case .userTranscript: "user_transcript"
        case .speechText: "speech_text"
        case .audioStreamStart: "assistant_audio_stream_start"
        case .audioStreamChunk: "assistant_audio_stream_chunk"
        case .audioStreamEnd: "assistant_audio_stream_end"
        case .done: "done"
        case .noSpeech: "no_speech"
        case .wakeOnly: "wake_only"
        case .wakeNotDetected: "wake_not_detected"
        case .followUpStopped: "follow_up_stopped"
        case .meetingMode: "meeting_mode"
        case .error: "error"
        case .toolCall: "tool_call"
        case .sidekickStarted: "sidekick_started"
        case .heard: "heard"
        case .silent: "silent"
        case .sidekickEnded: "sidekick_ended"
        case .captureRequest: "capture_request"
        case .pong: "pong"
        case .other(let type): type
        }
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: Keys.self)
        let type = try c.decode(String.self, forKey: .type)
        func message() throws -> String { try c.decodeIfPresent(String.self, forKey: .message) ?? "" }
        switch type {
        case "ready":
            self = .ready(message: try message())
        case "listening":
            self = .listening(message: try message(), endpointMs: try c.decodeIfPresent(Double.self, forKey: .endpointMs))
        case "chunk_received":
            self = .chunkReceived(count: try c.decode(Int.self, forKey: .count), bytes: try c.decode(Int.self, forKey: .bytes))
        case "partial_transcript":
            self = .partialTranscript(
                text: try c.decode(String.self, forKey: .text),
                seq: try c.decodeIfPresent(Int.self, forKey: .seq) ?? 0,
                endpointMs: try c.decodeIfPresent(Double.self, forKey: .endpointMs)
            )
        case "user_transcript":
            self = .userTranscript(
                text: try c.decode(String.self, forKey: .text),
                conversationId: try c.decodeIfPresent(String.self, forKey: .conversationId) ?? ""
            )
        case "speech_text":
            self = .speechText(
                text: try c.decode(String.self, forKey: .text),
                role: try c.decodeIfPresent(String.self, forKey: .role) ?? "final",
                conversationId: try c.decodeIfPresent(String.self, forKey: .conversationId) ?? ""
            )
        case "assistant_audio_stream_start":
            self = .audioStreamStart(
                streamId: try c.decode(String.self, forKey: .streamId),
                mimeType: try c.decodeIfPresent(String.self, forKey: .mimeType) ?? "audio/mpeg",
                role: try c.decodeIfPresent(AudioRole.self, forKey: .role) ?? .final
            )
        case "assistant_audio_stream_chunk":
            self = .audioStreamChunk(
                streamId: try c.decode(String.self, forKey: .streamId),
                chunkBase64: try c.decode(String.self, forKey: .chunkBase64),
                seq: try c.decodeIfPresent(Int.self, forKey: .seq) ?? 0
            )
        case "assistant_audio_stream_end":
            self = .audioStreamEnd(streamId: try c.decode(String.self, forKey: .streamId))
        case "done":
            self = .done(
                message: try message(),
                conversationId: try c.decodeIfPresent(String.self, forKey: .conversationId) ?? "",
                assistantText: try c.decodeIfPresent(String.self, forKey: .assistantText) ?? ""
            )
        case "no_speech": self = .noSpeech(message: try message())
        case "wake_only": self = .wakeOnly(message: try message())
        case "wake_not_detected": self = .wakeNotDetected(message: try message())
        case "follow_up_stopped": self = .followUpStopped(message: try message())
        case "meeting_mode": self = .meetingMode(message: try message())
        case "error":
            self = .error(message: try message(), code: try c.decodeIfPresent(String.self, forKey: .code))
        case "sidekick_started":
            self = .sidekickStarted(conversationId: try c.decodeIfPresent(String.self, forKey: .conversationId) ?? "")
        case "heard":
            self = .heard(text: try c.decodeIfPresent(String.self, forKey: .text) ?? "")
        case "silent": self = .silent
        case "sidekick_ended":
            self = .sidekickEnded(reason: try c.decodeIfPresent(String.self, forKey: .reason) ?? "stopped")
        case "tool_call":
            self = .toolCall(tool: try c.decodeIfPresent(String.self, forKey: .tool) ?? "")
        case "capture_request":
            self = .captureRequest(
                requestId: try c.decode(String.self, forKey: .requestId),
                conversationId: try c.decodeIfPresent(String.self, forKey: .conversationId)
            )
        case "pong": self = .pong
        default: self = .other(type: type)
        }
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: Keys.self)
        try c.encode(type, forKey: .type)
        switch self {
        case .ready(let m), .noSpeech(let m), .wakeOnly(let m), .wakeNotDetected(let m),
             .followUpStopped(let m), .meetingMode(let m):
            try c.encode(m, forKey: .message)
        case .listening(let m, let endpointMs):
            try c.encode(m, forKey: .message)
            try c.encodeIfPresent(endpointMs, forKey: .endpointMs)
        case .chunkReceived(let count, let bytes):
            try c.encode(count, forKey: .count)
            try c.encode(bytes, forKey: .bytes)
        case .partialTranscript(let text, let seq, let endpointMs):
            try c.encode(text, forKey: .text)
            try c.encode(seq, forKey: .seq)
            try c.encodeIfPresent(endpointMs, forKey: .endpointMs)
        case .userTranscript(let text, let id):
            try c.encode(text, forKey: .text)
            try c.encode(id, forKey: .conversationId)
        case .speechText(let text, let role, let id):
            try c.encode(text, forKey: .text)
            try c.encode(role, forKey: .role)
            try c.encode(id, forKey: .conversationId)
        case .audioStreamStart(let streamId, let mimeType, let role):
            try c.encode(streamId, forKey: .streamId)
            try c.encode(mimeType, forKey: .mimeType)
            try c.encode(role, forKey: .role)
        case .audioStreamChunk(let streamId, let chunk, let seq):
            try c.encode(streamId, forKey: .streamId)
            try c.encode(chunk, forKey: .chunkBase64)
            try c.encode(seq, forKey: .seq)
        case .audioStreamEnd(let streamId):
            try c.encode(streamId, forKey: .streamId)
        case .done(let m, let id, let text):
            try c.encode(m, forKey: .message)
            try c.encode(id, forKey: .conversationId)
            try c.encode(text, forKey: .assistantText)
        case .error(let m, let code):
            try c.encode(m, forKey: .message)
            try c.encodeIfPresent(code, forKey: .code)
        case .toolCall(let tool):
            try c.encode(tool, forKey: .tool)
        case .sidekickStarted(let conversationId):
            try c.encode(conversationId, forKey: .conversationId)
        case .heard(let text):
            try c.encode(text, forKey: .text)
        case .sidekickEnded(let reason):
            try c.encode(reason, forKey: .reason)
        case .silent:
            break
        case .captureRequest(let requestId, let conversationId):
            try c.encode(requestId, forKey: .requestId)
            try c.encodeIfPresent(conversationId, forKey: .conversationId)
        case .pong, .other:
            break
        }
    }
}
