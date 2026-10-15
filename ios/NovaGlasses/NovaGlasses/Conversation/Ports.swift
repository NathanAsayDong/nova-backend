import Foundation

/// The seams ConversationController talks through, so the state machine can be
/// driven in tests with fakes instead of a socket, a speaker and a recognizer.

enum SocketConnectionState: Equatable, Sendable {
    case disconnected
    case connecting
    case connected
    /// The server refused the token (close 4401 / HTTP 401-403). Needs a login.
    case unauthorized
}

@MainActor
protocol NovaSocketing: AnyObject {
    var isOpen: Bool { get }
    var onEvent: ((ServerEvent) -> Void)? { get set }
    var onStateChange: ((SocketConnectionState) -> Void)? { get set }
    func connect()
    func disconnect()
    @discardableResult func send(_ event: ClientEvent) -> Bool
    @discardableResult func sendAudio(_ data: Data) -> Bool
}

@MainActor
protocol SpeechPlaying: AnyObject {
    /// Something is queued or playing.
    var isBusy: Bool { get }
    /// The queue ran dry: every started stream has ended and finished playing.
    var onDrained: (() -> Void)? { get set }
    func beginStream(_ streamId: String)
    func appendChunk(_ streamId: String, data: Data)
    func endStream(_ streamId: String)
    /// Barge-in: drop everything queued and stop the current sound now.
    func stopAll()
}

enum Earcon: String, CaseIterable, Sendable {
    /// Rising fifth: "I heard you, go ahead."
    case wake
    /// One soft tick: the turn went to the server.
    case thinking
    /// Falling fifth: "Finished, back to waiting."
    case done
    /// One low, quiet note: "Never mind."
    case cancel
    /// Two low notes: something failed.
    case error
}

@MainActor
protocol EarconPlaying: AnyObject {
    func play(_ earcon: Earcon)
}

/// Watches the microphone for "Hey Nova", one utterance at a time. The
/// controller opens an utterance at the turn detector's onset (seeded with the
/// pre-roll) so a phrase-level "starts with the wake phrase" check is possible.
@MainActor
protocol WakeDetecting: AnyObject {
    var onWake: (() -> Void)? { get set }
    /// Begin recognizing a new utterance. `seed` is 16 kHz mono Int16 PCM.
    func beginUtterance(seed: Data)
    /// More audio for the open utterance (same format).
    func feed(_ pcm: Data)
    /// No more audio is coming; a late final result may still fire `onWake`.
    func endUtterance()
    /// Drop the utterance; nothing more will fire for it.
    func cancel()
}

@MainActor
protocol Cancellable: AnyObject {
    func cancel()
}

@MainActor
protocol Scheduling: AnyObject {
    @discardableResult
    func after(_ seconds: Double, _ block: @escaping @MainActor @Sendable () -> Void) -> Cancellable
}

/// Real scheduler: main-actor tasks that sleep.
@MainActor
final class MainScheduler: Scheduling {
    private final class Handle: Cancellable {
        var task: Task<Void, Never>?
        func cancel() { task?.cancel() }
    }

    func after(_ seconds: Double, _ block: @escaping @MainActor @Sendable () -> Void) -> Cancellable {
        let handle = Handle()
        handle.task = Task { @MainActor in
            try? await Task.sleep(nanoseconds: UInt64(max(0, seconds) * 1_000_000_000))
            guard !Task.isCancelled else { return }
            block()
        }
        return handle
    }
}

/// The conversation the voice turns continue, kept across launches the same
/// way the web client keeps it in localStorage. Cleared when the server says
/// the conversation is closed.
final class ConversationIdStore {
    private let defaults: UserDefaults
    private let key = "nova.conversationId"

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    func load() -> String? {
        guard let value = defaults.string(forKey: key), !value.isEmpty else { return nil }
        return value
    }

    func save(_ id: String) {
        guard !id.isEmpty else { return }
        defaults.set(id, forKey: key)
    }

    func clear() {
        defaults.removeObject(forKey: key)
    }
}
