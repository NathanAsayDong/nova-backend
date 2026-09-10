"""
Unit coverage for the seam between what Nova says and what Nova writes.

The prompt asks the model for a `<speak>` block. These tests are about what
happens when it complies, when it half-complies, and when it ignores the
instruction entirely — because the brevity of the spoken track has to be a
property of the system, not a hope about the model.
"""

import unittest

from src.harness.spoken_reply import (
    LIVE_HOLD_CHARS,
    MAX_SPOKEN_CHARS,
    LiveReply,
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


class LiveReplyTests(unittest.TestCase):
    """
    One round of a reply, read as it is written.

    The hard question is not the spoken line — the watcher handles that — but
    when prose may go to the screen. A round's first sentence looks the same
    whether it is the answer or a pre-tool "let me check", so prose is held
    until the text itself, a tool_use start, or the end of the round settles
    which it was.
    """

    def test_a_short_reply_is_held_then_released_whole(self):
        live = LiveReply()

        self.assertEqual(live.push("Sure thing. "), [])
        self.assertEqual(live.push("Here it is."), [])
        self.assertEqual(
            live.finish(), [{"type": "text", "text": "Sure thing. Here it is."}]
        )

    def test_a_long_reply_goes_live_once_it_is_plainly_an_answer(self):
        live = LiveReply()
        opening = "x" * LIVE_HOLD_CHARS

        self.assertEqual(live.push(opening), [{"type": "text", "text": opening}])
        # Live from here: every delta passes straight through, whitespace intact.
        self.assertEqual(live.push(" more"), [{"type": "text", "text": " more"}])
        self.assertEqual(live.finish(), [])
        self.assertEqual(live.streamed, opening + " more")

    def test_an_acknowledgment_never_reaches_the_screen_as_prose(self):
        live = LiveReply()

        self.assertEqual(live.push("Let me check your calendar."), [])
        self.assertEqual(live.tool_use_started(), [])
        self.assertEqual(live.finish(), [])
        self.assertTrue(live.tool_round)
        self.assertEqual(live.streamed, "")

    def test_a_tagged_acknowledgment_is_a_status_line_the_moment_the_tool_opens(self):
        live = LiveReply()

        # Closed, but whose line is it? Not knowable yet.
        self.assertEqual(live.push("<speak>Checking your calendar.</speak>"), [])
        self.assertEqual(
            live.tool_use_started(),
            [{"type": "speech_text", "text": "Checking your calendar.", "role": "status"}],
        )
        self.assertEqual(live.finish(), [])

    def test_a_tagged_line_followed_by_prose_is_the_answer(self):
        live = LiveReply()

        self.assertEqual(live.push("<speak>Both passed.</speak>"), [])
        # Whitespace after the tag settles nothing.
        self.assertEqual(live.push("\n\n"), [])
        self.assertEqual(
            live.push("## Results"),
            [{"type": "speech_text", "text": "Both passed.", "role": "final"}],
        )
        # The prose is short of going live, so it is released at the end —
        # exactly as written, tag excluded.
        self.assertEqual(live.finish(), [{"type": "text", "text": "\n\n## Results"}])

    def test_a_tagged_line_alone_is_the_answer_at_the_end(self):
        live = LiveReply()
        live.push("<speak>Done.</speak>")

        self.assertEqual(
            live.finish(), [{"type": "speech_text", "text": "Done.", "role": "final"}]
        )

    def test_a_round_handed_in_complete_is_told_what_it_was(self):
        live = LiveReply()
        live.push("<speak>On it.</speak>")

        self.assertEqual(
            live.finish(tool_round=True),
            [{"type": "speech_text", "text": "On it.", "role": "status"}],
        )
        self.assertTrue(live.tool_round)

    def test_an_unclosed_tag_never_reaches_the_screen(self):
        live = LiveReply()

        events = live.push("<speak>Still talking and never closing. " * 10)

        self.assertEqual(events, [])
        self.assertEqual(live.finish(), [])
        self.assertEqual(live.streamed, "")

    def test_a_block_on_a_chat_turn_is_still_not_prose(self):
        """The loop drops the speech on a chat turn; the tag stays off screen either way."""
        live = LiveReply()
        prose = "y" * LIVE_HOLD_CHARS

        events = live.push("<speak>Hi.</speak>" + prose)

        self.assertEqual(
            events,
            [
                {"type": "speech_text", "text": "Hi.", "role": "final"},
                {"type": "text", "text": prose},
            ],
        )

    def test_prose_that_went_live_before_a_tool_call_is_remembered(self):
        """So the end-of-round path can skip captioning what is already on screen."""
        live = LiveReply()
        preamble = "p" * LIVE_HOLD_CHARS

        self.assertEqual(live.push(preamble), [{"type": "text", "text": preamble}])
        self.assertEqual(live.tool_use_started(), [])
        self.assertEqual(live.streamed, preamble)
        self.assertTrue(live.tool_round)
