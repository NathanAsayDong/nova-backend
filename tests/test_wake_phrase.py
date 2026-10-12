import unittest

from src.controller.nova_controller import has_wake_phrase, split_wake_phrase


class WakePhraseTests(unittest.TestCase):
    def test_exact_wake_phrases(self):
        for text in ("Nova", "Hey Nova.", "okay nova what's the weather", "yo nova please"):
            self.assertTrue(has_wake_phrase(text), text)

    def test_common_mishearings_still_wake(self):
        for text in ("Hey Noah.", "Noah?", "hey no va", "Hey Nover", "Novah, are you there"):
            self.assertTrue(has_wake_phrase(text), text)

    def test_unrelated_speech_does_not_wake(self):
        for text in ("", "No.", "I told Noah about the meeting yesterday", "no worries at all"):
            self.assertFalse(has_wake_phrase(text), text)


class SplitWakePhraseTests(unittest.TestCase):
    """Sentry mode: the wake phrase must open the utterance, and the rest is the request."""

    def test_request_in_the_same_breath_is_kept_verbatim(self):
        cases = {
            "Hey Nova, what's on my calendar today?": "what's on my calendar today?",
            "Nova what time is it": "what time is it",
            "OK Nova. Turn off the lights.": "Turn off the lights.",
            "Hey Noah, remind me to call Sam.": "remind me to call Sam.",
            "hey no va set a timer": "set a timer",
            "Alright Nova - how's the weather": "how's the weather",
        }
        for text, request in cases.items():
            self.assertEqual(split_wake_phrase(text), request, text)

    def test_bare_wake_phrase_means_wait_for_the_request(self):
        for text in ("Hey Nova.", "Nova?", "okay nova", "Hey Nova, um", "Nova, are you there?"):
            self.assertEqual(split_wake_phrase(text), "", text)

    def test_nova_mentioned_mid_sentence_is_not_a_wake(self):
        for text in (
            "I asked Nova yesterday",
            "can you ask nova later",
            "hey can nova do that",
            "No, that's fine.",
            "",
        ):
            self.assertIsNone(split_wake_phrase(text), text)


if __name__ == "__main__":
    unittest.main()
