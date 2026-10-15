@preconcurrency import AVFoundation
import Foundation

/// Owns the AVAudioSession: Bluetooth HFP to the glasses, the mode for the
/// microphone in use (see `AudioSessionPolicy`), and the notifications that
/// tell the engine to stop or restart.
///
/// The glasses are a plain Bluetooth headset. Opening their microphone forces
/// HFP (8 kHz mono, beamformed to the wearer), and while HFP is up their
/// speakers play at that rate too — so Nova's voice is phone-call quality
/// while listening is on. That is the accepted cost of hands-free.
@MainActor
final class AudioRouteManager {
    struct Route: Equatable {
        var inputName: String
        var outputName: String
        var isBluetooth: Bool
        var sampleRate: Double

        var summary: String {
            let rate = sampleRate > 0 ? " · \(Int(sampleRate)) Hz" : ""
            return inputName == outputName ? "\(inputName)\(rate)" : "\(inputName) → \(outputName)\(rate)"
        }
    }

    /// The route changed; the engine has to be rebuilt for the new input format.
    var onRouteChange: ((Route) -> Void)?
    /// Something (a phone call, Siri, "Hey Meta") took the audio session.
    var onInterruptionBegan: (() -> Void)?
    /// The interruption ended; `shouldResume` is iOS's hint.
    var onInterruptionEnded: ((_ shouldResume: Bool) -> Void)?
    /// The media server restarted; everything audio must be rebuilt.
    var onMediaServicesReset: (() -> Void)?

    private(set) var route = Route(inputName: "—", outputName: "—", isBluetooth: false, sampleRate: 0)
    /// What the session is set up for right now. The engine reads
    /// `voiceProcessing` from it when it (re)starts.
    private(set) var policy = AudioSessionPolicy.voice
    private var isActive = false
    private let session = AVAudioSession.sharedInstance()
    private let log = AudioLog.shared
    private var observers: [NSObjectProtocol] = []

    init() {
        let center = NotificationCenter.default
        observers.append(center.addObserver(
            forName: AVAudioSession.routeChangeNotification, object: nil, queue: .main
        ) { [weak self] note in
            let reason = (note.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt)
                .flatMap(AVAudioSession.RouteChangeReason.init(rawValue:))
            MainActor.assumeIsolated { self?.routeChanged(reason: reason) }
        })
        observers.append(center.addObserver(
            forName: AVAudioSession.interruptionNotification, object: nil, queue: .main
        ) { [weak self] note in
            let type = (note.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt)
                .flatMap(AVAudioSession.InterruptionType.init(rawValue:))
            let options = (note.userInfo?[AVAudioSessionInterruptionOptionKey] as? UInt)
                .map(AVAudioSession.InterruptionOptions.init(rawValue:)) ?? []
            let reason = note.userInfo?[AVAudioSessionInterruptionReasonKey] as? UInt
            MainActor.assumeIsolated {
                switch type {
                case .began:
                    self?.log.add("Interrupted (reason \(reason.map(String.init) ?? "none"))")
                    self?.onInterruptionBegan?()
                case .ended:
                    let resume = options.contains(.shouldResume)
                    self?.log.add("Interruption ended (shouldResume: \(resume))")
                    self?.onInterruptionEnded?(resume)
                default: break
                }
            }
        })
        observers.append(center.addObserver(
            forName: AVAudioSession.mediaServicesWereResetNotification, object: nil, queue: .main
        ) { [weak self] _ in
            MainActor.assumeIsolated {
                self?.log.add("Media services were reset")
                self?.onMediaServicesReset?()
            }
        })
    }

    /// Configure and activate the session for two-way voice over the glasses.
    func activate() throws {
        try session.setCategory(.playAndRecord, mode: policy.mode, options: AudioSessionPolicy.options)
        // HFP wideband is 16 kHz; ask for it and take what the headset gives.
        try? session.setPreferredSampleRate(PCMFormat.sampleRate)
        try? session.setPreferredIOBufferDuration(0.02)
        try session.setActive(true)
        isActive = true
        preferBluetoothInput()
        refreshRoute()
        log.add("Session active: \(policy.mode.rawValue), voice processing \(policy.voiceProcessing ? "on" : "off") · \(route.summary)")
    }

    func deactivate() {
        isActive = false
        try? session.setActive(false, options: .notifyOthersOnDeactivation)
        refreshRoute()
        log.add("Session inactive")
    }

    /// Pick the glasses' microphone over the phone's when both are present.
    private func preferBluetoothInput() {
        guard let bluetooth = session.availableInputs?.first(where: { $0.portType == .bluetoothHFP }) else {
            return
        }
        if session.preferredInput?.uid != bluetooth.uid {
            try? session.setPreferredInput(bluetooth)
        }
    }

    private func routeChanged(reason: AVAudioSession.RouteChangeReason?) {
        preferBluetoothInput()
        let previous = route
        refreshRoute()
        if route != previous {
            log.add("Route \(reasonName(reason)): \(route.summary)")
            onRouteChange?(route)
        }
    }

    private func reasonName(_ reason: AVAudioSession.RouteChangeReason?) -> String {
        switch reason {
        case .newDeviceAvailable: "new device"
        case .oldDeviceUnavailable: "device gone"
        case .categoryChange: "category change"
        case .override: "override"
        case .wakeFromSleep: "wake from sleep"
        case .noSuitableRouteForCategory: "no suitable route"
        case .routeConfigurationChange: "configuration change"
        default: "changed"
        }
    }

    private func refreshRoute() {
        let current = session.currentRoute
        let input = current.inputs.first
        let output = current.outputs.first
        route = Route(
            inputName: input?.portName ?? "No microphone",
            outputName: output?.portName ?? "No speaker",
            isBluetooth: input?.portType == .bluetoothHFP,
            sampleRate: session.sampleRate
        )
    }
}

