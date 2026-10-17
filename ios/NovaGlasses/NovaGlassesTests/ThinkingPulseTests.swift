import XCTest
@testable import NovaGlasses

@MainActor
final class ThinkingPulseTests: XCTestCase {
    typealias Rig = ConversationControllerTests.Rig

    private func pulses(_ rig: Rig) -> Int {
        rig.earcons.played.filter { $0 == .thinkingPulse }.count
    }

    func testBreathesWhileNovaWorks() {
        let rig = Rig.thinking()
        XCTAssertEqual(pulses(rig), 0)
        rig.scheduler.advance(ConversationController.thinkingGraceSeconds + 0.01)
        XCTAssertEqual(pulses(rig), 1)
        rig.scheduler.advance(ConversationController.thinkingPulseSeconds * 2 + 0.01)
        XCTAssertEqual(pulses(rig), 3)
    }

    func testAQuickAnswerNeverHearsIt() {
        let rig = Rig.thinking()
        rig.socket.emit(.audioStreamStart(streamId: "s1", mimeType: "audio/mpeg", role: .final))
        rig.scheduler.advance(5)
        XCTAssertEqual(pulses(rig), 0)
    }

    func testStopsWhenNovaTalksAndResumesWhileAToolRuns() {
        let rig = Rig.thinking()
        rig.scheduler.advance(1)
        XCTAssertEqual(pulses(rig), 1)

        // A spoken status line: silent while it plays.
        rig.socket.emit(.audioStreamStart(streamId: "s1", mimeType: "audio/mpeg", role: .status))
        rig.socket.emit(.audioStreamEnd(streamId: "s1"))
        rig.scheduler.advance(5)
        XCTAssertEqual(pulses(rig), 1)

        // The line finished and a tool is running: breathe again.
        rig.player.finishPlaying()
        rig.socket.emit(.toolCall(tool: "calendar_events"))
        rig.scheduler.advance(ConversationController.thinkingGraceSeconds + 0.01)
        XCTAssertEqual(pulses(rig), 2)
    }

    func testDoneEndsIt() {
        let rig = Rig.thinking()
        rig.scheduler.advance(1)
        rig.socket.emit(.done(message: "", conversationId: "c", assistantText: ""))
        let count = pulses(rig)
        rig.scheduler.advance(10)
        XCTAssertEqual(pulses(rig), count)
    }

    func testThePhotoWaitPulseTakesPrecedence() async {
        let camera = FakeCamera(), vision = FakeVision()
        let rig = Rig.idle(camera: camera, vision: vision)
        rig.speak(600)
        rig.wake.hear()
        rig.wake.caption("hey nova what do you see")
        for _ in 0..<20 { await Task.yield() }
        rig.silence(1500)
        rig.scheduler.advance(3)
        XCTAssertEqual(pulses(rig), 0, "only the waiting pulse while the photo is on its way")
        XCTAssertGreaterThan(rig.earcons.played.filter { $0 == .waiting }.count, 0)

        camera.complete()
        for _ in 0..<20 { await Task.yield() }
        rig.scheduler.advance(ConversationController.thinkingGraceSeconds + 0.01)
        XCTAssertEqual(pulses(rig), 1, "then Nova is thinking")
    }
}
