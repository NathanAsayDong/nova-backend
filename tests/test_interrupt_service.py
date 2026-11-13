"""
is_nova_interrupt_phrase: the matcher behind the "Nova stop" / "Nova pause"
mid-speech barge-in (src/service/interrupt_service.py).

Covers the positives the feature exists for, the negatives that keep it from
over-matching (a longer sentence that merely contains the words, Nova's own
voice saying "stop" without its name attached), and the punctuation/casing
variance real transcripts produce.
"""

import unittest

from src.service.interrupt_service import is_nova_interrupt_phrase


class PositiveMatchTests(unittest.TestCase):
    def test_the_bare_phrase(self):
        self.assertTrue(is_nova_interrupt_phrase("Nova stop"))
        self.assertTrue(is_nova_interrupt_phrase("Nova pause"))

    def test_case_insensitive(self):
        self.assertTrue(is_nova_interrupt_phrase("NOVA STOP"))
        self.assertTrue(is_nova_interrupt_phrase("nOvA pAuSe"))

    def test_punctuation_is_ignored(self):
        self.assertTrue(is_nova_interrupt_phrase("Nova, stop!"))
        self.assertTrue(is_nova_interrupt_phrase("Nova... pause?"))
        self.assertTrue(is_nova_interrupt_phrase("nova-stop"))

    def test_leading_words_of_a_short_utterance(self):
        self.assertTrue(is_nova_interrupt_phrase("Nova stop the music"))
        self.assertTrue(is_nova_interrupt_phrase("Nova pause please"))

    def test_exactly_four_words_still_matches(self):
        self.assertTrue(is_nova_interrupt_phrase("Nova stop right now"))

    def test_extra_whitespace(self):
        self.assertTrue(is_nova_interrupt_phrase("  Nova   stop  "))


class NegativeMatchTests(unittest.TestCase):
    def test_empty_or_blank(self):
        self.assertFalse(is_nova_interrupt_phrase(""))
        self.assertFalse(is_nova_interrupt_phrase("   "))

    def test_novas_own_voice_saying_stop_alone_is_not_a_match(self):
        # Echo safety: Nova saying the word "stop" mid-sentence, with no
        # wake word in front of it, can never trip its own interrupt.
        self.assertFalse(is_nova_interrupt_phrase("let's stop here for today"))
        self.assertFalse(is_nova_interrupt_phrase("stop"))
        self.assertFalse(is_nova_interrupt_phrase("please stop"))

    def test_a_longer_sentence_that_merely_contains_the_words(self):
        self.assertFalse(is_nova_interrupt_phrase("tell Nova stop words list"))
        self.assertFalse(
            is_nova_interrupt_phrase("can you remind me to tell Nova stop emailing")
        )

    def test_a_long_utterance_leading_with_the_phrase_still_does_not_match(self):
        # More than four words: this is about something else, even though it
        # starts with the exact words.
        self.assertFalse(
            is_nova_interrupt_phrase("Nova stop telling me about this please right now")
        )

    def test_reversed_word_order(self):
        self.assertFalse(is_nova_interrupt_phrase("stop Nova"))
        self.assertFalse(is_nova_interrupt_phrase("pause Nova"))

    def test_not_a_leading_match_when_nova_is_not_first(self):
        self.assertFalse(is_nova_interrupt_phrase("okay Nova stop"))
        self.assertFalse(is_nova_interrupt_phrase("hey Nova pause"))

    def test_similar_but_different_words_do_not_match(self):
        self.assertFalse(is_nova_interrupt_phrase("Nova pausing"))
        self.assertFalse(is_nova_interrupt_phrase("Nova stopped"))
        self.assertFalse(is_nova_interrupt_phrase("Nova stops"))


if __name__ == "__main__":
    unittest.main()
