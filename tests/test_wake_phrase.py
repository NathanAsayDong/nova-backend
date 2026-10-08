import unittest

from src.controller.nova_controller import has_wake_phrase


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


if __name__ == "__main__":
    unittest.main()
