@preconcurrency import AVFoundation

/// How the audio session is set up for two-way voice.
///
/// Always `.voiceChat` with voice processing. The glasses' microphone is
/// Bluetooth HFP, which is a phone-call link whatever the app's mode, and
/// `.default` mode made iOS move the microphone back to the phone and the
/// output to the earpiece (seen on device as a route that flapped several
/// times a second). What can be fixed is how Nova sits with other audio.
struct AudioSessionPolicy: Equatable {
    var mode: AVAudioSession.Mode
    var voiceProcessing: Bool

    static let voice = AudioSessionPolicy(mode: .voiceChat, voiceProcessing: true)

    /// Mixable, so other apps neither interrupt Nova nor get stopped by it.
    /// Not ducked: changing the category options mid-session re-routes the
    /// audio, which is what made the glasses route flap.
    // `.allowBluetooth` is the HFP option (renamed `.allowBluetoothHFP` in
    // the iOS 26 SDK).
    static let options: AVAudioSession.CategoryOptions = [.allowBluetooth, .defaultToSpeaker, .mixWithOthers]
}
