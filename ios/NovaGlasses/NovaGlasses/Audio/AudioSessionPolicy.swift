@preconcurrency import AVFoundation

/// How the audio session should be set up for the microphone in use.
///
/// `.voiceChat` plus voice processing is iOS's VoIP-call configuration: it
/// plays at the separate call volume, applies automatic gain, ducks other apps
/// hard, and makes Nova feel like a phone call. The glasses already beamform
/// and handle echo themselves, so on them the session runs in `.default` mode
/// with voice processing off. Only the phone's own mic and speaker, which sit
/// next to each other, still need echo cancellation.
struct AudioSessionPolicy: Equatable {
    var mode: AVAudioSession.Mode
    var voiceProcessing: Bool

    static func forInput(onGlasses: Bool) -> AudioSessionPolicy {
        onGlasses
            ? AudioSessionPolicy(mode: .default, voiceProcessing: false)
            : AudioSessionPolicy(mode: .voiceChat, voiceProcessing: true)
    }

    /// Mixable, so other apps neither interrupt Nova nor get stopped by it.
    /// Other audio is ducked only while Nova is actually speaking.
    static func options(ducking: Bool) -> AVAudioSession.CategoryOptions {
        // `.allowBluetooth` is the HFP option (renamed `.allowBluetoothHFP`
        // in the iOS 26 SDK).
        var options: AVAudioSession.CategoryOptions = [.allowBluetooth, .defaultToSpeaker, .mixWithOthers]
        if ducking {
            options.insert(.duckOthers)
        }
        return options
    }
}
