@preconcurrency import AVFoundation
import Foundation
import Observation
import UIKit
import UserNotifications

/// Wires the real audio, network and recognizer pieces to the
/// ConversationController, and owns the things the screen shows.
@MainActor
@Observable
final class AppModel {
    static let defaultBaseURL: URL = {
        let configured = Bundle.main.object(forInfoDictionaryKey: "NovaAPIBaseURL") as? String
        return URL(string: configured ?? "") ?? URL(string: "https://api.nova-api.us")!
    }()
    /// Disconnected from the glasses this long while listening: switch off.
    static let glassesGoneAutoOffSeconds: Double = 10 * 60

    private(set) var isLoggedIn: Bool
    private(set) var listeningEnabled = false
    private(set) var errorMessage: String?
    private(set) var routeSummary = "—"
    private(set) var wakeAvailable = false
    var serverURLString: String {
        didSet { UserDefaults.standard.set(serverURLString, forKey: Self.serverKey) }
    }

    let controller: ConversationController
    /// The glasses camera (Meta toolkit). Observable: the screen shows its state.
    let camera = DATGlassesCamera()
    /// Sidekick mode: always listening, chiming in unprompted.
    let sidekick: SidekickController

    @ObservationIgnored private let auth = AuthStore()
    @ObservationIgnored private let route = AudioRouteManager()
    @ObservationIgnored private let capture = CaptureEngine()
    @ObservationIgnored private let player = SpeechPlayer()
    @ObservationIgnored private let earcons = Earcons()
    @ObservationIgnored private let wake = SpeechWakeDetector()
    @ObservationIgnored private let socket: NovaSocket
    @ObservationIgnored private let vision: VisionClient
    @ObservationIgnored private let sidekickSocket: NovaSocket
    @ObservationIgnored private var token: String?
    @ObservationIgnored private var autoOffTask: Task<Void, Never>?
    @ObservationIgnored private var wasOnGlasses = false
    private static let serverKey = "nova.serverURL"

    init() {
        let storedServer = UserDefaults.standard.string(forKey: Self.serverKey)
        serverURLString = storedServer ?? Self.defaultBaseURL.absoluteString
        token = auth.loadToken()
        isLoggedIn = token != nil

        socket = NovaSocket(baseURL: { AppModel.defaultBaseURL }, token: { nil })
        vision = VisionClient(api: { APIClient(baseURL: AppModel.defaultBaseURL) })
        sidekickSocket = NovaSocket(baseURL: { AppModel.defaultBaseURL }, token: { nil }, path: "/ws/sidekick")
        // One store for both: Sidekick's interjections and the direct
        // conversation need to land in the same thread.
        let conversationIds = ConversationIdStore()
        controller = ConversationController(
            socket: socket,
            player: player,
            earcons: earcons,
            wake: wake,
            scheduler: MainScheduler(),
            conversationIds: conversationIds,
            camera: camera,
            vision: vision
        )
        let controller = self.controller
        sidekick = SidekickController(
            socket: sidekickSocket,
            player: player,
            earcons: earcons,
            camera: camera,
            vision: vision,
            scheduler: MainScheduler(),
            conversationIds: conversationIds,
            mainIsIdle: { controller.phase == .idle },
            expectFollowUp: { controller.expectSidekickFollowUp() }
        )
        // Late-bound so a server or token change applies on the next connect
        // without rebuilding the socket.
        socket.baseURL = { [weak self] in self?.baseURL ?? AppModel.defaultBaseURL }
        socket.token = { [weak self] in self?.token }
        sidekickSocket.baseURL = { [weak self] in self?.baseURL ?? AppModel.defaultBaseURL }
        sidekickSocket.token = { [weak self] in self?.token }
        sidekick.onEnded = { [weak self] reason in
            guard let self else { return }
            self.controller.onAmbientUtterance = nil
            self.controller.onWakeHeard = nil
            switch reason {
            case "timeout": self.postLocalNotification("Sidekick turned off after an hour.")
            case "error": self.errorMessage = "Sidekick stopped: the server refused it."
            default: break
            }
        }
        vision.api = { [weak self] in self?.api ?? APIClient(baseURL: AppModel.defaultBaseURL) }
        // Meta: the glasses mic (HFP) must be up before the camera stream starts.
        camera.audioReady = { [weak self] in
            guard let self else { return false }
            return self.listeningEnabled && self.route.route.isBluetooth
        }

        capture.attach(player.node)
        capture.attach(earcons.node)
        capture.onRestart = { [weak self] in
            self?.player.engineRestarted()
            self?.earcons.engineRestarted()
        }
        capture.onFrame = { [weak self] frame, now in
            self?.controller.ingest(frame: frame, at: now)
        }
        controller.onUnauthorized = { [weak self] in
            self?.signedOut(message: "Your session expired. Log in again.")
        }
        wireRouteEvents()
    }

    var baseURL: URL {
        URL(string: serverURLString.trimmingCharacters(in: .whitespaces)) ?? Self.defaultBaseURL
    }

    var api: APIClient { APIClient(baseURL: baseURL, token: token) }

    /// Sidekick needs Listening on: it rides on the same microphone.
    func setSidekick(_ on: Bool) {
        guard on else {
            sidekick.stop()
            return
        }
        guard listeningEnabled else { return }
        controller.onAmbientUtterance = { [weak self] pcm in self?.sidekick.ambient(pcm) }
        controller.onWakeHeard = { [weak self] in self?.sidekick.userWoke() }
        sidekick.start()
    }

    /// `novaglasses://` — the Meta AI app returning after registration.
    func handleOpenURL(_ url: URL) {
        camera.handleUrl(url)
    }

    // MARK: - Session

    func bootstrap() async {
        guard isLoggedIn else { return }
        do {
            let enabled = try await api.power()
            if enabled {
                await startListening()
            }
        } catch APIClient.APIError.unauthorized {
            signedOut(message: "Your session expired. Log in again.")
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func login(username: String, password: String) async {
        errorMessage = nil
        do {
            let token = try await api.login(username: username, password: password)
            auth.saveToken(token)
            self.token = token
            isLoggedIn = true
            await bootstrap()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func logout() async {
        await stopListening(mirrorToServer: false)
        try? await api.logout()
        signedOut(message: nil)
    }

    private func signedOut(message: String?) {
        stopAudio()
        controller.setEnabled(false)
        listeningEnabled = false
        auth.clear()
        token = nil
        isLoggedIn = false
        errorMessage = message
    }

    // MARK: - Listening

    func setListening(_ on: Bool) async {
        if on {
            await startListening()
            if listeningEnabled {
                _ = try? await api.setPower(true)
            }
        } else {
            await stopListening(mirrorToServer: true)
        }
    }

    private func startListening() async {
        errorMessage = nil
        guard await AVAudioApplication.requestRecordPermission() else {
            errorMessage = "Microphone access is off. Allow it in Settings → Nova."
            return
        }
        if !(await SpeechWakeDetector.requestAuthorization()) {
            errorMessage = "Speech recognition is off, so \"Hey Nova\" can't be heard. Allow it in Settings → Nova."
        }
        wakeAvailable = wake.isAvailable
        if !wakeAvailable && errorMessage == nil {
            errorMessage = "On-device speech recognition isn't available, so \"Hey Nova\" can't be heard."
        }
        _ = try? await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound])
        do {
            try startAudio()
        } catch {
            errorMessage = "Couldn't start audio: \(error.localizedDescription)"
            return
        }
        controller.setEnabled(true)
        listeningEnabled = true
    }

    private func stopListening(mirrorToServer: Bool) async {
        sidekick.stop()
        controller.setEnabled(false)
        stopAudio()
        listeningEnabled = false
        autoOffTask?.cancel()
        if mirrorToServer {
            _ = try? await api.setPower(false)
        }
    }

    private func startAudio() throws {
        try route.activate()
        routeSummary = route.route.summary
        wasOnGlasses = route.route.isBluetooth
        capture.voiceProcessing = route.policy.voiceProcessing
        try capture.start()
        // Anything Nova was saying when the engine went down plays on; the
        // earcons node needs the same nudge or it can be left in a stale
        // playing state that never renders scheduled buffers.
        player.engineRestarted()
        earcons.engineRestarted()
    }

    private func stopAudio() {
        capture.stop()
        route.deactivate()
        routeSummary = route.route.summary
    }

    // MARK: - Route, interruptions

    private func wireRouteEvents() {
        route.onRouteChange = { [weak self] route in
            guard let self else { return }
            self.routeSummary = route.summary
            self.glassesRouteChanged(onGlasses: route.isBluetooth)
        }
        route.onInterruptionBegan = { [weak self] in
            // iOS has already stopped the engine; mark it so a resume rebuilds.
            self?.capture.stop()
        }
        route.onInterruptionEnded = { [weak self] _ in
            // Resume regardless of `shouldResume`: an always-listening app is
            // the whole point, and a refused resume is reported below.
            self?.resumeAfterInterruption()
        }
        route.onMediaServicesReset = { [weak self] in
            self?.resumeAfterInterruption()
        }
        NotificationCenter.default.addObserver(
            forName: UIApplication.didBecomeActiveNotification, object: nil, queue: .main
        ) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let self, self.listeningEnabled else { return }
                if !self.capture.isRunning {
                    self.resumeAfterInterruption()
                }
                self.socket.reconnectIfDown()
            }
        }
    }

    private func resumeAfterInterruption() {
        guard listeningEnabled else { return }
        do {
            try startAudio()
        } catch {
            errorMessage = "Nova stopped listening: \(error.localizedDescription)"
            postLocalNotification("Nova stopped listening — tap to resume.")
        }
    }

    private func glassesRouteChanged(onGlasses: Bool) {
        if onGlasses {
            wasOnGlasses = true
            autoOffTask?.cancel()
            autoOffTask = nil
            return
        }
        guard listeningEnabled, wasOnGlasses, autoOffTask == nil else { return }
        autoOffTask = Task { @MainActor [weak self] in
            try? await Task.sleep(nanoseconds: UInt64(Self.glassesGoneAutoOffSeconds * 1_000_000_000))
            guard let self, !Task.isCancelled, self.listeningEnabled else { return }
            self.autoOffTask = nil
            await self.stopListening(mirrorToServer: false)
            self.postLocalNotification("Glasses disconnected — Nova stopped listening.")
        }
    }

    private func postLocalNotification(_ body: String) {
        let content = UNMutableNotificationContent()
        content.title = "Nova"
        content.body = body
        let request = UNNotificationRequest(identifier: "nova.listening", content: content, trigger: nil)
        UNUserNotificationCenter.current().add(request)
    }
}
