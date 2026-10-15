import XCTest
@testable import NovaGlasses

// MARK: - Fakes

@MainActor
final class FakeCamera: GlassesCamera {
    var state: GlassesCameraState = .ready
    private(set) var captures = 0
    private var pending: CheckedContinuation<Data, Error>?

    func capturePhoto() async throws -> Data {
        captures += 1
        return try await withCheckedThrowingContinuation { pending = $0 }
    }

    func complete(_ jpeg: Data = Data([0xFF, 0xD8, 0xFF])) {
        pending?.resume(returning: jpeg)
        pending = nil
    }

    func fail() {
        pending?.resume(throwing: DATGlassesCamera.CameraError.timeout("the photo"))
        pending = nil
    }
}

@MainActor
final class FakeVision: VisionUploading {
    private(set) var uploads: [(bytes: Int, requestId: String?)] = []
    private(set) var failures: [(requestId: String, reason: String)] = []

    func upload(_ jpeg: Data, requestId: String?) async throws -> String {
        uploads.append((jpeg.count, requestId))
        return "img-\(uploads.count)"
    }

    func reportCaptureFailed(requestId: String, reason: String) async {
        failures.append((requestId, reason))
    }
}

/// Lets the photo tasks the controller starts run to their next await.
@MainActor
private func settle() async {
    for _ in 0..<20 {
        await Task.yield()
    }
}

// MARK: - Intent

final class VisionIntentTests: XCTestCase {
    func testAsksToLook() {
        for caption in [
            "Hey Nova, what do you see?",
            "hey nova what am I looking at",
            "Nova, who's this?",
            "Who is that over there",
            "what’s this thing",
            "can you read this sign for me",
            "take a look at my screen",
            "do you recognize him",
        ] {
            XCTAssertTrue(VisionIntent.wantsToSee(caption), caption)
        }
    }

    func testOrdinaryRequestsDoNotTakePhotos() {
        for caption in [
            "Hey Nova, what time is it?",
            "what's the weather",
            "remind me to look into flights",
            "see you later",
            "this is great",
            "who won the game",
        ] {
            XCTAssertFalse(VisionIntent.wantsToSee(caption), caption)
        }
    }
}

// MARK: - Controller

@MainActor
final class VisionControllerTests: XCTestCase {
    typealias Rig = ConversationControllerTests.Rig

    private func wokenRig(_ camera: FakeCamera, _ vision: FakeVision) -> Rig {
        let rig = Rig.idle(camera: camera, vision: vision)
        rig.speak(600)
        rig.wake.hear()
        XCTAssertEqual(rig.controller.phase, .listening)
        return rig
    }

    func testAskingToLookTakesThePhotoAndStopWaitsForIt() async {
        let camera = FakeCamera(), vision = FakeVision()
        let rig = wokenRig(camera, vision)
        rig.socket.emit(.partialTranscript(text: "hey nova what do you see", seq: 1, endpointMs: nil))
        await settle()
        XCTAssertEqual(camera.captures, 1)

        rig.speak(300)
        rig.silence(1500)
        XCTAssertEqual(rig.controller.phase, .thinking)
        XCTAssertFalse(rig.socket.log.contains("stop"), "stop waits for the photo")

        camera.complete()
        await settle()
        XCTAssertEqual(vision.uploads.map(\.requestId), [nil])
        XCTAssertEqual(rig.socket.events.last, .stop(purpose: .sentry, conversationId: nil, imageIds: ["img-1"]))
        XCTAssertTrue(rig.earcons.played.contains(.shutter))
    }

    func testAPhotoAlreadyUploadedGoesOutWithTheStop() async {
        let camera = FakeCamera(), vision = FakeVision()
        let rig = wokenRig(camera, vision)
        rig.socket.emit(.partialTranscript(text: "who is this", seq: 1, endpointMs: nil))
        await settle()
        camera.complete()
        await settle()
        rig.silence(1500)
        XCTAssertEqual(rig.socket.events.last, .stop(purpose: .sentry, conversationId: nil, imageIds: ["img-1"]))
    }

    func testASlowPhotoIsLeftBehind() async {
        let camera = FakeCamera(), vision = FakeVision()
        let rig = wokenRig(camera, vision)
        rig.socket.emit(.partialTranscript(text: "what am I looking at", seq: 1, endpointMs: nil))
        await settle()
        rig.silence(1500)
        XCTAssertFalse(rig.socket.log.contains("stop"))
        rig.scheduler.advance(ConversationController.photoWaitSeconds)
        XCTAssertEqual(rig.socket.events.last, .stop(purpose: .sentry, conversationId: nil, imageIds: []))

        camera.complete()
        await settle()
        XCTAssertEqual(rig.socket.log.filter { $0 == "stop" }.count, 1, "never a second stop")
    }

    func testAFailedPhotoStillEndsTheTurn() async {
        let camera = FakeCamera(), vision = FakeVision()
        let rig = wokenRig(camera, vision)
        rig.socket.emit(.partialTranscript(text: "what do you see", seq: 1, endpointMs: nil))
        await settle()
        rig.silence(1500)
        camera.fail()
        await settle()
        XCTAssertEqual(rig.socket.events.last, .stop(purpose: .sentry, conversationId: nil, imageIds: []))
        XCTAssertTrue(vision.uploads.isEmpty)
    }

    func testOrdinaryCaptionsAndAnUnreadyCameraTakeNoPhoto() async {
        let camera = FakeCamera(), vision = FakeVision()
        let rig = wokenRig(camera, vision)
        rig.socket.emit(.partialTranscript(text: "what time is it", seq: 1, endpointMs: nil))
        camera.state = .unregistered
        rig.socket.emit(.partialTranscript(text: "what time is it, what do you see", seq: 2, endpointMs: nil))
        await settle()
        XCTAssertEqual(camera.captures, 0)
        rig.silence(1500)
        XCTAssertEqual(rig.socket.events.last, .stop(purpose: .sentry, conversationId: nil))
    }

    func testCaptureRequestUploadsWithItsRequestId() async {
        let camera = FakeCamera(), vision = FakeVision()
        let rig = Rig.thinking()
        let controller = ConversationController(
            socket: rig.socket, player: rig.player, earcons: rig.earcons, wake: rig.wake,
            scheduler: rig.scheduler, conversationIds: rig.ids, camera: camera, vision: vision
        )
        controller.setEnabled(true)
        rig.socket.emit(.captureRequest(requestId: "req-7", conversationId: "conv-1"))
        await settle()
        camera.complete()
        await settle()
        XCTAssertEqual(vision.uploads.map(\.requestId), ["req-7"])
        XCTAssertTrue(vision.failures.isEmpty)
    }

    func testCaptureRequestWithoutACameraReportsFailure() async {
        let camera = FakeCamera(), vision = FakeVision()
        camera.state = .unregistered
        let rig = Rig.idle(camera: camera, vision: vision)
        rig.socket.emit(.captureRequest(requestId: "req-8", conversationId: nil))
        await settle()
        XCTAssertEqual(vision.failures.map(\.requestId), ["req-8"])
        XCTAssertEqual(camera.captures, 0)
    }
}
