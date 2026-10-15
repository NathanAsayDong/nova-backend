# NovaGlasses

Talk to Nova hands-free through Ray-Ban Meta glasses. This is a native iOS client (Swift 6, SwiftUI, iOS 17.2+, no third-party dependencies).

The glasses act as a plain Bluetooth headset (HFP). There is no Meta toolkit and no Meta approval in v1. You say "Hey Nova …" and the phone recognizes the wake phrase on-device. It then streams the utterance as 16 kHz PCM to `wss://api.nova-api.us/ws/transcribe` with `client: "glasses"`, and plays Nova's spoken reply back through the glasses.

## Build and test (CLI)

```bash
brew install xcodegen          # once; only needed after editing project.yml
cd ios/NovaGlasses
xcodegen generate              # regenerates NovaGlasses.xcodeproj from project.yml
xcodebuild build -project NovaGlasses.xcodeproj -scheme NovaGlasses \
  -destination 'platform=iOS Simulator,name=iPhone 17,OS=27.0'
xcodebuild test  -project NovaGlasses.xcodeproj -scheme NovaGlasses \
  -destination 'platform=iOS Simulator,name=iPhone 17,OS=27.0'
```

Run the tests on an iOS 26+ simulator. On the iOS 18.5 simulator, Meta's
`MWDATCore` aborts with a Swift metadata error as soon as XCTest enumerates
classes.

Edit `project.yml`, not the generated project. The generated `NovaGlasses.xcodeproj` is checked in so Xcode can open it directly.

The tests (63 of them) cover:
- the `TurnDetector` port, case by case against `turnDetector.ts`
- wake-phrase matching
- `Codable` round-trips for every client and server event
- PCM/WAV framing, the pre-roll ring, 48k→16k conversion and incremental MP3 decoding (fixture: `NovaGlassesTests/Fixtures/tone_1s_22050.mp3`)
- the `ConversationController` state machine, driven through fake socket, player, earcons, wake detector and clock

## Install on your iPhone

1. Use Xcode 16.4+ and a paid Apple Developer account. A free account works, but the app must be re-signed every 7 days.
2. Turn on Developer Mode on the iPhone (Settings → Privacy & Security → Developer Mode) and connect it by USB once.
3. Open `NovaGlasses.xcodeproj`, select the **NovaGlasses** target, then **Signing & Capabilities**. Pick your Team. If `us.nova-api.NovaGlasses` is taken, change the bundle id.
   - To keep the team across regenerations, set `DEVELOPMENT_TEAM` in `project.yml`.
4. Choose your iPhone as the run destination and press ⌘R.
   - On first launch, trust the developer certificate in Settings → General → VPN & Device Management.
5. Pair the glasses with the phone in the Meta AI app as usual. In iOS Settings → Bluetooth they should show as connected.
6. Log in with your Nova username and password. The token is stored in the Keychain and slides for 30 days. Turn on **Listening**.
   - Allow Microphone, Speech Recognition and Notifications when asked.

For TestFlight: Product → Archive → Distribute App → TestFlight (Internal). Personal use needs no review.

**Test against a local backend first.** On the login screen, set the Server field to `http://<your-mac-ip>:8000` (phone and Mac on the same Wi-Fi). Local-network http is allowed by `NSAllowsLocalNetworking`. Switch the field back to `https://api.nova-api.us` afterwards. The backend must include the Phase 1 changes: raw PCM `mimeType` and `client: "glasses"` → `GLASSES_PROMPT`.

## Vision: "Hey Nova, what do you see?"

The glasses camera comes through Meta's Wearables Device Access Toolkit
(`MWDATCore` + `MWDATCamera` 1.0.1, Swift Package). Audio does not use it.

**One-time setup:**
1. In the Meta AI app, open **App Info** and tap the version number 5 times. Then turn on **Developer Mode** for the glasses.
2. In Nova, turn Listening on with the glasses connected, then tap **Connect glasses camera in Meta AI**.
3. Approve Nova in Meta AI, then allow the camera. Meta AI returns to Nova through `novaglasses://`.

**How a photo is taken:**
- **Phrase trigger.** When a live caption asks to look ("what do you see", "who's this", "read this", …; see `Voice/VisionIntent.swift`), the phone starts the camera stream and takes a JPEG. It plays the shutter tick, scales the image to a 1280 px long edge, and uploads it to `POST /vision/images`. All of this happens while you are still talking. `stop` waits up to 3 s for the upload and then carries `imageIds`.
- **Nova's `look` tool.** The server sends `capture_request`. The phone uploads with that `requestId`, or calls `POST /vision/capture-failed`.
- **Stream lifetime.** The stream needs the glasses to be the HFP microphone (Meta's ordering rule). It stops after 20 s idle, so the capture LED is only on around a photo.

**People Nova knows** (home screen):
- Enroll only people who agreed. Adding someone requires their name and a confirmation that they consented.
- Add 3+ face photos, taken with the glasses or picked from Photos.
- The server matches faces and stores only embeddings. Swipe to delete a person and everything stored for them.

## How it behaves

| State | What you hear | Leaves when |
|---|---|---|
| idle | nothing | an utterance opens with "Hey Nova" (on-device recognizer), which plays the **wake** chime |
| listening | — | your utterance ends. Silence length is set by the server's `endpointMs`. Plays a **thinking** tick |
| thinking | — | Nova's audio starts |
| speaking | Nova's voice | the reply finishes, then it listens for a follow-up |
| listening (follow-up) | — | you speak, or 8 s pass with nothing (**done**), or you say "thanks Nova" (`follow_up_stopped`, **done**) |

- **Nothing leaves the phone while idle.** Each utterance is held locally until the recognizer hears "Hey Nova" at its start. Then the whole utterance is sent as `purpose: "sentry"` (with 500 ms of pre-roll), so "Hey Nova, what's the weather" works in one breath.
- **Barge-in.** Say "Hey Nova …" while Nova is talking. Playback stops, the rest of that reply is dropped, and your new utterance is sent.
  - This is client-side only. The server still finishes the old turn; its late events are ignored until the server acknowledges the new `start`. A server-side `cancel` is Phase 3.
- The conversation id persists in UserDefaults and is cleared when the server says `conversation_closed`.
- The **Listening** toggle mirrors `POST /nova/power`, which is the same switch the web UI uses. Turning it off here also turns Nova off for the web.
- Earcons: **wake** (rising), **thinking** (tick), **done** (falling), **cancel** (low), **error** (two low notes).
- If the glasses disconnect for 10 minutes while listening, listening switches off and a notification is posted. If iOS refuses to restart audio after an interruption, you get a "Nova stopped listening — tap to resume" notification.

## Code map

| File | Role |
|---|---|
| `Auth/AuthStore.swift`, `Auth/APIClient.swift` | Keychain token; `/auth/login`, `/auth/logout`, `/nova/power` |
| `Audio/AudioRouteManager.swift` | `.playAndRecord` + `.allowBluetooth` (HFP) + `.voiceChat`; prefers the HFP mic; route, interruption and media-reset events |
| `Audio/CaptureEngine.swift` | One `AVAudioEngine`: mic tap → 16 kHz mono Int16 frames; player nodes for voice and earcons (same engine, so the route stays HFP) |
| `Audio/PCM.swift` | Wire format, RMS, WAV header, 500 ms pre-roll ring |
| `Audio/MP3StreamDecoder.swift`, `Audio/SpeechPlayer.swift` | Incremental MP3 decode (AudioFileStream + AVAudioConverter); ordered stream queue |
| `Audio/Earcons.swift` | Synthesized chimes, matching the web's `earcons.ts` |
| `Voice/TurnDetector.swift` | Port of `turnDetector.ts` (+ the web's level smoothing) |
| `Voice/WakePhrase.swift`, `Voice/SpeechWakeDetector.swift` | Port of `wakePhrase.ts`; on-device `SFSpeechRecognizer`, one task per utterance, behind `WakeDetecting` |
| `Net/NovaEvents.swift`, `Net/NovaSocket.swift` | Typed events; bearer on the upgrade, 4401 → logout, 20 s ping, 1/2/5/10/30 s backoff |
| `Conversation/ConversationController.swift` | The state machine (ports in `Conversation/Ports.swift`) |
| `UI/` | Login screen and a minimal home screen |

## What is verified and what is not

**Verified (simulator):**
- `xcodebuild build` and `xcodebuild test` pass on the iPhone 16 / iOS 18.5 simulator (63 tests).
- The app launches to the login screen.

**Not verified.** None of this can be checked in the simulator, and it has not been run on a device yet:
- **Any Bluetooth behaviour.** HFP routing to the glasses, the 8 kHz vs 16 kHz input rate, whether `setPreferredInput` reliably picks the glasses' mic, and playback quality over HFP.
- **The live audio path end to end.** This covers the real mic tap and converter on a device route, voice processing with HFP, and the engine restarting on route or configuration changes.
- **On-device speech recognition for "Hey Nova"** (`supportsOnDeviceRecognition` is false in the simulator): its latency, accuracy, and echo from Nova's own voice re-triggering it.
- **MP3 playback through the player node.** Decoding is unit-tested; scheduled playback and the drain → follow-up timing are not.
- **Against the real server:** login, the WebSocket handshake with the bearer header, 4401 handling, ping/reconnect, and the Phase 1 PCM + `GLASSES_PROMPT` path.
- **Background:** staying alive while locked, recovery after a phone call or "Hey Meta", and battery.

## On-device field checklist

Run this against the local backend first, then `api.nova-api.us`. Note where it fails.

- [ ] **Route:** with the glasses connected and Listening on, the home screen's Audio row shows the glasses as both input and output, and the sample rate (8000 or 16000).
- [ ] **Wake → ask → answer:** "Hey Nova, what time is it?" in one breath. You hear the wake chime and the thinking tick, then the answer in the glasses.
- [ ] **Bare wake:** "Hey Nova." (pause) "What's on my calendar?" The second sentence is answered.
- [ ] **Follow-up:** after an answer, ask something else without "Hey Nova". It is answered in the same conversation.
- [ ] **Stop phrase:** "Thanks Nova" ends the conversation (falling chime).
- [ ] **Timeout:** after an answer, stay silent for 8 s. You hear the falling chime and it goes back to idle.
- [ ] **Not addressed:** talk normally near the glasses without "Hey Nova". Nothing is sent, and the server logs show no `[sentry]` lines.
- [ ] **Barge-in:** while Nova is talking, say "Hey Nova, stop. What's the weather instead?" Nova stops at once and the new question is answered. The old reply does not resume.
- [ ] **Echo:** Nova saying something with "Nova" in it does not trigger a barge-in.
- [ ] **Locked phone:** lock the phone for 30 minutes, then "Hey Nova …". It still answers.
- [ ] **Phone call:** take a call, hang up, then "Hey Nova …". It still answers. If not, the "tap to resume" notification should appear.
- [ ] **"Hey Meta":** use Meta's assistant, then "Hey Nova …". It still answers.
- [ ] **Wi-Fi → cellular:** walk out of Wi-Fi range mid-idle. It reconnects (Server row) and still answers.
- [ ] **Glasses removed or disconnected:** audio falls back to the phone. After 10 minutes listening switches off with a notification.
- [ ] **Token expiry → login:** log out on the web with "log out everywhere". The app returns to the login screen when it next connects.
- [ ] **Battery:** note glasses and phone battery drain per hour with Listening on.
- [ ] **Accuracy:** check whether Whisper copes with 8 kHz beamformed audio (`user_transcript` in the home screen's "You said").
