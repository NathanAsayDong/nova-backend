import Foundation

/// The voice WebSocket, /ws/transcribe.
///
///  - Sends the bearer token on the upgrade request. A refused token closes
///    the socket with 4401 before the handshake completes (or fails the
///    upgrade with 401/403), which is reported as `.unauthorized` and not
///    retried.
///  - Counts as open once the server's `ready` arrives: it is the first thing
///    the server sends after accepting.
///  - Pings every 20 s so idle proxies (the Cloudflare tunnel) keep it up.
///  - Reconnects with a 1/2/5/10/30 s backoff while `connect()` is in effect.
@MainActor
final class NovaSocket: NovaSocketing {
    static let pingInterval: Double = 20
    static let reconnectDelays: [Double] = [1, 2, 5, 10, 30]
    static let unauthorizedCloseCode = 4401

    var onEvent: ((ServerEvent) -> Void)?
    var onStateChange: ((SocketConnectionState) -> Void)?
    private(set) var isOpen = false

    /// Read on every connect, so a server or token change applies next time.
    var baseURL: () -> URL
    var token: () -> String?
    private let session: URLSession
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()

    private var task: URLSessionWebSocketTask?
    private var wantConnected = false
    private var reconnectAttempt = 0
    private var reconnectTask: Task<Void, Never>?
    private var pingTask: Task<Void, Never>?

    init(
        baseURL: @escaping () -> URL,
        token: @escaping () -> String?,
        session: URLSession = .shared
    ) {
        self.baseURL = baseURL
        self.token = token
        self.session = session
    }

    static func socketURL(for base: URL) -> URL {
        var components = URLComponents(url: base, resolvingAgainstBaseURL: false)!
        components.scheme = components.scheme == "http" ? "ws" : "wss"
        components.path = "/ws/transcribe"
        return components.url!
    }

    func connect() {
        wantConnected = true
        guard task == nil else { return }
        reconnectTask?.cancel()
        open()
    }

    func disconnect() {
        wantConnected = false
        reconnectTask?.cancel()
        reconnectTask = nil
        reconnectAttempt = 0
        let closing = task
        task = nil
        closing?.cancel(with: .normalClosure, reason: nil)
        markClosed(.disconnected)
    }

    @discardableResult
    func send(_ event: ClientEvent) -> Bool {
        guard isOpen, let task, let data = try? encoder.encode(event),
              let text = String(data: data, encoding: .utf8) else { return false }
        task.send(.string(text)) { @Sendable _ in }
        return true
    }

    @discardableResult
    func sendAudio(_ data: Data) -> Bool {
        guard isOpen, let task else { return false }
        task.send(.data(data)) { @Sendable _ in }
        return true
    }

    // MARK: - Lifecycle

    private func open() {
        guard let token = token(), !token.isEmpty else {
            onStateChange?(.unauthorized)
            wantConnected = false
            return
        }
        var request = URLRequest(url: Self.socketURL(for: baseURL()))
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.timeoutInterval = 10
        let task = session.webSocketTask(with: request)
        self.task = task
        onStateChange?(.connecting)
        task.resume()
        receive(on: task)
    }

    private func receive(on task: URLSessionWebSocketTask) {
        Task { @MainActor [weak self] in
            while true {
                let message: URLSessionWebSocketTask.Message
                do {
                    message = try await task.receive()
                } catch {
                    self?.closed(task)
                    return
                }
                guard let self, self.task === task else { return }
                self.handle(message)
            }
        }
    }

    private func handle(_ message: URLSessionWebSocketTask.Message) {
        let data: Data
        switch message {
        case .string(let text): data = Data(text.utf8)
        case .data(let bytes): data = bytes
        @unknown default: return
        }
        guard let event = try? decoder.decode(ServerEvent.self, from: data) else { return }
        if !isOpen {
            isOpen = true
            reconnectAttempt = 0
            startPinging()
            onStateChange?(.connected)
        }
        onEvent?(event)
    }

    private func closed(_ closedTask: URLSessionWebSocketTask) {
        guard task === closedTask else { return }
        task = nil
        let status = (closedTask.response as? HTTPURLResponse)?.statusCode
        let refused = closedTask.closeCode.rawValue == Self.unauthorizedCloseCode
            || status == 401 || status == 403
        if refused {
            wantConnected = false
            markClosed(.unauthorized)
            return
        }
        markClosed(.disconnected)
        scheduleReconnect()
    }

    private func markClosed(_ state: SocketConnectionState) {
        isOpen = false
        pingTask?.cancel()
        pingTask = nil
        onStateChange?(state)
    }

    private func scheduleReconnect() {
        guard wantConnected else { return }
        let delays = Self.reconnectDelays
        let delay = delays[min(reconnectAttempt, delays.count - 1)]
        reconnectAttempt += 1
        reconnectTask?.cancel()
        reconnectTask = Task { @MainActor [weak self] in
            try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            guard let self, !Task.isCancelled, self.wantConnected, self.task == nil else { return }
            self.open()
        }
    }

    /// Reconnect now rather than at the next backoff step (network came back,
    /// app returned to the foreground).
    func reconnectIfDown() {
        guard wantConnected, task == nil else { return }
        reconnectTask?.cancel()
        reconnectAttempt = 0
        open()
    }

    private func startPinging() {
        pingTask?.cancel()
        pingTask = Task { @MainActor [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: UInt64(Self.pingInterval * 1_000_000_000))
                guard let self, !Task.isCancelled else { return }
                self.send(.ping)
            }
        }
    }
}
