import XCTest
@testable import NovaGlasses

final class EventCodingTests: XCTestCase {
    private func json(_ value: some Encodable) throws -> [String: Any] {
        let data = try JSONEncoder().encode(value)
        return try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
    }

    private func decode(_ text: String) throws -> ServerEvent {
        try JSONDecoder().decode(ServerEvent.self, from: Data(text.utf8))
    }

    // MARK: Client → server

    func testStartAlwaysCarriesGlassesClientAndPCMMimeType() throws {
        let object = try json(ClientEvent.start(StartEvent(purpose: .sentry, conversationId: "c-1")))
        XCTAssertEqual(object["event"] as? String, "start")
        XCTAssertEqual(object["client"] as? String, "glasses")
        XCTAssertEqual(object["mimeType"] as? String, "audio/pcm;rate=16000;channels=1")
        XCTAssertEqual(object["purpose"] as? String, "sentry")
        XCTAssertEqual(object["language"] as? String, "en")
        XCTAssertEqual(object["conversationId"] as? String, "c-1")
    }

    func testStartOmitsAMissingConversationId() throws {
        let object = try json(ClientEvent.start(StartEvent(purpose: .turn, conversationId: nil)))
        XCTAssertNil(object["conversationId"])
    }

    func testControlEventNames() throws {
        XCTAssertEqual(try json(ClientEvent.speechPause)["event"] as? String, "speech_pause")
        XCTAssertEqual(try json(ClientEvent.speechResume)["event"] as? String, "speech_resume")
        XCTAssertEqual(try json(ClientEvent.abort)["event"] as? String, "abort")
        XCTAssertEqual(try json(ClientEvent.ping)["event"] as? String, "ping")
        let stop = try json(ClientEvent.stop(purpose: .sentry, conversationId: "c-2"))
        XCTAssertEqual(stop["event"] as? String, "stop")
        XCTAssertEqual(stop["purpose"] as? String, "sentry")
        XCTAssertEqual(stop["conversationId"] as? String, "c-2")
    }

    func testClientEventsRoundTrip() throws {
        let events: [ClientEvent] = [
            .start(StartEvent(purpose: .turn, conversationId: "abc")),
            .start(StartEvent(purpose: .sentry, conversationId: nil)),
            .speechPause, .speechResume, .abort, .ping,
            .stop(purpose: .turn, conversationId: nil),
            .stop(purpose: .sentry, conversationId: "abc"),
        ]
        for event in events {
            let data = try JSONEncoder().encode(event)
            XCTAssertEqual(try JSONDecoder().decode(ClientEvent.self, from: data), event)
        }
    }

    // MARK: Server → client

    func testDecodesServerPayloadsAsTheBackendSendsThem() throws {
        XCTAssertEqual(try decode(#"{"type":"ready","message":"Connected."}"#), .ready(message: "Connected."))
        XCTAssertEqual(
            try decode(#"{"type":"listening","message":"Streaming","endpointMs":1000}"#),
            .listening(message: "Streaming", endpointMs: 1000)
        )
        XCTAssertEqual(
            try decode(#"{"type":"partial_transcript","text":"what is","seq":3,"endpointMs":1800,"endpointReason":"dangling"}"#),
            .partialTranscript(text: "what is", seq: 3, endpointMs: 1800)
        )
        XCTAssertEqual(
            try decode(#"{"type":"assistant_audio_stream_start","streamId":"s1","mimeType":"audio/mpeg","role":"final","iteration":2}"#),
            .audioStreamStart(streamId: "s1", mimeType: "audio/mpeg", role: .final)
        )
        XCTAssertEqual(
            try decode(#"{"type":"assistant_audio_stream_chunk","streamId":"s1","chunkBase64":"AAA=","seq":0}"#),
            .audioStreamChunk(streamId: "s1", chunkBase64: "AAA=", seq: 0)
        )
        XCTAssertEqual(
            try decode(#"{"type":"speech_text","text":"Sure.","role":"status","conversationId":"c"}"#),
            .speechText(text: "Sure.", role: "status", conversationId: "c")
        )
        XCTAssertEqual(
            try decode(#"{"type":"error","message":"Conversation is closed.","code":"conversation_closed"}"#),
            .error(message: "Conversation is closed.", code: "conversation_closed")
        )
        XCTAssertEqual(try decode(#"{"type":"error","message":"No audio chunks received."}"#),
                       .error(message: "No audio chunks received.", code: nil))
        XCTAssertEqual(try decode(#"{"type":"pong"}"#), .pong)
    }

    func testScreenOnlyEventsDecodeAsOther() throws {
        XCTAssertEqual(
            try decode(#"{"type":"assistant_text","text":"Title","seq":1,"conversationId":"c"}"#),
            .other(type: "assistant_text")
        )
        XCTAssertEqual(try decode(#"{"type":"tool_call","tool":"x","input":{},"conversationId":"c"}"#),
                       .other(type: "tool_call"))
    }

    func testServerEventsRoundTrip() throws {
        let events: [ServerEvent] = [
            .ready(message: "hi"),
            .listening(message: "l", endpointMs: 900),
            .listening(message: "l", endpointMs: nil),
            .chunkReceived(count: 3, bytes: 9600),
            .partialTranscript(text: "t", seq: 2, endpointMs: 1200),
            .userTranscript(text: "what's up", conversationId: "c"),
            .speechText(text: "Hello.", role: "final", conversationId: "c"),
            .audioStreamStart(streamId: "s", mimeType: "audio/mpeg", role: .status),
            .audioStreamChunk(streamId: "s", chunkBase64: "SUQz", seq: 4),
            .audioStreamEnd(streamId: "s"),
            .done(message: "Done", conversationId: "c", assistantText: "Long answer"),
            .noSpeech(message: "n"),
            .wakeOnly(message: "w"),
            .wakeNotDetected(message: "x"),
            .followUpStopped(message: "bye"),
            .meetingMode(message: "m"),
            .error(message: "e", code: "conversation_closed"),
            .error(message: "e", code: nil),
            .pong,
        ]
        for event in events {
            let data = try JSONEncoder().encode(event)
            XCTAssertEqual(try JSONDecoder().decode(ServerEvent.self, from: data), event)
        }
    }
}
