import Foundation

/// The few HTTP routes the glasses client needs.
struct APIClient: Sendable {
    enum APIError: LocalizedError {
        case unauthorized
        case server(status: Int, detail: String)
        case badResponse

        var errorDescription: String? {
            switch self {
            case .unauthorized: "Wrong username or password, or the session expired."
            case .server(let status, let detail): "Server error \(status): \(detail)"
            case .badResponse: "Unexpected response from the server."
            }
        }
    }

    var baseURL: URL
    var token: String?
    var session: URLSession = .shared

    private func request(_ path: String, method: String, body: [String: Any]? = nil) throws -> URLRequest {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = method
        request.timeoutInterval = 15
        if let token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
        }
        return request
    }

    private func perform(_ request: URLRequest) async throws -> [String: Any] {
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw APIError.badResponse }
        let json = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] ?? [:]
        if http.statusCode == 401 { throw APIError.unauthorized }
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.server(status: http.statusCode, detail: json["detail"] as? String ?? "")
        }
        return json
    }

    /// POST /auth/login → the bearer token.
    func login(username: String, password: String) async throws -> String {
        let json = try await perform(request("auth/login", method: "POST", body: [
            "username": username,
            "password": password,
        ]))
        guard let token = json["token"] as? String else { throw APIError.badResponse }
        return token
    }

    func logout() async throws {
        _ = try await perform(request("auth/logout", method: "POST"))
    }

    /// GET /nova/power: whether Nova is allowed to listen (shared with the web UI).
    func power() async throws -> Bool {
        let json = try await perform(request("nova/power", method: "GET"))
        return json["enabled"] as? Bool ?? false
    }

    @discardableResult
    func setPower(_ enabled: Bool) async throws -> Bool {
        let json = try await perform(request("nova/power", method: "POST", body: ["enabled": enabled]))
        return json["enabled"] as? Bool ?? enabled
    }
}
