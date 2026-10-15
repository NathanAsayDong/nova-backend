@preconcurrency import AVFoundation
import XCTest
@testable import NovaGlasses

final class AudioSessionPolicyTests: XCTestCase {
    func testVoiceKeepsTheStableCallSetup() {
        XCTAssertEqual(AudioSessionPolicy.voice.mode, .voiceChat)
        XCTAssertTrue(AudioSessionPolicy.voice.voiceProcessing)
    }

    func testSessionMixesWithOtherAudio() {
        XCTAssertTrue(AudioSessionPolicy.options.contains(.mixWithOthers))
        XCTAssertTrue(AudioSessionPolicy.options.contains(.allowBluetooth))
        XCTAssertFalse(AudioSessionPolicy.options.contains(.duckOthers))
    }
}

final class PlaybackWatchdogTests: XCTestCase {
    func testNothingWaitingIsNeverStalled() {
        var watchdog = PlaybackWatchdog()
        XCTAssertFalse(watchdog.isStalled(now: 100, waiting: false, engineRunning: true, headDuration: 0.5))
    }

    func testPlayingWithinTheBuffersLengthIsFine() {
        var watchdog = PlaybackWatchdog()
        watchdog.progressed(at: 10)
        XCTAssertFalse(watchdog.isStalled(now: 13, waiting: true, engineRunning: true, headDuration: 1))
    }

    func testNoProgressPastTheBufferAndGraceIsAStall() {
        var watchdog = PlaybackWatchdog()
        watchdog.progressed(at: 10)
        XCTAssertTrue(watchdog.isStalled(now: 14.1, waiting: true, engineRunning: true, headDuration: 1))
    }

    func testProgressResetsTheClock() {
        var watchdog = PlaybackWatchdog()
        watchdog.progressed(at: 10)
        watchdog.progressed(at: 13.5)
        XCTAssertFalse(watchdog.isStalled(now: 14.1, waiting: true, engineRunning: true, headDuration: 1))
    }

    func testEngineDownGetsItsOwnLongerLimit() {
        var watchdog = PlaybackWatchdog()
        watchdog.progressed(at: 0)
        XCTAssertFalse(watchdog.isStalled(now: 20, waiting: true, engineRunning: false, headDuration: 1))
        XCTAssertFalse(watchdog.isStalled(now: 27, waiting: true, engineRunning: false, headDuration: 1))
        XCTAssertTrue(watchdog.isStalled(now: 28, waiting: true, engineRunning: false, headDuration: 1))
    }

    func testEngineComingBackClearsTheDownClock() {
        var watchdog = PlaybackWatchdog()
        XCTAssertFalse(watchdog.isStalled(now: 0, waiting: true, engineRunning: false, headDuration: 1))
        watchdog.progressed(at: 5)
        XCTAssertFalse(watchdog.isStalled(now: 6, waiting: true, engineRunning: true, headDuration: 1))
        XCTAssertNil(watchdog.engineDownSince)
    }
}
