"""
Unit coverage for the seam between what Nova says and what Nova writes.

The prompt asks the model for a `<speak>` block. These tests are about what
happens when it complies, when it half-complies, and when it ignores the
instruction entirely — because the brevity of the spoken track has to be a
property of the system, not a hope about the model.
"""

import unittest

from src.harness.spoken_reply import (
    MAX_SPOKEN_CHARS,
    SpokenLineWatcher,
    clamp_spoken,
    speech_summary,
    split_spoken_reply,
)


class SplitSpokenReplyTests(unittest.TestCase):
    def test_pulls_speak_block_out_of_the_written_answer(self):
        display, spoken = split_spoken_reply(
            "<speak>Deploy's live.</speak>\n\n## Deploy\n\nAll three checks passed."
        )

        self.assertEqual(spoken, "Deploy's live.")
        self.assertEqual(display, "## Deploy\n\nAll three checks passed.")

    def test_written_answer_keeps_its_markdown_intact(self):
        display, _ = split_spoken_reply(
            "<speak>Here's the fix.</speak>\n"
            "```python\nx = 1\n```\n"
            "- first\n- second\n"
        )

        self.assertIn("```python\nx = 1\n```", display)
        self.assertIn("- first\n- second", display)

    def test_no_block_leaves_the_reply_untouched(self):
        display, spoken = split_spoken_reply("Just an ordinary chat reply.")

        self.assertEqual(display, "Just an ordinary chat reply.")
        self.assertIsNone(spoken)

    def test_block_only_reply_still_has_something_to_show(self):
        """A one-line answer has no longer written form; show the line."""
        display, spoken = split_spoken_reply("<speak>It's 3pm.</speak>")

        self.assertEqual(spoken, "It's 3pm.")
        self.assertEqual(display, "It's 3pm.")

    def test_unclosed_tag_does_not_leak_markup_onto_the_screen(self):
        display, spoken = split_spoken_reply("<speak>Running it now.")

        self.assertEqual(spoken, "Running it now.")
        self.assertNotIn("<speak", display)

    def test_tag_is_stripped_even_when_the_medium_did_not_ask_for_one(self):
        """
        A chat turn has no spoken track, but a model that emits the tag anyway
        must not put raw markup in the transcript.
        """
        display, _ = split_spoken_reply("<SPEAK>Hi.</SPEAK> The long version.")

        self.assertNotIn("SPEAK", display)
        self.assertEqual(display, "The long version.")


class SpeechSummaryTests(unittest.TestCase):
    def test_keeps_at_most_two_sentences(self):
        summary = speech_summary("One. Two. Three. Four.")

        self.assertEqual(summary, "One. Two.")

    def test_drops_code_blocks_and_tables(self):
        summary = speech_summary(
            "Here's the patch.\n\n```python\nprint('x')\n```\n\n"
            "| col | col |\n| --- | --- |\n"
        )

        self.assertEqual(summary, "Here's the patch.")

    def test_reads_list_items_as_prose_not_bullets(self):
        summary = speech_summary("- Migrations ran.\n- Cache is warm.\n- Done.")

        self.assertNotIn("-", summary)
        self.assertEqual(summary, "Migrations ran. Cache is warm.")

    def test_unwraps_headings_links_and_emphasis(self):
        summary = speech_summary(
            "## Status\n\nThe **build** passed on [main](https://example.com/x)."
        )

        self.assertEqual(summary, "Status The build passed on main.")

    def test_nothing_sayable_yields_silence(self):
        self.assertEqual(speech_summary("```\nnot speech\n```"), "")

    def test_one_runaway_sentence_is_cut_at_a_word_boundary(self):
        summary = speech_summary("word " * 400)

        self.assertLessEqual(len(summary), MAX_SPOKEN_CHARS + 1)
        self.assertTrue(summary.endswith("…"))
        self.assertFalse(summary.endswith("wor…"))


class ClampSpokenTests(unittest.TestCase):
    def test_a_model_that_ignores_the_ceiling_is_held_to_it_anyway(self):
        clamped = clamp_spoken("One. Two. Three. Four. Five.")

        self.assertEqual(clamped, "One. Two.")

    def test_short_line_passes_through_unchanged(self):
        self.assertEqual(clamp_spoken("On it."), "On it.")

    def test_newlines_inside_a_spoken_line_are_flattened(self):
        self.assertEqual(clamp_spoken("On\n  it."), "On it.")

    def test_empty_stays_empty(self):
        self.assertEqual(clamp_spoken("   "), "")


class SpokenLineWatcherTests(unittest.TestCase):
    """
    Reading the reply as it is written. A real stream splits wherever the
    tokenizer happens to split, so the tag arrives in pieces.
    """

    @staticmethod
    def _feed(deltas: list[str]) -> list[tuple[int, str]]:
        """Every line the watcher reported, with the delta index that did it."""
        watcher = SpokenLineWatcher()
        fired = []
        for index, delta in enumerate(deltas):
            line = watcher.push(delta)
            if line is not None:
                fired.append((index, line))
        return fired

    def test_fires_on_the_delta_that_closes_the_tag(self):
        fired = self._feed(
            ["<spe", "ak>Both checks", " passed.</spe", "ak>", "\n\n## Results", " and more"]
        )

        self.assertEqual(fired, [(3, "Both checks passed.")])

    def test_never_fires_twice(self):
        fired = self._feed(
            ["<speak>One.</speak>", "<speak>Two.</speak>", "trailing"]
        )

        self.assertEqual(len(fired), 1)
        self.assertEqual(fired[0][1], "One.")

    def test_an_unclosed_block_never_fires(self):
        self.assertEqual(self._feed(["<speak>Still going", " and going"]), [])

    def test_a_reply_that_declines_the_format_never_fires(self):
        self.assertEqual(
            self._feed(["Plain prose. ", "More prose. ", "Even more."]), []
        )

    def test_stops_watching_once_the_opener_is_clearly_not_coming(self):
        """
        The block is asked for first, so a page of prose without it settles
        the question — and a long generation should not keep re-scanning.
        """
        watcher = SpokenLineWatcher()
        watcher.push("Prose with an angle bracket > in it. " * 12)

        # A tag this late is not the opening block; it is content.
        self.assertIsNone(watcher.push("<speak>too late</speak>"))

    def test_an_empty_block_reports_nothing_to_say(self):
        self.assertEqual(self._feed(["<speak></speak>", "the answer"]), [])


if __name__ == "__main__":
    unittest.main()
