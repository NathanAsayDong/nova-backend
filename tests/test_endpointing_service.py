import unittest

from src.service.endpointing_service import (
    DEFAULT_SILENCE_MS,
    MAX_SILENCE_MS,
    MIN_SILENCE_MS,
    PENDING_SILENCE_MS,
    STATEMENT_SILENCE_MS,
    endpoint_decision,
    silence_budget_ms,
)


class EndpointDecisionTests(unittest.TestCase):
    def assert_window(self, transcript, expected_ms, expected_reason=None):
        decision = endpoint_decision(transcript)
        self.assertEqual(
            decision.silence_ms, expected_ms, f"transcript={transcript!r} ({decision.reason})"
        )
        if expected_reason is not None:
            self.assertEqual(decision.reason, expected_reason, f"transcript={transcript!r}")

    def test_no_transcript_gets_the_neutral_window(self):
        # Nothing has been transcribed yet, so there is no semantic evidence
        # either way and the acoustic detector is on its own.
        self.assert_window("", DEFAULT_SILENCE_MS, "no_transcript")
        self.assert_window(None, DEFAULT_SILENCE_MS, "no_transcript")
        self.assert_window("   ", DEFAULT_SILENCE_MS, "no_transcript")

    def test_punctuation_only_transcript_has_no_words(self):
        self.assert_window("...", DEFAULT_SILENCE_MS, "no_words")

    def test_questions_get_the_floor_statements_get_grace(self):
        # A question mark is rarely fake — a question to an assistant is over
        # when it is asked. A period is Whisper's habit: real dictation pauses
        # between complete sentences, so statements keep a thinking pause.
        self.assert_window(
            "What did we decide about the migration?",
            MIN_SILENCE_MS,
            "terminal_question",
        )
        self.assert_window(
            "Send Sophie the deploy notes.",
            STATEMENT_SILENCE_MS,
            "terminal_statement",
        )
        self.assertLess(STATEMENT_SILENCE_MS, DEFAULT_SILENCE_MS)

    def test_ellipsis_reads_as_trailing_off(self):
        # Whisper writes down a trail-off as an ellipsis; it must not be
        # mistaken for a finished statement's period.
        self.assert_window("I was thinking...", PENDING_SILENCE_MS, "ellipsis")
        self.assert_window("I was thinking…", PENDING_SILENCE_MS, "ellipsis")

    def test_hard_continuations_hold_the_line(self):
        for transcript in (
            "Can you send this to",
            "I want to deploy the backend and",
            "Put that in the",
            "Check the calendar because",
        ):
            self.assert_window(transcript, MAX_SILENCE_MS, "hard_continuation")

    def test_whisper_punctuating_a_fragment_does_not_end_the_turn(self):
        # Whisper punctuates whatever fragment it is handed, so the period
        # here is a decoding artifact and the dangling "to" is the real
        # evidence. Hard-continuation checks must beat punctuation checks.
        self.assert_window("Can you send this to.", MAX_SILENCE_MS, "hard_continuation")
        self.assert_window("Check that in the.", MAX_SILENCE_MS, "hard_continuation")

    def test_filler_words_hold_the_line(self):
        self.assert_window("Email that to, um", MAX_SILENCE_MS, "filler")
        self.assert_window("Let me think. Uh", MAX_SILENCE_MS, "filler")

    # --- regressions from the first live test -------------------------------
    # These are all COMPLETE spoken sentences that the first lexicon treated
    # as unfinished (pronouns and particles were on the hard list), so every
    # one of them waited the maximum window — slower than the fixed timeout
    # this whole thing replaced.

    def test_final_pronouns_do_not_hold_the_line(self):
        # Three-word-plus clauses ending in a pronoun read as neutral; the one
        # thing none of these may get is the maximum hold.
        for transcript in ("What time is it", "Can you fix it"):
            self.assert_window(transcript, DEFAULT_SILENCE_MS, "unpunctuated_clause")
        self.assertLess(
            endpoint_decision("Remember that").silence_ms, MAX_SILENCE_MS
        )

    def test_complete_commands_ending_in_a_particle_get_at_most_pending(self):
        # "on"/"off" genuinely can dangle ("turn the volume of..."), so they
        # get the middle window — never the maximum hold.
        for transcript in ("Turn the lights on", "Turn it off", "What's going on"):
            self.assert_window(transcript, PENDING_SILENCE_MS, "soft_continuation")

    def test_terminal_punctuation_beats_a_soft_continuation(self):
        # Whisper reads a finished command as finished; trust it over the
        # particle. "Turn it off." ends on the statement tier, not the hold.
        for transcript in ("Turn it off.", "Turn the lights on.", "I think so."):
            self.assert_window(transcript, STATEMENT_SILENCE_MS, "terminal_statement")
        self.assert_window("What are you waiting for?", MIN_SILENCE_MS)

    def test_sentence_final_adverbs_get_at_most_pending(self):
        # "so"/"though"/"then" close sentences all the time in speech.
        for transcript in ("I think so", "It's fine though", "Do it then"):
            self.assert_window(transcript, PENDING_SILENCE_MS, "soft_continuation")

    # ------------------------------------------------------------------------

    def test_trailing_digits_get_pending_even_with_a_period(self):
        # Mid-dictation of a number: Whisper writes "801." while the phone
        # number is still in progress, so digits beat punctuation.
        self.assert_window("My number is 801.", PENDING_SILENCE_MS, "digits")
        self.assert_window("Set a timer for 15", PENDING_SILENCE_MS, "digits")

    def test_pending_punctuation_waits_longer_than_a_full_stop(self):
        self.assert_window(
            "First the tests, then the deploy,",
            PENDING_SILENCE_MS,
            "pending_punctuation",
        )

    def test_auxiliaries_and_question_words_get_pending(self):
        self.assert_window("Do you know what", PENDING_SILENCE_MS, "soft_continuation")
        self.assert_window("I wonder if it will", PENDING_SILENCE_MS, "soft_continuation")

    def test_short_acknowledgments_are_complete(self):
        # Punctuated ones resolve via the period, bare ones via the standalone
        # list; either way the answer is the floor.
        for transcript in ("Yes.", "yeah", "No", "Stop.", "Thanks", "Okay"):
            self.assert_window(transcript, MIN_SILENCE_MS)

    def test_short_fragments_are_not(self):
        self.assert_window("The migration", PENDING_SILENCE_MS, "short_fragment")
        self.assert_window("Sophie", PENDING_SILENCE_MS, "short_fragment")

    def test_unpunctuated_clause_gets_the_neutral_window(self):
        self.assert_window(
            "deploy the backend tonight", DEFAULT_SILENCE_MS, "unpunctuated_clause"
        )

    def test_windows_are_ordered(self):
        self.assertLess(MIN_SILENCE_MS, STATEMENT_SILENCE_MS)
        self.assertLess(STATEMENT_SILENCE_MS, DEFAULT_SILENCE_MS)
        self.assertLess(DEFAULT_SILENCE_MS, PENDING_SILENCE_MS)
        self.assertLess(PENDING_SILENCE_MS, MAX_SILENCE_MS)

    def test_max_hold_is_not_slower_than_it_needs_to_be(self):
        # The ceiling exists for genuine dangles; it must still feel like a
        # conversation, not a timeout.
        self.assertLessEqual(MAX_SILENCE_MS, 2500)

    def test_silence_budget_ms_matches_the_decision(self):
        self.assertEqual(
            silence_budget_ms("Send Sophie the deploy notes."), STATEMENT_SILENCE_MS
        )


if __name__ == "__main__":
    unittest.main()
