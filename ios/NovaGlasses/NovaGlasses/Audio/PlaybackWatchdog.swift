import Foundation

/// Decides when Nova's playback has stalled for good.
///
/// Scheduled audio can vanish without its completion ever firing: the engine
/// stops for an interruption or a route change, or the output goes away. The
/// player then believes it is still speaking and the conversation waits
/// forever in silence. This notices and lets the player give up cleanly.
struct PlaybackWatchdog {
    /// Grace beyond the head buffer's own length before progress counts as stuck.
    static let stallGrace: Double = 3
    /// How long audio may sit unplayed while the engine is down.
    static let engineDownLimit: Double = 8

    /// When a buffer last finished, or audio was last queued (monotonic seconds).
    var lastProgress: Double = 0
    /// When the engine was seen not running with audio waiting; nil if running.
    var engineDownSince: Double?

    mutating func progressed(at now: Double) {
        lastProgress = now
    }

    /// - Parameters:
    ///   - waiting: audio is queued or playing.
    ///   - engineRunning: the engine is up, so queued audio should be moving.
    ///   - headDuration: length in seconds of the buffer that should be playing.
    mutating func isStalled(now: Double, waiting: Bool, engineRunning: Bool, headDuration: Double) -> Bool {
        guard waiting else {
            engineDownSince = nil
            return false
        }
        if !engineRunning {
            let since = engineDownSince ?? now
            engineDownSince = since
            return now - since >= Self.engineDownLimit
        }
        engineDownSince = nil
        return now - lastProgress >= headDuration + Self.stallGrace
    }
}
