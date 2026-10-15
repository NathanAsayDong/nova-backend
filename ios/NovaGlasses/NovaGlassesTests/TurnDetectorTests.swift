import XCTest
@testable import NovaGlasses

/// Behaviour of the TurnDetector port, case by case against the rules in the
/// web client's turnDetector.ts.
@MainActor
final class TurnDetectorTests: XCTestCase {
    /// Records callbacks and drives the detector on a fake clock.
    @MainActor
    final class Harness {
        let detector = TurnDetector()
        var events: [String] = []
        var now: Double = 0

        init() {
            detector.onSpeechOnset = { [unowned self] in events.append("onset") }
            detector.onSpeechAbort = { [unowned self] in events.append("abort") }
            detector.onSpeechStart = { [unowned self] in events.append("start") }
            detector.onSpeechPause = { [unowned self] in events.append("pause") }
            detector.onSpeechResume = { [unowned self] in events.append("resume") }
            detector.onTurnEnd = { [unowned self] reason in events.append("end:\(reason.rawValue)") }
            detector.onSpeakingChange = { [unowned self] speaking in events.append(speaking ? "speaking" : "quiet") }
        }

        /// Feed a constant level for `ms`, one sample per `tick`.
        func hold(_ level: Double, for ms: Double, tick: Double = 20) {
            let end = now + ms
            while now < end {
                now += tick
                detector.push(level: level, now: now)
            }
        }

        /// Speech-like level: modulated at syllable rate around `mean`.
        func speak(for ms: Double, mean: Double = 0.2, tick: Double = 20) {
            let end = now + ms
            while now < end {
                now += tick
                let level = mean + mean * 0.5 * sin(2 * .pi * 5 * now / 1000)
                detector.push(level: level, now: now)
            }
        }

        func calibrate(floor: Double = 0.002) {
            hold(floor, for: 700)
            events.removeAll()
        }
    }

    func testCalibrationMeasuresTheRoomAfterTheRamp() {
        let h = Harness()
        // Ramp: zero for the skipped 250 ms, then the room at 0.01.
        h.hold(0, for: 240)
        XCTAssertEqual(h.detector.state, .calibrating)
        h.hold(0.01, for: 460)
        XCTAssertEqual(h.detector.state, .idle)
        XCTAssertEqual(h.detector.noiseFloor, 0.01, accuracy: 0.0005)
    }

    func testGateCannotOpenWhileCalibrating() {
        let h = Harness()
        h.hold(0.5, for: 400)
        XCTAssertFalse(h.events.contains("onset"))
    }

    func testThresholdsHaveAbsoluteMinimumsInAQuietRoom() {
        let h = Harness()
        h.calibrate(floor: 0.0)
        XCTAssertEqual(h.detector.openThreshold, TurnDetector.minOpenLevel, accuracy: 1e-9)
        XCTAssertEqual(h.detector.closeThreshold, TurnDetector.minCloseLevel, accuracy: 1e-9)
    }

    func testThresholdsRideOnALoudFloorWithHysteresis() {
        let h = Harness()
        h.calibrate(floor: 0.05)
        let floor = h.detector.noiseFloor
        XCTAssertEqual(h.detector.openThreshold, floor * 1.8 + 0.008, accuracy: 1e-6)
        XCTAssertEqual(h.detector.closeThreshold, floor * 1.3 + 0.004, accuracy: 1e-6)
        XCTAssertGreaterThan(h.detector.openThreshold, h.detector.closeThreshold)
    }

    func testOpenThresholdIsCapped() {
        let h = Harness()
        h.calibrate(floor: 0.5)
        XCTAssertEqual(h.detector.openThreshold, TurnDetector.maxOpenLevel, accuracy: 1e-9)
    }

    func testAClickOpensThenAbortsWithoutStartingSpeech() {
        let h = Harness()
        h.calibrate()
        h.hold(0.3, for: 60)
        h.hold(0.002, for: 40)
        XCTAssertEqual(h.events, ["onset", "abort"])
    }

    func testSpeechStartsAfterTheOnsetHoldAndEndsAfterTheSilenceWindow() {
        let h = Harness()
        h.calibrate()
        h.speak(for: 600)
        XCTAssertEqual(Array(h.events.prefix(3)), ["onset", "speaking", "start"])
        h.hold(0.002, for: 980)
        XCTAssertFalse(h.events.contains { $0.hasPrefix("end") }, "ended before the 1 s window")
        h.hold(0.002, for: 100)
        XCTAssertEqual(h.events.suffix(3), ["quiet", "pause", "end:silence"])
    }

    func testOnsetFiresBeforeConfirmation() {
        let h = Harness()
        h.calibrate()
        h.hold(0.3, for: 20)
        XCTAssertEqual(h.events, ["onset"])
        h.hold(0.3, for: 100)
        XCTAssertEqual(h.events, ["onset"], "confirmation needs 120 ms")
        h.hold(0.3, for: 20)
        XCTAssertEqual(h.events, ["onset", "speaking", "start"])
    }

    func testAPauseInsideASentenceResumesInsteadOfEnding() {
        let h = Harness()
        h.calibrate()
        h.speak(for: 500)
        h.hold(0.002, for: 600)
        h.speak(for: 300)
        XCTAssertTrue(h.events.contains("pause"))
        XCTAssertTrue(h.events.contains("resume"))
        XCTAssertFalse(h.events.contains { $0.hasPrefix("end") })
    }

    func testBackendCanShortenTheSilenceWindow() {
        let h = Harness()
        h.calibrate()
        h.speak(for: 500)
        h.detector.setSilenceWindow(300)
        h.hold(0.002, for: 340)
        XCTAssertEqual(h.events.last, "end:silence")
    }

    func testInvalidSilenceWindowsAreIgnored() {
        let h = Harness()
        h.detector.setSilenceWindow(0)
        h.detector.setSilenceWindow(-5)
        h.detector.setSilenceWindow(.nan)
        XCTAssertEqual(h.detector.silenceWindowMs, TurnDetector.defaultSilenceMs)
    }

    func testNewWordsUndoAShortenedWindowButKeepALengthenedOne() {
        let h = Harness()
        h.calibrate()
        h.speak(for: 400)
        h.hold(0.002, for: 100)
        h.detector.setSilenceWindow(300)
        h.speak(for: 200)
        XCTAssertEqual(h.detector.silenceWindowMs, TurnDetector.defaultSilenceMs)

        h.hold(0.002, for: 100)
        h.detector.setSilenceWindow(2500)
        h.speak(for: 200)
        XCTAssertEqual(h.detector.silenceWindowMs, 2500)
    }

    func testAFreshUtteranceStartsWithANeutralWindow() {
        let h = Harness()
        h.calibrate()
        h.speak(for: 400)
        h.detector.setSilenceWindow(400)
        h.hold(0.002, for: 1500)
        XCTAssertEqual(h.events.last, "end:silence")
        h.speak(for: 200)
        XCTAssertEqual(h.detector.silenceWindowMs, TurnDetector.defaultSilenceMs)
    }

    func testTooLittleSpeechIsAbortedNotSubmitted() {
        let h = Harness()
        h.calibrate()
        // 160 ms of sound clears the 120 ms onset hold but not the 250 ms floor.
        h.hold(0.3, for: 160)
        h.hold(0.002, for: 1100)
        XCTAssertTrue(h.events.contains("start"))
        XCTAssertEqual(h.events.last, "abort")
        XCTAssertFalse(h.events.contains { $0.hasPrefix("end") })
    }

    func testAOneWordAnswerStillCounts() {
        let h = Harness()
        h.calibrate()
        h.hold(0.3, for: 320) // "yes"
        h.hold(0.002, for: 1100)
        XCTAssertEqual(h.events.last, "end:silence")
    }

    func testSteadyNoiseEndsTheTurnAndBecomesTheFloor() {
        let h = Harness()
        h.calibrate()
        h.hold(0.1, for: 2_400)
        XCTAssertEqual(h.events.last, "end:steady_noise")
        // The hum is now the floor, so it sits under the close threshold and
        // the cooldown releases at once…
        XCTAssertGreaterThanOrEqual(h.detector.noiseFloor, 0.09)
        XCTAssertEqual(h.detector.state, .idle)
        // …but the same hum cannot reopen the gate.
        h.events.removeAll()
        h.hold(0.1, for: 2_000)
        XCTAssertFalse(h.events.contains("onset"))
    }

    func testRealSpeechIsNotMistakenForSteadyNoise() {
        let h = Harness()
        h.calibrate()
        h.speak(for: 5_000)
        XCTAssertFalse(h.events.contains("end:steady_noise"))
    }

    func testATurnIsCappedAtThirtySeconds() {
        let h = Harness()
        h.calibrate()
        h.speak(for: 30_100)
        XCTAssertEqual(h.events.last, "end:max_duration")
        XCTAssertEqual(h.detector.state, .cooldown)
    }

    func testCooldownWaitsForTheLevelToDrop() {
        let h = Harness()
        h.calibrate()
        h.speak(for: 30_100)
        h.events.removeAll()
        h.hold(0.2, for: 300)
        XCTAssertEqual(h.detector.state, .cooldown)
        XCTAssertTrue(h.events.isEmpty)
        h.hold(0.002, for: 40)
        XCTAssertEqual(h.detector.state, .idle)
    }

    func testFloorFallsFastAndRisesSlowly() {
        let h = Harness()
        h.calibrate(floor: 0.008)
        h.hold(0.0, for: 200)
        XCTAssertLessThan(h.detector.noiseFloor, 0.008 * 0.15, "falls with a 90 ms time constant")

        let rising = Harness()
        rising.calibrate(floor: 0.002)
        rising.hold(0.012, for: 200) // below the open threshold
        XCTAssertLessThan(rising.detector.noiseFloor, 0.002 + 0.01 * 0.3, "rises with a 700 ms time constant")
    }

    func testRateConstantsAreTimeBasedNotPerCall() {
        func endTime(tick: Double) -> Double? {
            let h = Harness()
            h.calibrate()
            h.hold(0.3, for: 500, tick: tick)
            let start = h.now
            while h.now < start + 3000 {
                h.hold(0.002, for: tick, tick: tick)
                if h.events.last == "end:silence" { return h.now - start }
            }
            return nil
        }
        let fast = endTime(tick: 10)
        let slow = endTime(tick: 100)
        XCTAssertNotNil(fast)
        XCTAssertNotNil(slow)
        XCTAssertEqual(fast!, slow!, accuracy: 110)
    }

    func testResetKeepsTheFloorAndForgetsTheTurn() {
        let h = Harness()
        h.calibrate(floor: 0.03)
        h.speak(for: 300, mean: 0.3)
        h.detector.setSilenceWindow(2000)
        let floor = h.detector.noiseFloor
        h.detector.reset()
        XCTAssertEqual(h.detector.state, .idle)
        XCTAssertEqual(h.detector.noiseFloor, floor, accuracy: 1e-9)
        XCTAssertEqual(h.detector.silenceWindowMs, TurnDetector.defaultSilenceMs)
        XCTAssertEqual(h.events.last, "quiet")
    }

    func testResetDuringCalibrationFinishesCalibrating() {
        let h = Harness()
        h.hold(0.01, for: 300)
        h.detector.reset()
        XCTAssertEqual(h.detector.state, .calibrating)
    }

    func testLevelSmootherMatchesTheWebTransform() {
        var smoother = LevelSmoother()
        var level = 0.0
        for i in 1...100 {
            level = smoother.apply(rms: 0.1, now: Double(i) * 10)
        }
        XCTAssertEqual(level, 0.28, accuracy: 0.001, "settles at rms × 2.8")
        XCTAssertEqual(LevelSmoother().value, 0)
        var clipped = LevelSmoother()
        for i in 1...100 { level = clipped.apply(rms: 0.9, now: Double(i) * 10) }
        XCTAssertLessThanOrEqual(level, 1)
    }
}
