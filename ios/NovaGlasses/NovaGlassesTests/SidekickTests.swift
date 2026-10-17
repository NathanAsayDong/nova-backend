import XCTest
@testable import NovaGlasses

final class SidekickEventCodingTests: XCTestCase {
    private func json(_ event: ClientEvent) throws -> [String: Any] {
        let data = try JSONEncoder().encode(event)
        return try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
    }

    private func decode(_ text: String) throws -> ServerEvent {
        try JSONDecoder().decode(ServerEvent.self, from: Data(text.utf8))
    }

    func testClientEventsMatchTheSidekickProtocol() throws {
        let start = try json(.sidekickStart(conversationId: "c-1"))
        XCTAssertEqual(start["event"] as? String, "start")
        XCTAssertEqual(start["conversationId"] as? String, "c-1")
        XCTAssertNil(start["mimeType"], "a sidekick start is not a voice turn")
        XCTAssertEqual(try json(.utteranceStart)["event"] as? String, "utterance_start")
        XCTAssertEqual(try json(.utteranceEnd)["event"] as? String, "utterance_end")
        XCTAssertEqual(try json(.interrupted)["event"] as? String, "interrupted")
        XCTAssertEqual(try json(.sidekickStop)["event"] as? String, "stop")

        let decoded = try JSONDecoder().decode(ClientEvent.self, from: JSONEncoder().encode(ClientEvent.sidekickStart(conversationId: nil)))
        XCTAssertEqual(decoded, .sidekickStart(conversationId: nil))
    }

    func testDecodesSidekickServerEvents() throws {
        XCTAssertEqual(try decode(#"{"type":"sidekick_started","conversationId":"c"}"#), .sidekickStarted(conversationId: "c"))
        XCTAssertEqual(try decode(#"{"type":"heard","text":"your move"}"#), .heard(text: "your move"))
        XCTAssertEqual(try decode(#"{"type":"silent","conversationId":"c"}"#), .silent)
        XCTAssertEqual(try decode(#"{"type":"sidekick_ended","reason":"be_quiet"}"#), .sidekickEnded(reason: "be_quiet"))
    }
}

@MainActor
final class AmbientForwardingTests: XCTestCase {
    typealias Rig = ConversationControllerTests.Rig

    func testAnUtteranceWithoutTheWakePhraseGoesToSidekick() {
        let rig = Rig.idle()
        var forwarded: [Data] = []
        rig.controller.onAmbientUtterance = { forwarded.append($0) }
        rig.speak(800)
        rig.silence(2500)
        XCTAssertEqual(forwarded.count, 1)
        XCTAssertGreaterThanOrEqual(PCMFormat.durationMs(ofBytes: forwarded[0].count), 800)
        XCTAssertTrue(rig.socket.log.isEmpty, "nothing on the voice socket")
    }

    func testAWakeUtteranceDoesNot() {
        let rig = Rig.idle()
        var forwarded = 0
        var woke = 0
        rig.controller.onAmbientUtterance = { _ in forwarded += 1 }
        rig.controller.onWakeHeard = { woke += 1 }
        rig.speak(600)
        rig.wake.hear()
        rig.speak(300)
        rig.silence(2500)
        XCTAssertEqual(forwarded, 0)
        XCTAssertEqual(woke, 1)
    }

    func testNothingIsForwardedWhenSidekickIsOff() {
        let rig = Rig.idle()
        rig.speak(800)
        rig.silence(2500)
        XCTAssertNil(rig.controller.onAmbientUtterance)
    }

    func testSpeechWhileNovaTalksIsNotAmbient() {
        let rig = Rig.speaking()
        var forwarded = 0
        rig.controller.onAmbientUtterance = { _ in forwarded += 1 }
        rig.speak(800)
        rig.silence(2500)
        XCTAssertEqual(forwarded, 0, "likely Nova's own voice")
    }
}

@MainActor
final class SidekickControllerTests: XCTestCase {
    @MainActor
    final class Rig {
        let socket = FakeSocket()
        let player = FakePlayer()
        let earcons = FakeEarcons()
        let scheduler = ManualScheduler()
        var mainIdle = true
        var ended: [String] = []
        lazy var sidekick: SidekickController = {
            let sidekick = SidekickController(
                socket: socket, player: player, earcons: earcons, camera: nil, vision: nil,
                scheduler: scheduler, mainIsIdle: { [unowned self] in self.mainIdle }
            )
            sidekick.onEnded = { [unowned self] in self.ended.append($0) }
            return sidekick
        }()

        /// On, connected and acknowledged.
        static func started() -> Rig {
            let rig = Rig()
            rig.sidekick.start()
            rig.socket.open()
            rig.socket.emit(.sidekickStarted(conversationId: "side-1"))
            return rig
        }

        func interjection(_ id: String = "r1") {
            socket.emit(.audioStreamStart(streamId: id, mimeType: "audio/mpeg", role: .final))
            socket.emit(.audioStreamChunk(streamId: id, chunkBase64: Data([1, 2]).base64EncodedString(), seq: 0))
        }
    }

    func testStartingConnectsAndIntroducesItself() {
        let rig = Rig()
        rig.sidekick.start()
        XCTAssertEqual(rig.socket.connectCalls, 1)
        XCTAssertEqual(rig.earcons.played, [.sidekickOn])
        rig.socket.open()
        XCTAssertEqual(rig.socket.events, [.sidekickStart(conversationId: nil)])
    }

    func testUtterancesWaitForTheServerThenGoOutFramed() {
        let rig = Rig()
        rig.sidekick.start()
        rig.sidekick.ambient(Data(count: 6400))
        XCTAssertTrue(rig.socket.audio.isEmpty)
        rig.socket.open()
        rig.socket.emit(.sidekickStarted(conversationId: "side-1"))
        XCTAssertEqual(rig.socket.log, ["start", "utterance_start", "audio", "utterance_end"])
        XCTAssertEqual(rig.socket.audio.count, 6400)
    }

    func testAnInterjectionPlaysWithACueWhenNovaIsIdle() {
        let rig = Rig.started()
        rig.interjection()
        XCTAssertEqual(rig.player.active, ["r1"])
        XCTAssertEqual(rig.earcons.played.last, .sidekickCue)
        XCTAssertNotNil(rig.player.chunks["r1"])
    }

    func testAnInterjectionDuringADirectTurnIsDropped() {
        let rig = Rig.started()
        rig.mainIdle = false
        rig.interjection()
        XCTAssertTrue(rig.player.active.isEmpty)
        XCTAssertNil(rig.player.chunks["r1"])
        XCTAssertEqual(rig.socket.events.last, .interrupted)
    }

    func testHeyNovaCutsAnInterjectionOff() {
        let rig = Rig.started()
        rig.interjection()
        rig.sidekick.userWoke()
        XCTAssertEqual(rig.player.stopAllCalls, 1)
        XCTAssertEqual(rig.socket.events.last, .interrupted)
        rig.socket.emit(.audioStreamChunk(streamId: "r1", chunkBase64: Data([9]).base64EncodedString(), seq: 1))
        XCTAssertEqual(rig.player.chunks["r1"], Data([1, 2]), "the rest of it is ignored")
    }

    func testTurnsItselfOffAfterAnHour() {
        let rig = Rig.started()
        rig.scheduler.advance(SidekickController.autoOffSeconds + 1)
        XCTAssertFalse(rig.sidekick.isOn)
        XCTAssertEqual(rig.ended, ["timeout"])
        XCTAssertTrue(rig.socket.events.contains(.sidekickStop))
        XCTAssertEqual(rig.earcons.played.last, .sidekickOff)
    }

    func testBeQuietFromTheServerEndsIt() {
        let rig = Rig.started()
        rig.socket.emit(.sidekickEnded(reason: "be_quiet"))
        XCTAssertFalse(rig.sidekick.isOn)
        XCTAssertEqual(rig.ended, ["be_quiet"])
        XCTAssertEqual(rig.socket.disconnectCalls, 1)
    }
}
