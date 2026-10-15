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

    /// A request whose body is raw bytes (a JPEG), with optional query items.
    private func upload(_ path: String, body: Data, contentType: String, query: [URLQueryItem] = []) -> URLRequest {
        var components = URLComponents(url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: false)!
        if !query.isEmpty {
            components.queryItems = query
        }
        var request = URLRequest(url: components.url!)
        request.httpMethod = "POST"
        request.timeoutInterval = 20
        if let token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        request.httpBody = body
        return request
    }

    private func perform(_ request: URLRequest) async throws -> [String: Any] {
        try await performAny(request) as? [String: Any] ?? [:]
    }

    private func performAny(_ request: URLRequest) async throws -> Any {
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw APIError.badResponse }
        let json = (try? JSONSerialization.jsonObject(with: data)) ?? [String: Any]()
        if http.statusCode == 401 { throw APIError.unauthorized }
        guard (200..<300).contains(http.statusCode) else {
            let detail = (json as? [String: Any])?["detail"]
            throw APIError.server(status: http.statusCode, detail: detail as? String ?? "\(detail ?? "")")
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

    // MARK: - Vision

    /// POST /vision/images: a glasses photo → its id for `stop.imageIds`.
    /// `requestId` answers a `capture_request` from Nova's `look` tool.
    func uploadImage(_ jpeg: Data, requestId: String?) async throws -> String {
        let query = requestId.map { [URLQueryItem(name: "requestId", value: $0)] } ?? []
        let json = try await perform(upload("vision/images", body: jpeg, contentType: "image/jpeg", query: query))
        guard let imageId = json["imageId"] as? String else { throw APIError.badResponse }
        return imageId
    }

    func reportCaptureFailed(requestId: String, reason: String) async throws {
        _ = try await perform(request("vision/capture-failed", method: "POST", body: [
            "requestId": requestId,
            "reason": reason,
        ]))
    }

    // MARK: - Faces

    struct Person: Identifiable, Equatable, Sendable {
        let id: String
        let name: String
        let samples: Int
    }

    func people() async throws -> [Person] {
        let json = try await performAny(request("faces/people", method: "GET"))
        let rows = (json as? [[String: Any]]) ?? ((json as? [String: Any])?["people"] as? [[String: Any]]) ?? []
        return rows.compactMap { row in
            guard let id = row["id"].map({ "\($0)" }), let name = row["name"] as? String else { return nil }
            return Person(id: id, name: name, samples: row["samples"] as? Int ?? 0)
        }
    }

    /// Enroll someone. `consent` must be true: they agreed to be recognized.
    func addPerson(name: String, consent: Bool) async throws -> Person {
        let json = try await perform(request("faces/people", method: "POST", body: [
            "name": name,
            "consent": consent,
        ]))
        guard let id = json["id"].map({ "\($0)" }) else { throw APIError.badResponse }
        return Person(id: id, name: json["name"] as? String ?? name, samples: json["samples"] as? Int ?? 0)
    }

    func deletePerson(id: String) async throws {
        _ = try await perform(request("faces/people/\(id)", method: "DELETE"))
    }

    /// One photo of that person's face → their sample count. The server
    /// rejects photos without exactly one clear face (422, with the reason).
    func addFaceSample(personId: String, jpeg: Data) async throws -> Int {
        let json = try await perform(upload("faces/people/\(personId)/samples", body: jpeg, contentType: "image/jpeg"))
        return json["samples"] as? Int ?? 0
    }
}
