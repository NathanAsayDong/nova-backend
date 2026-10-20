import XCTest
@testable import NovaGlasses

final class WakePhraseAloneTests: XCTestCase {
    func testRecognizesABareWakePhrase() {
        for text in ["Hey Nova", "Hey Nova.", "Nova?", "hey noah", "Hey Nova, um", "OK Nova"] {
            XCTAssertTrue(WakePhrase.isOnlyWakePhrase(text), text)
        }
        for text in ["Hey Nova what time is it", "Nova, lights", "hello there", ""] {
            XCTAssertFalse(WakePhrase.isOnlyWakePhrase(text), text)
        }
    }
}

@MainActor
final class WakeStraightToListeningTests: XCTestCase {
    typealias Rig = ConversationControllerTests.Rig

    func testHeyNovaThenAPauseListensWithoutThinking() {
        let rig = Rig.idle()
        rig.speak(500)
        rig.wake.hear()
        rig.wake.caption("Hey Nova")
        rig.silence(1500)
        XCTAssertEqual(rig.controller.phase, .listening)
        XCTAssertFalse(rig.earcons.played.contains(.thinking), "no thinking tick for a bare wake")
        XCTAssertFalse(rig.socket.log.contains("stop"), "nothing sent for the server to rule on")

        // The request that follows is its own turn.
        rig.socket.events.removeAll()
        rig.speak(600)
        XCTAssertEqual(rig.socket.starts.last?.purpose, .turn)
        rig.silence(1500)
        XCTAssertEqual(rig.controller.phase, .thinking)
        XCTAssertEqual(rig.socket.events.last, .stop(purpose: .turn, conversationId: nil))
    }

    func testAWakeConfirmedAfterTheUtteranceEndedAlsoJustListens() {
        let rig = Rig.idle()
        rig.speak(500)
        rig.silence(1500) // ended before the recognizer ruled
        rig.wake.hear()
        rig.wake.caption("Hey Nova.")
        // The caption arrives with the wake; the controller decides on it.
        XCTAssertEqual(rig.controller.phase, .listening)
        rig.scheduler.advance(2)
        XCTAssertNotEqual(rig.controller.phase, .thinking)
        XCTAssertFalse(rig.earcons.played.contains(.thinking))
    }

    func testOneBreathRequestsAreUnchanged() {
        let rig = Rig.idle()
        rig.speak(500)
        rig.wake.hear()
        rig.wake.caption("Hey Nova what time is it")
        rig.speak(400)
        rig.silence(1500)
        XCTAssertEqual(rig.controller.phase, .thinking)
        XCTAssertEqual(rig.socket.events.last, .stop(purpose: .sentry, conversationId: nil))
    }

    func testListeningTimesOutIfNoRequestFollows() {
        let rig = Rig.idle()
        rig.speak(500)
        rig.wake.hear()
        rig.wake.caption("Hey Nova")
        rig.silence(1500)
        rig.silence(ConversationController.listenTimeoutSeconds * 1000 + 200)
        XCTAssertEqual(rig.controller.phase, .idle)
    }
}
