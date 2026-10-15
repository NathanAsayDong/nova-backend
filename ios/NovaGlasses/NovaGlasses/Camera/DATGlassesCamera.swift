import Foundation
import MWDATCamera
import MWDATCore
import Observation
import UIKit

/// The glasses camera through Meta's Wearables Device Access Toolkit.
///
/// Registration happens once, in the Meta AI app (Developer Mode on the
/// glasses), which then hands control back through `novaglasses://`. After
/// that a photo is: open a device session, add a camera stream, wait for it
/// to run, `capturePhoto(.jpeg)`. The stream is started only when a photo is
/// wanted and stopped after `idleSeconds`, so the capture LED is on only
/// around a photo and the glasses' battery is spared.
///
/// Meta's docs: the HFP microphone must be up before the stream starts, or
/// the audio route can fail silently — so `audioReady` gates the start.
@MainActor
@Observable
final class DATGlassesCamera: GlassesCamera {
    enum CameraError: LocalizedError {
        case notReady(GlassesCameraState)
        case glassesAudioNotUp
        case timeout(String)
        case noCamera
        case failed(String)

        var errorDescription: String? {
            switch self {
            case .notReady(let state): "The glasses camera isn't ready (\(state))."
            case .glassesAudioNotUp: "The glasses aren't connected as the microphone."
            case .timeout(let what): "Timed out waiting for \(what)."
            case .noCamera: "The glasses didn't offer a camera."
            case .failed(let reason): reason
            }
        }
    }

    static let idleSeconds: Double = 20
    /// The stream negotiates a Wi‑Fi link to the glasses on first use, which
    /// can take a while.
    static let startTimeout: Double = 15
    static let photoTimeout: Double = 4

    private(set) var state: GlassesCameraState = .unregistered
    /// True when the glasses are the active HFP microphone.
    @ObservationIgnored var audioReady: () -> Bool = { true }

    @ObservationIgnored private var wearables: (any WearablesInterface)?
    @ObservationIgnored private var session: DeviceSession?
    @ObservationIgnored private var camera: Camera?
    @ObservationIgnored private var tokens: [any AnyListenerToken] = []
    @ObservationIgnored private var latestFrame: VideoFrame?
    @ObservationIgnored private var photoWaiter: CheckedContinuation<Data, Error>?
    @ObservationIgnored private var startTask: Task<Void, Error>?
    @ObservationIgnored private var coolTask: Task<Void, Never>?
    /// nil: not known yet, because the glasses were not connected when we
    /// asked. Checked again when they connect, and before a photo.
    @ObservationIgnored private var cameraPermitted: Bool?
    @ObservationIgnored private var registered = false
    /// Link-state listeners, one per glasses the toolkit knows about.
    @ObservationIgnored private var linkWatches: [DeviceIdentifier: any AnyListenerToken] = [:]
    /// The glasses whose toolkit link is up: the session is opened on them
    /// directly. A fresh AutoDeviceSelector has not picked a device yet and
    /// fails with "No eligible device available".
    @ObservationIgnored private var connectedDevice: DeviceIdentifier?

    init() {
        do {
            try Wearables.configure()
            let wearables = Wearables.shared
            self.wearables = wearables
            Task { @MainActor [weak self] in
                for await registration in wearables.registrationStateStream() {
                    await self?.registrationChanged(registration)
                }
            }
            Task { @MainActor [weak self] in
                for await devices in wearables.devicesStream() {
                    await self?.devicesChanged(devices)
                }
            }
        } catch {
            state = .unavailable(error.localizedDescription)
            AudioLog.shared.add("Glasses camera unavailable: \(error.localizedDescription)")
        }
    }

    // MARK: - Registration

    /// Send the user to the Meta AI app to register Nova (or, once
    /// registered, to grant the camera permission).
    func register() {
        guard let wearables else { return }
        Task { @MainActor in
            do {
                if wearables.registrationState == .registered {
                    try await requestCameraPermission()
                } else {
                    state = .registering
                    try await wearables.startRegistration()
                }
            } catch {
                AudioLog.shared.add("Glasses registration failed: \(error.localizedDescription)")
                state = .unregistered
            }
        }
    }

    /// The Meta AI app returned to us through `novaglasses://`.
    func handleUrl(_ url: URL) {
        guard let wearables else { return }
        Task { @MainActor in
            do {
                _ = try await wearables.handleUrl(url)
            } catch {
                AudioLog.shared.add("Meta AI callback failed: \(error.localizedDescription)")
            }
        }
    }

    private func registrationChanged(_ registration: RegistrationState) async {
        AudioLog.shared.add("Glasses registration: \(registration == .registered ? "registered" : "\(registration)")")
        switch registration {
        case .registered:
            registered = true
            await refreshPermission()
        case .registering:
            state = .registering
        default:
            registered = false
            cameraPermitted = nil
            tearDown()
            state = .unregistered
        }
    }

    /// The toolkit lists the glasses before its link to them is up, and a
    /// permission check before then fails. Watch each one's link and check
    /// once it connects.
    private func devicesChanged(_ devices: [DeviceIdentifier]) async {
        guard let wearables else { return }
        for id in devices where linkWatches[id] == nil {
            guard let device = wearables.deviceForIdentifier(id) else { continue }
            AudioLog.shared.add("Glasses \(device.nameOrId()): link \(device.linkState)")
            linkWatches[id] = device.addLinkStateListener { [weak self] link in
                Task { @MainActor in await self?.linkChanged(link, device: id) }
            }
            if device.linkState == .connected {
                await linkChanged(.connected, device: id)
            }
        }
    }

    private func linkChanged(_ link: LinkState, device id: DeviceIdentifier) async {
        let compatibility = wearables?.deviceForIdentifier(id)?.compatibility()
        AudioLog.shared.add("Glasses link: \(link) (\(compatibility?.displayString ?? "unknown compatibility"))")
        if link == .connected {
            connectedDevice = id
            if registered, cameraPermitted != true {
                await refreshPermission()
            }
        } else if connectedDevice == id {
            connectedDevice = nil
        }
    }

    /// Ask the toolkit whether the camera is allowed. Only a definite answer
    /// changes anything: a check that fails because the glasses are not
    /// connected yet leaves the camera usable, to be checked again later.
    private func refreshPermission() async {
        guard let wearables else { return }
        do {
            let status = try await wearables.checkPermissionStatus(.camera)
            AudioLog.shared.add("Glasses camera permission: \(status)")
            switch status {
            case .granted: cameraPermitted = true
            case .denied: cameraPermitted = false
            default: break
            }
        } catch {
            AudioLog.shared.add("Camera permission check deferred: \(error.localizedDescription)")
        }
        if session == nil {
            state = registered && cameraPermitted != false ? .ready : .unregistered
        }
    }

    private func requestCameraPermission() async throws {
        guard let wearables else { return }
        state = .registering
        let status = try await wearables.requestPermission(.camera)
        cameraPermitted = status == .granted
        state = status == .granted ? .ready : .unregistered
        AudioLog.shared.add("Glasses camera permission: \(status)")
    }

    // MARK: - Photo

    func capturePhoto() async throws -> Data {
        let started = ProcessInfo.processInfo.systemUptime
        try await warm()
        let warmed = ProcessInfo.processInfo.systemUptime
        var jpeg: Data
        do {
            jpeg = try await takePhoto()
        } catch {
            // A frame off the running stream beats no photo at all.
            guard let image = latestFrame?.makeUIImage(),
                  let frameJpeg = image.jpegData(compressionQuality: ImagePrep.quality) else { throw error }
            AudioLog.shared.add("Photo capture failed (\(error.localizedDescription)); using a stream frame")
            jpeg = frameJpeg
        }
        scheduleCool()
        let done = ProcessInfo.processInfo.systemUptime
        AudioLog.shared.add("Photo: stream ready in \(Int((warmed - started) * 1000)) ms, photo in \(Int((done - warmed) * 1000)) ms")
        return ImagePrep.scaled(jpeg) ?? jpeg
    }

    /// Start the session and stream if they are not running yet.
    private func warm() async throws {
        coolTask?.cancel()
        if state == .streaming, camera != nil { return }
        guard state.canCapture else { throw CameraError.notReady(state) }
        guard audioReady() else { throw CameraError.glassesAudioNotUp }
        if cameraPermitted != true {
            await refreshPermission()
            guard cameraPermitted != false else { throw CameraError.notReady(state) }
        }
        if let startTask {
            return try await startTask.value
        }
        let task = Task { @MainActor in try await self.startStream() }
        startTask = task
        defer { startTask = nil }
        do {
            try await task.value
        } catch {
            tearDown()
            throw error
        }
    }

    private func startStream() async throws {
        guard let wearables else { throw CameraError.notReady(state) }
        let selector: any DeviceSelector = connectedDevice.map { SpecificDeviceSelector(device: $0) }
            ?? AutoDeviceSelector(wearables: wearables)
        let session = try wearables.createSession(deviceSelector: selector)
        self.session = session
        tokens.append(session.statePublisher.listen { [weak self] sessionState in
            Task { @MainActor in self?.sessionChanged(sessionState) }
        })
        try session.start()
        try await waitUntil("the glasses session") { session.state == .started }
        AudioLog.shared.add("Glasses session started")

        // Meta's own sample configuration. (hvc1 would keep streaming while
        // the phone is locked, where raw pauses; revisit once this works.)
        let config = StreamConfiguration(videoCodec: .raw, resolution: .low, frameRate: 24)
        guard let camera = try session.addCamera(config: config) else { throw CameraError.noCamera }
        self.camera = camera
        let stream = camera.stream
        if let device = session.device {
            AudioLog.shared.add("Glasses: worn \(device.donState), hinges \(device.hingeState), battery \(device.batteryLevel.map(String.init) ?? "?")%, thermal \(device.thermalLevel)")
        }
        let startedAt = ProcessInfo.processInfo.systemUptime
        tokens.append(stream.statePublisher.listen { streamState in
            let ms = Int((ProcessInfo.processInfo.systemUptime - startedAt) * 1000)
            Task { @MainActor in AudioLog.shared.add("Camera stream: \(streamState) at \(ms) ms") }
        })
        tokens.append(stream.photoDataPublisher.listen { [weak self] photo in
            let data = photo.data
            Task { @MainActor in self?.photoArrived(.success(data)) }
        })
        tokens.append(stream.videoFramePublisher.listen { [weak self] frame in
            Task { @MainActor in self?.latestFrame = frame }
        })
        tokens.append(stream.errorPublisher.listen { [weak self] error in
            let reason = error.description
            Task { @MainActor in
                AudioLog.shared.add("Glasses camera error: \(reason)")
                self?.photoArrived(.failure(CameraError.failed(reason)))
            }
        })
        stream.start()
        do {
            try await waitUntil("the camera stream") { stream.state == .streaming }
        } catch {
            AudioLog.shared.add("Camera stream stuck in \(stream.state); session \(session.state)")
            throw error
        }
        state = .streaming
    }

    private func takePhoto() async throws -> Data {
        guard let stream = camera?.stream else { throw CameraError.noCamera }
        return try await withCheckedThrowingContinuation { continuation in
            photoWaiter?.resume(throwing: CameraError.failed("Superseded by a newer photo."))
            photoWaiter = continuation
            guard stream.capturePhoto(format: .jpeg) else {
                photoArrived(.failure(CameraError.failed("The glasses refused the photo.")))
                return
            }
            Task { @MainActor [weak self] in
                try? await Task.sleep(nanoseconds: UInt64(Self.photoTimeout * 1_000_000_000))
                self?.photoArrived(.failure(CameraError.timeout("the photo")))
            }
        }
    }

    private func photoArrived(_ result: Result<Data, Error>) {
        guard let waiter = photoWaiter else { return }
        photoWaiter = nil
        waiter.resume(with: result)
    }

    private func waitUntil(_ what: String, _ condition: @MainActor () -> Bool) async throws {
        let deadline = ProcessInfo.processInfo.systemUptime + Self.startTimeout
        while !condition() {
            guard ProcessInfo.processInfo.systemUptime < deadline else { throw CameraError.timeout(what) }
            try await Task.sleep(nanoseconds: 100_000_000)
        }
    }

    // MARK: - Lifecycle

    private func sessionChanged(_ sessionState: DeviceSessionState) {
        // Hinges closed, glasses off, or another app took the session.
        if sessionState == .stopped, session != nil, startTask == nil {
            AudioLog.shared.add("Glasses session stopped")
            tearDown()
        }
    }

    private func scheduleCool() {
        coolTask?.cancel()
        coolTask = Task { @MainActor [weak self] in
            try? await Task.sleep(nanoseconds: UInt64(Self.idleSeconds * 1_000_000_000))
            guard let self, !Task.isCancelled else { return }
            self.tearDown()
        }
    }

    private func tearDown() {
        coolTask?.cancel()
        coolTask = nil
        photoArrived(.failure(CameraError.failed("The camera stopped.")))
        let tokens = self.tokens
        self.tokens = []
        Task { for token in tokens { await token.cancel() } }
        camera?.stream.stop()
        camera?.stop()
        session?.stop()
        camera = nil
        session = nil
        latestFrame = nil
        if state == .streaming {
            state = registered && cameraPermitted != false ? .ready : .unregistered
        }
    }
}
