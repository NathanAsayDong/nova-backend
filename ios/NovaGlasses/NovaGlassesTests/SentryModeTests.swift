import XCTest
@testable import NovaGlasses

/// Sentry mode: every turn needs its own "Hey Nova" (no follow-up loop), and
/// it only runs while Nova is on and connected. Reuses the fakes and `Rig`
/// from `ConversationControllerTests`.
@MainActor
final class SentryModeTests: XCTestCase {
    typealias Rig = ConversationControllerTests.Rig

    // MARK: - Persistence

    func testVoiceModeDefaultsToConversationAndPersists() {
        let defaults = UserDefaults(suiteName: "test.\(UUID().uuidString)")!
        let store = VoiceModeStore(defaults: defaults)
        XCTAssertEqual(store.load(), .conversation)
        store.save(.sentry)
        XCTAssertEqual(VoiceModeStore(defaults: defaults).load(), .sentry, "a fresh store reads the same UserDefaults key back")
    }

    func testSetVoiceModePersistsThroughTheStore() {
        let rig = Rig.idle()
        XCTAssertEqual(rig.controller.voiceMode, .conversation)
        rig.controller.setVoiceMode(.sentry)
        XCTAssertEqual(rig.controller.voiceMode, .sentry)
    }

    // MARK: - Held capture, same guarantee as conversation mode

    func testSentryIdleSpeechIsHeldLocallyAndOpensAWakeUtterance() {
        let rig = Rig.sentryIdle()
        rig.speak(500)
        XCTAssertEqual(rig.wake.utterances, 1)
        XCTAssertGreaterThan(rig.wake.fedBytes, 0)
        XCTAssertTrue(rig.socket.log.isEmpty, "nothing leaves the phone before the wake, same as conversation mode")
    }

    // MARK: - Wake detected -> promote / send

    func testWakeMidUtterancePromotesAndSendsInSentryMode() throws {
        let rig = Rig.sentryIdle()
        rig.speak(600)
        rig.wake.hear()
        XCTAssertEqual(rig.controller.phase, .listening)
        let start = try XCTUnwrap(rig.socket.starts.first)
        XCTAssertEqual(start.purpose, .sentry)
        XCTAssertGreaterThan(rig.socket.audio.count, 0, "the held audio is sent once the wake fires")
    }

    // MARK: - Grace period

    func testLateWakeWithinGracePeriodStillPromotesTheCapture() {
        let rig = Rig.sentryIdle()
        rig.speak(600)
        rig.silence(1500) // the turn detector thinks the utterance is over
        rig.wake.hear() // the recognizer only now confirms "Hey Nova", inside the grace window
        XCTAssertEqual(rig.socket.log.filter { $0 != "audio" }, ["start"])
        XCTAssertEqual(rig.controller.phase, .listening)

        // Nothing more said: once the grace/settle window closes, it is
        // treated as request-only and sent off.
        rig.silence(ConversationController.wakeGraceSeconds * 1000 + 100)
        XCTAssertEqual(rig.controller.phase, .thinking)
    }

    func testUtteranceEndingBeforeWakeConfirmsIsDroppedAfterGracePeriod() {
        let rig = Rig.sentryIdle()
        rig.speak(600)
        rig.silence(ConversationController.wakeGraceSeconds * 1000 + 1600) // well past the grace window, no wake
        XCTAssertTrue(rig.socket.log.isEmpty, "never sent: the wake phrase never came")
        XCTAssertEqual(rig.controller.phase, .idle)
        XCTAssertEqual(rig.controller.statusMessage, ConversationController.sentryWaitingMessage)
    }

    // MARK: - Bare-wake listen timeout -> back to waiting

    func testBareWakeTimesOutBackToSentryWaiting() {
        let rig = Rig.sentryIdle()
        rig.wake.hear()
        XCTAssertEqual(rig.controller.phase, .listening)
        rig.silence(ConversationController.listenTimeoutSeconds * 1000 + 100)
        XCTAssertEqual(rig.controller.phase, .idle)
        XCTAssertEqual(rig.controller.statusMessage, ConversationController.sentryWaitingMessage)
        XCTAssertEqual(rig.earcons.played, [.wake, .cancel])
    }

    // MARK: - Return to waiting after a reply (no follow-up loop)

    func testReplyFinishingReturnsStraightToSentryWaitingNoFollowUpLoop() {
        let rig = Rig.sentryIdle()
        rig.speak(600)
        rig.wake.hear()
        rig.speak(400)
        rig.silence(1500)
        XCTAssertEqual(rig.controller.phase, .thinking)

        rig.socket.emit(.userTranscript(text: "what time is it", conversationId: "conv-1"))
        rig.socket.emit(.speechText(text: "It's noon.", role: "final", conversationId: "conv-1"))
        rig.socket.emit(.audioStreamStart(streamId: "s1", mimeType: "audio/mpeg", role: .final))
        rig.socket.emit(.audioStreamChunk(streamId: "s1", chunkBase64: Data([1, 2, 3]).base64EncodedString(), seq: 0))
        XCTAssertEqual(rig.controller.phase, .speaking)

        rig.socket.emit(.audioStreamEnd(streamId: "s1"))
        rig.socket.emit(.done(message: "Done", conversationId: "conv-1", assistantText: "It's noon."))
        XCTAssertEqual(rig.controller.phase, .speaking, "waits for playback to finish")

        rig.player.finishPlaying()
        // Conversation mode would go to `.listening` for a follow-up without
        // requiring the wake phrase again; sentry goes straight back to
        // waiting for "Hey Nova".
        XCTAssertEqual(rig.controller.phase, .idle)
        XCTAssertEqual(rig.controller.statusMessage, ConversationController.sentryWaitingMessage)

        // The next utterance, with no wake phrase, is held and never sent —
        // exactly like the very first one.
        rig.socket.events.removeAll()
        rig.socket.audio = Data()
        rig.socket.log.removeAll()
        rig.speak(500)
        XCTAssertTrue(rig.socket.log.isEmpty, "every turn needs its own wake phrase in sentry mode")
    }

    // MARK: - Nova off / disconnected: no capture, auto-resume

    func testSentryBlockedWhileDisconnectedCapturesNothing() {
        let rig = Rig.idle(voiceMode: .sentry) // never opened: no connection yet
        XCTAssertEqual(rig.controller.phase, .sentryBlocked)
        XCTAssertEqual(rig.controller.statusMessage, ConversationController.sentryBlockedMessage)

        rig.speak(800)
        XCTAssertEqual(rig.wake.utterances, 0, "no wake detection while blocked")
        XCTAssertTrue(rig.socket.log.isEmpty, "no capture, no local buffering while blocked")
    }

    func testSentryResumesAutomaticallyWhenConnectionComesBack() {
        let rig = Rig.idle(voiceMode: .sentry)
        XCTAssertEqual(rig.controller.phase, .sentryBlocked)

        rig.socket.open() // no user action — the connection just comes back
        XCTAssertEqual(rig.controller.phase, .idle, "resumes into the normal sentry waiting state on its own")
        XCTAssertEqual(rig.controller.statusMessage, ConversationController.sentryWaitingMessage)

        // Sentry works normally from here (the detector gets a beat to
        // calibrate, same as any fresh `.idle` — it never ran while blocked).
        rig.silence(800)
        rig.speak(600)
        rig.wake.hear()
        XCTAssertEqual(rig.controller.phase, .listening)
        XCTAssertFalse(rig.socket.log.isEmpty)
    }

    func testDisconnectingMidSentryCaptureDropsItWithoutSendingAnything() {
        let rig = Rig.sentryIdle()
        rig.speak(400) // held locally, wake not yet heard
        XCTAssertEqual(rig.wake.utterances, 1)
        XCTAssertTrue(rig.socket.log.isEmpty)

        rig.socket.isOpen = false
        rig.socket.onStateChange?(.disconnected)
        XCTAssertEqual(rig.controller.phase, .sentryBlocked)
        XCTAssertTrue(rig.socket.log.isEmpty, "the held capture never reaches the server")

        // Keeps saying nothing while blocked, even if the mic is still live.
        rig.speak(400)
        XCTAssertTrue(rig.socket.log.isEmpty)

        // Reconnect: fresh start, no stale held audio resent.
        rig.socket.isOpen = true
        rig.socket.onStateChange?(.connected)
        XCTAssertEqual(rig.controller.phase, .idle)
        rig.speak(500)
        rig.wake.hear()
        XCTAssertEqual(rig.controller.phase, .listening)
        XCTAssertLessThan(
            PCMFormat.durationMs(ofBytes: rig.socket.audio.count), 3000,
            "only the fresh utterance's audio went out, not anything held before the disconnect"
        )
    }

    func testSwitchingToSentryModeWhileDisconnectedBlocksImmediately() {
        let rig = Rig.idle() // conversation mode, never connected either
        XCTAssertEqual(rig.controller.phase, .idle)
        rig.controller.setVoiceMode(.sentry)
        XCTAssertEqual(rig.controller.phase, .sentryBlocked)
    }

    func testSwitchingBackToConversationModeClearsTheSentryBlock() {
        let rig = Rig.idle(voiceMode: .sentry)
        XCTAssertEqual(rig.controller.phase, .sentryBlocked)
        rig.controller.setVoiceMode(.conversation)
        XCTAssertEqual(rig.controller.phase, .idle)
        XCTAssertEqual(rig.controller.statusMessage, "Say \"Hey Nova\".")
    }

    func testTurningNovaOffFromSentryBlockedGoesFullyOff() {
        let rig = Rig.idle(voiceMode: .sentry)
        XCTAssertEqual(rig.controller.phase, .sentryBlocked)
        rig.controller.setEnabled(false)
        XCTAssertEqual(rig.controller.phase, .off)
        rig.speak(500)
        XCTAssertTrue(rig.socket.log.isEmpty)
    }
}
