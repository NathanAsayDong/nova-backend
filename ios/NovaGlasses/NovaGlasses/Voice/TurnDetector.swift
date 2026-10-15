import Foundation

/// Acoustic half of turn detection: deciding when the user started and stopped
/// talking, from the microphone level alone.
///
/// A faithful port of the web client's `turnDetector.ts`
/// (nova-frontend/src/features/nova/turnDetector.ts). Keep the two in step:
/// every constant and transition below has a reason documented there, and the
/// short version is repeated here.
///
///  - The noise floor is measured continuously and the thresholds ride on top
///    of it, so the same code works in a quiet room and next to a fan.
///  - Opening and closing use different thresholds (hysteresis).
///  - The silence window is variable, driven by the backend's semantic scorer
///    (`listening.endpointMs`, `partial_transcript.endpointMs`).
///  - Every rate constant is time-based: each EMA derives its alpha from the
///    actual elapsed time, so the frame cadence changes resolution, not
///    behaviour.
///  - Steady sound is not speech. "Speech" that stays statistically flat for a
///    couple of seconds ends the turn and becomes the new noise floor.
@MainActor
final class TurnDetector {
    enum TurnEndReason: String, Equatable {
        case silence
        case maxDuration = "max_duration"
        case steadyNoise = "steady_noise"
    }

    enum State: String, Equatable {
        /// Measuring the room. The gate cannot open yet.
        case calibrating
        /// No speech. The noise floor is being learned.
        case idle
        /// Level is above the open threshold but has not held long enough yet.
        case onset
        /// Speech in progress.
        case speaking
        /// Speech stopped; the silence window is running.
        case trailing
        /// A turn was force-ended; waiting for the level to drop before arming again.
        case cooldown
    }

    struct Snapshot: Equatable {
        var state: State
        var noiseFloor: Double
        var openThreshold: Double
        var closeThreshold: Double
        var silenceWindowMs: Double
    }

    /// Level crossed the open threshold — MAYBE speech. Fired before the onset
    /// hold confirms it, so capture can start without clipping the first
    /// syllable. Followed by `onSpeechStart` (real) or `onSpeechAbort` (a click).
    var onSpeechOnset: (() -> Void)?
    /// The onset was too brief to be speech, or the whole turn held too little
    /// speech to submit. Undo whatever onset started.
    var onSpeechAbort: (() -> Void)?
    var onSpeechStart: (() -> Void)?
    var onSpeechPause: (() -> Void)?
    var onSpeechResume: (() -> Void)?
    var onTurnEnd: ((TurnEndReason) -> Void)?
    var onSpeakingChange: ((Bool) -> Void)?

    /// Matches the backend's DEFAULT_SILENCE_MS at scale 1.0.
    static let defaultSilenceMs: Double = 1000
    static let minSpeechMs: Double = 120
    static let calibrationMs: Double = 650
    static let calibrationRampSkipMs: Double = 250
    static let maxUtteranceMs: Double = 30_000
    static let minTurnSpeechMs: Double = 250
    static let steadyNoiseMinMs: Double = 2_000
    static let steadyNoiseDevRatio: Double = 0.13
    static let steadyStatsTauMs: Double = 400
    static let openOverFloor: Double = 1.8
    static let closeOverFloor: Double = 1.3
    static let openMargin: Double = 0.008
    static let closeMargin: Double = 0.004
    static let minOpenLevel: Double = 0.015
    static let minCloseLevel: Double = 0.01
    static let maxOpenLevel: Double = 0.25
    static let floorFallTauMs: Double = 90
    static let floorRiseTauMs: Double = 700

    private(set) var state: State = .calibrating
    // A seed, not an assumption: calibration replaces it with a measurement.
    private(set) var noiseFloor: Double = 0.004
    private var lastPushAt: Double?
    private var calibrationStartedAt: Double?
    private var calibrationSum: Double = 0
    private var calibrationSamples = 0
    private var onsetStartedAt: Double = 0
    private var speechStartedAt: Double = 0
    // Speaking time across the whole turn, pauses excluded. Resets per turn.
    private var speechAccumMs: Double = 0
    private var silenceStartedAt: Double = 0
    private(set) var silenceWindowMs: Double = TurnDetector.defaultSilenceMs
    private var speakingReported = false
    private var steadySince: Double = 0
    private var steadyMean: Double = 0
    private var steadyDeviation: Double = 0

    init() {}

    var openThreshold: Double {
        min(Self.maxOpenLevel, max(Self.minOpenLevel, noiseFloor * Self.openOverFloor + Self.openMargin))
    }

    var closeThreshold: Double {
        max(Self.minCloseLevel, noiseFloor * Self.closeOverFloor + Self.closeMargin)
    }

    var snapshot: Snapshot {
        Snapshot(
            state: state,
            noiseFloor: noiseFloor,
            openThreshold: openThreshold,
            closeThreshold: closeThreshold,
            silenceWindowMs: silenceWindowMs
        )
    }

    /// EMA weight for a step of `dt` toward a time constant of `tau`.
    private static func alpha(_ dtMs: Double, _ tauMs: Double) -> Double {
        1 - exp(-dtMs / tauMs)
    }

    private func reportSpeaking(_ speaking: Bool) {
        guard speaking != speakingReported else { return }
        speakingReported = speaking
        onSpeakingChange?(speaking)
    }

    private func trackNoiseFloor(_ level: Double, _ dt: Double) {
        // Only while not in a turn: adapting during speech would learn the voice.
        let tau = level < noiseFloor ? Self.floorFallTauMs : Self.floorRiseTauMs
        noiseFloor += (level - noiseFloor) * Self.alpha(dt, tau)
    }

    private func enterSpeaking(now: Double, startedAt: Double) {
        state = .speaking
        speechStartedAt = startedAt
        steadySince = now
        steadyMean = 0
        steadyDeviation = 0
    }

    private func updateSteadyStats(_ level: Double, _ dt: Double) {
        let a = Self.alpha(dt, Self.steadyStatsTauMs)
        if steadyMean == 0 {
            // Seed the deviation high so the verdict needs sustained flatness.
            steadyMean = level
            steadyDeviation = level * 0.5
            return
        }
        steadyMean += (level - steadyMean) * a
        steadyDeviation += (abs(level - steadyMean) - steadyDeviation) * a
    }

    private func isSteadyNoise(_ now: Double) -> Bool {
        now - steadySince >= Self.steadyNoiseMinMs
            && steadyDeviation < steadyMean * Self.steadyNoiseDevRatio
    }

    private func endAsSteadyNoise() {
        // Machinery, not a person: learn the hum as the floor.
        noiseFloor = max(noiseFloor, steadyMean)
        state = .cooldown
        reportSpeaking(false)
        onTurnEnd?(.steadyNoise)
    }

    /// Feed one level sample. `level` is smoothed RMS in 0...1, `now` in ms.
    func push(level: Double, now: Double) {
        let dt = lastPushAt.map { max(1, now - $0) } ?? 25
        lastPushAt = now

        let open = openThreshold
        let close = closeThreshold

        switch state {
        case .calibrating:
            if calibrationStartedAt == nil {
                calibrationStartedAt = now
            }
            let elapsed = now - (calibrationStartedAt ?? now)
            if elapsed >= Self.calibrationRampSkipMs {
                calibrationSum += level
                calibrationSamples += 1
            }
            if elapsed >= Self.calibrationMs {
                if calibrationSamples > 0 {
                    noiseFloor = calibrationSum / Double(calibrationSamples)
                }
                state = .idle
            }

        case .cooldown:
            trackNoiseFloor(level, dt)
            if level <= close {
                state = .idle
            }

        case .idle:
            trackNoiseFloor(level, dt)
            if level > open {
                state = .onset
                onsetStartedAt = now
                speechAccumMs = 0
                // A fresh utterance: start from a neutral window.
                silenceWindowMs = Self.defaultSilenceMs
                onSpeechOnset?()
            }

        case .onset:
            if level <= close {
                // Too brief to be speech — a click or a knock.
                state = .idle
                trackNoiseFloor(level, dt)
                onSpeechAbort?()
                return
            }
            if now - onsetStartedAt >= Self.minSpeechMs {
                // Bank the onset window too, or a short "yes" gets discarded.
                speechAccumMs += now - onsetStartedAt
                enterSpeaking(now: now, startedAt: onsetStartedAt)
                reportSpeaking(true)
                onSpeechStart?()
            }

        case .speaking:
            speechAccumMs += dt
            updateSteadyStats(level, dt)
            if isSteadyNoise(now) {
                endAsSteadyNoise()
                return
            }
            if now - speechStartedAt >= Self.maxUtteranceMs {
                state = .cooldown
                reportSpeaking(false)
                onTurnEnd?(.maxDuration)
                return
            }
            if level < close {
                state = .trailing
                silenceStartedAt = now
                reportSpeaking(false)
                onSpeechPause?()
            }

        case .trailing:
            if level > open {
                // A pause inside a sentence. New words invalidate a SHORTENED
                // window; a lengthened one keeps its hold.
                enterSpeaking(now: now, startedAt: speechStartedAt)
                silenceWindowMs = max(silenceWindowMs, Self.defaultSilenceMs)
                reportSpeaking(true)
                onSpeechResume?()
                return
            }
            if now - speechStartedAt >= Self.maxUtteranceMs {
                state = .cooldown
                onTurnEnd?(.maxDuration)
                return
            }
            if now - silenceStartedAt >= silenceWindowMs {
                state = .idle
                if speechAccumMs < Self.minTurnSpeechMs {
                    // Not enough speech in the whole turn to be an utterance.
                    onSpeechAbort?()
                    return
                }
                onTurnEnd?(.silence)
            }
        }
    }

    /// How long silence must last to end the turn. Driven by the backend.
    func setSilenceWindow(_ ms: Double) {
        if ms.isFinite && ms > 0 {
            silenceWindowMs = ms
        }
    }

    /// Forget the turn in progress. Keeps the learned noise floor.
    func reset() {
        state = state == .calibrating ? .calibrating : .idle
        silenceWindowMs = Self.defaultSilenceMs
        reportSpeaking(false)
    }
}

/// The level the detector is fed: RMS amplified and smoothed with a ~90 ms
/// time constant, the same transform the web client applies before `push`.
struct LevelSmoother {
    static let gain: Double = 2.8
    static let tauMs: Double = 90

    private(set) var value: Double = 0
    private var lastAt: Double?

    mutating func apply(rms: Double, now: Double) -> Double {
        let amplified = min(1, rms * Self.gain)
        let dt = lastAt.map { max(1, now - $0) } ?? 25
        lastAt = now
        value += (amplified - value) * (1 - exp(-dt / Self.tauMs))
        return value
    }
}
