import Foundation

/// `VisionUploading` over the HTTP API, with the current server and token.
@MainActor
final class VisionClient: VisionUploading {
    /// Late-bound so a server or token change applies to the next upload.
    var api: () -> APIClient

    init(api: @escaping () -> APIClient) {
        self.api = api
    }

    func upload(_ jpeg: Data, requestId: String?) async throws -> String {
        let started = ProcessInfo.processInfo.systemUptime
        let imageId = try await api().uploadImage(jpeg, requestId: requestId)
        let ms = Int((ProcessInfo.processInfo.systemUptime - started) * 1000)
        AudioLog.shared.add("Photo uploaded: \(jpeg.count / 1024) KB in \(ms) ms")
        return imageId
    }

    func reportCaptureFailed(requestId: String, reason: String) async {
        AudioLog.shared.add("Photo for Nova failed: \(reason)")
        try? await api().reportCaptureFailed(requestId: requestId, reason: reason)
    }
}
