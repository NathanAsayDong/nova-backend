"""
Unit coverage for the seam between what Nova writes and what Nova says.

The spoken reply is the written reply, read aloud, minus the markdown that has
no spoken form. These tests are about where that line falls, and about saying
it as the text streams in rather than after the last token.
"""

import unittest

from src.harness.spoken_reply import (
    LIVE_HOLD_CHARS,
    MAX_SPOKEN_CHARS,
    LiveReply,
    SpokenProse,
    clamp_spoken,
    is_repeat,
    speech_summary,
    strip_speak_tags,
)


def _said(*deltas: str) -> str:
    prose = SpokenProse()
    lines: list[str] = []
    for delta in deltas:
        lines.extend(prose.push(delta))
    lines.extend(prose.finish())
    return " ".join(lines)


class StripSpeakTagsTests(unittest.TestCase):
    def test_keeps_the_words_and_drops_the_markup(self):
        self.assertEqual(
            strip_speak_tags("<speak>Done.</speak>\n\nDetails."), "Done.\n\nDetails."
        )

    def test_an_unclosed_tag_does_not_leak_markup(self):
        self.assertEqual(strip_speak_tags("<speak>Still talking"), "Still talking")

    def test_text_without_a_tag_is_untouched(self):
        text = "Plain reply.\n\n- one\n- two\n"
        self.assertEqual(strip_speak_tags(text), text)


class SpeechSummaryTests(unittest.TestCase):
    def test_says_every_sentence(self):
        self.assertEqual(
            speech_summary("One. Two. Three. Four."), "One. Two. Three. Four."
        )

    def test_drops_code_blocks_and_tables(self):
        summary = speech_summary(
            "Here's the patch.\n\n```python\nprint('x')\n```\n\n"
            "| col | col |\n| --- | --- |\n"
        )

        self.assertEqual(summary, "Here's the patch.")

    def test_lists_are_markdown_and_stay_on_screen(self):
        summary = speech_summary("Three things happened.\n\n- Migrations ran.\n- Cache is warm.")

        self.assertEqual(summary, "Three things happened.")

    def test_numbered_lists_stay_on_screen_too(self):
        self.assertEqual(speech_summary("1. First step.\n2. Second step."), "")

    def test_headings_are_skipped_and_inline_markup_is_unwrapped(self):
        summary = speech_summary(
            "## Status\n\nThe **build** passed on [main](https://example.com/x), "
            "see `ci.yml`."
        )

        self.assertEqual(summary, "The build passed on main, see ci.yml.")

    def test_a_hashtag_is_not_a_heading(self):
        self.assertEqual(speech_summary("#winning today."), "#winning today.")

    def test_nothing_sayable_yields_silence(self):
        self.assertEqual(speech_summary("```\nnot speech\n```"), "")

    def test_text_after_a_code_block_is_spoken_again(self):
        summary = speech_summary("Before.\n\n```\nx = 1\n```\n\nAfter.")

        self.assertEqual(summary, "Before. After.")


class SpokenProseTests(unittest.TestCase):
    def test_a_sentence_is_released_when_it_is_finished_not_before(self):
        prose = SpokenProse()
        first = "The unit suite passed in four seconds and nothing regressed. "

        self.assertEqual(prose.push(first[:30]), [])
        self.assertEqual(
            prose.push(first[30:] + "Next"),
            ["The unit suite passed in four seconds and nothing regressed."],
        )
        self.assertEqual(prose.finish(), ["Next"])

    def test_whitespace_survives_being_split_across_deltas(self):
        self.assertEqual(
            _said("The migration finished. ", "It touched 12 tables."),
            "The migration finished. It touched 12 tables.",
        )

    def test_short_sentences_are_batched_into_one_line(self):
        prose = SpokenProse()

        lines = prose.push("Yes. ") + prose.push("Done. ") + prose.finish()

        self.assertEqual(lines, ["Yes. Done."])

    def test_a_code_fence_split_across_deltas_is_still_skipped(self):
        self.assertEqual(
            _said("Here it is.\n\n``", "`python\nprint(1)\n``", "`\n\nThat is all."),
            "Here it is. That is all.",
        )

    def test_a_table_split_across_deltas_is_still_skipped(self):
        self.assertEqual(
            _said("Two rows.\n\n| a", " | b |\n| - | - |\n"),
            "Two rows.",
        )

    def test_a_list_marker_split_across_deltas_is_still_skipped(self):
        self.assertEqual(_said("Items:\n\n-", " first item\n- second item\n"), "Items:")

    def test_a_line_break_ends_a_sentence_without_punctuation(self):
        self.assertEqual(_said("Heads up\nNext line."), "Heads up Next line.")

    def test_a_stray_speak_tag_is_not_said(self):
        self.assertEqual(_said("<speak>Hi there.</speak>"), "Hi there.")


class ClampSpokenTests(unittest.TestCase):
    def test_a_chatty_progress_line_is_held_to_a_couple_of_sentences(self):
        clamped = clamp_spoken("One. Two. Three. Four. Five.")

        self.assertEqual(clamped, "One. Two.")

    def test_short_line_passes_through_unchanged(self):
        self.assertEqual(clamp_spoken("On it."), "On it.")

    def test_newlines_inside_a_spoken_line_are_flattened(self):
        self.assertEqual(clamp_spoken("On\n  it."), "On it.")

    def test_empty_stays_empty(self):
        self.assertEqual(clamp_spoken("   "), "")

    def test_one_runaway_sentence_is_cut_at_a_word_boundary(self):
        clamped = clamp_spoken("word " * 400)

        self.assertLessEqual(len(clamped), MAX_SPOKEN_CHARS + 1)
        self.assertTrue(clamped.endswith("…"))
        self.assertFalse(clamped.endswith("wor…"))


class IsRepeatTests(unittest.TestCase):
    def test_punctuation_and_case_do_not_make_a_new_line(self):
        self.assertTrue(is_repeat("On it!", "on it."))

    def test_different_lines_are_not_repeats(self):
        self.assertFalse(is_repeat("On it.", "Done."))

    def test_nothing_repeats_nothing(self):
        self.assertFalse(is_repeat("", ""))


class LiveReplyTests(unittest.TestCase):
    """
    One round of a reply, read as it is written.

    A round's first sentence looks the same whether it is the answer or a
    pre-tool "let me check", so both the prose on screen and the speech are
    held until the text itself, a tool_use start, or the end of the round
    settles which it was.
    """

    def test_a_short_reply_is_held_then_released_whole(self):
        live = LiveReply()

        self.assertEqual(live.push("Sure thing. "), [])
        self.assertEqual(live.push("Here it is."), [])
        self.assertEqual(
            live.finish(),
            [
                {"type": "speech_text", "text": "Sure thing. Here it is.", "role": "final"},
                {"type": "text", "text": "Sure thing. Here it is."},
            ],
        )

    def test_a_long_reply_goes_live_once_it_is_plainly_an_answer(self):
        live = LiveReply()
        opening = ("A sentence that is long enough to be said. " * 6).rstrip()

        events = live.push(opening)

        self.assertGreaterEqual(len(opening), LIVE_HOLD_CHARS)
        self.assertEqual(events[-1], {"type": "text", "text": opening})
        self.assertTrue(
            all(e["type"] == "speech_text" and e["role"] == "final" for e in events[:-1])
        )
        self.assertTrue(events[:-1])
        # Live from here: text passes straight through, whitespace intact, and
        # each finished sentence is said as it lands.
        more = live.push(" And one more. Then")
        self.assertEqual(more[-1], {"type": "text", "text": " And one more. Then"})
        self.assertEqual(live.streamed, opening + " And one more. Then")

    def test_an_acknowledgment_never_reaches_the_screen_as_prose(self):
        live = LiveReply()

        self.assertEqual(live.push("Let me check your calendar."), [])
        self.assertEqual(
            live.tool_use_started(),
            [{"type": "speech_text", "text": "Let me check your calendar.", "role": "status"}],
        )
        self.assertEqual(live.finish(), [])
        self.assertTrue(live.tool_round)
        self.assertEqual(live.streamed, "")

    def test_a_multi_sentence_acknowledgment_is_one_status_line(self):
        live = LiveReply()
        live.push("Let me check. ")
        live.push("One moment.")

        self.assertEqual(
            live.tool_use_started(),
            [{"type": "speech_text", "text": "Let me check. One moment.", "role": "status"}],
        )

    def test_a_round_handed_in_complete_is_told_what_it_was(self):
        live = LiveReply()
        live.push("On it.")

        self.assertEqual(
            live.finish(tool_round=True),
            [{"type": "speech_text", "text": "On it.", "role": "status"}],
        )
        self.assertTrue(live.tool_round)

    def test_markdown_goes_to_the_screen_and_not_to_the_speaker(self):
        live = LiveReply()

        live.push("Two results.\n\n| a | b |\n| - | - |\n- one\n")
        events = live.finish()

        self.assertEqual(
            [e for e in events if e["type"] == "speech_text"],
            [{"type": "speech_text", "text": "Two results.", "role": "final"}],
        )
        self.assertIn("| a | b |", live.streamed)

    def test_a_reply_that_is_all_markdown_says_nothing_itself(self):
        live = LiveReply()
        live.push("| a | b |\n| - | - |\n")

        self.assertEqual(
            [e for e in live.finish() if e["type"] == "speech_text"], []
        )

    def test_prose_that_went_live_before_a_tool_call_is_remembered(self):
        """So the end-of-round path can skip captioning what is already on screen."""
        live = LiveReply()
        preamble = "p" * LIVE_HOLD_CHARS

        self.assertEqual(live.push(preamble), [{"type": "text", "text": preamble}])
        self.assertEqual(
            live.tool_use_started(),
            [{"type": "speech_text", "text": preamble, "role": "final"}],
        )
        self.assertEqual(live.streamed, preamble)
        self.assertTrue(live.tool_round)


if __name__ == "__main__":
    unittest.main()
