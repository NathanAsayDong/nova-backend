import Foundation
import Observation

/// A short in-memory history of what the audio stack did: route and mode
/// changes, interruptions, engine restarts, playback stalls. Shown on the
/// Audio log screen so "the audio got weird" comes with a record of why.
@MainActor
@Observable
final class AudioLog {
    static let shared = AudioLog()
    static let capacity = 100

    struct Entry: Identifiable, Sendable {
        let id: Int
        let time: Date
        let text: String
    }

    private(set) var entries: [Entry] = []
    @ObservationIgnored private var nextId = 0

    func add(_ text: String) {
        entries.append(Entry(id: nextId, time: Date(), text: text))
        nextId += 1
        if entries.count > Self.capacity {
            entries.removeFirst(entries.count - Self.capacity)
        }
        print("[audio] \(text)")
    }

    /// Plain text, newest last, for pasting into a bug report.
    func export() -> String {
        let format = Date.FormatStyle().hour().minute().second()
        return entries.map { "\($0.time.formatted(format))  \($0.text)" }.joined(separator: "\n")
    }
}
