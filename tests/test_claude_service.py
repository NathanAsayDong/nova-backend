"""
Per-model request settings.

Opus 5 and Sonnet 5 think by default at high effort, with the thinking
hidden. For a voice assistant that is a silence before the first word, so the
effort is turned down on the models that take the parameter — and left off
the ones that reject it.
"""

import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from src.harness.turn_timer import TurnTimer
from src.service.claude_service import ClaudeService, TurnStream


class _FakeUsage:
    """Stands in for anthropic.types.Usage with only the fields this needs."""

    def __init__(
        self,
        input_tokens=None,
        cache_creation_input_tokens=None,
        cache_read_input_tokens=None,
        output_tokens=None,
    ):
        self.input_tokens = input_tokens
        self.cache_creation_input_tokens = cache_creation_input_tokens
        self.cache_read_input_tokens = cache_read_input_tokens
        self.output_tokens = output_tokens


class _FakeMessage:
    def __init__(self, usage=None, stop_reason="end_turn"):
        self.usage = usage
        self.stop_reason = stop_reason
        self.content = []


class _FakeStream:
    """A no-op context manager standing in for the Anthropic SDK stream."""

    def __init__(self, final_message):
        self._final_message = final_message

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def __iter__(self):
        return iter(())

    def get_final_message(self):
        return self._final_message


def _drain(open_stream, timer=None, round_no=None):
    stream = TurnStream(open_stream, timer=timer, round_no=round_no)
    list(stream)
    return stream


class TurnStreamUsageMarkTests(unittest.TestCase):
    """The `usage` [timing] mark TurnStream emits once a round completes."""

    def test_normal_values_compute_cache_hit_pct(self):
        message = _FakeMessage(
            usage=_FakeUsage(
                input_tokens=100,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=900,
                output_tokens=50,
            )
        )
        timer = TurnTimer("abc123", start=100.0)
        with redirect_stdout(io.StringIO()) as buf:
            _drain(lambda: _FakeStream(message), timer=timer, round_no=1)
        lines = buf.getvalue().splitlines()
        usage_line = next(line for line in lines if " usage " in line)
        self.assertIn("round=1", usage_line)
        self.assertIn("input=100", usage_line)
        self.assertIn("cache_read=900", usage_line)
        self.assertIn("cache_write=0", usage_line)
        self.assertIn("output=50", usage_line)
        self.assertIn("cache_hit_pct=90", usage_line)

    def test_missing_fields_are_treated_as_zero(self):
        # usage present but every field None, as the SDK can report mid-stream.
        message = _FakeMessage(usage=_FakeUsage())
        timer = TurnTimer("abc123", start=100.0)
        with redirect_stdout(io.StringIO()) as buf:
            _drain(lambda: _FakeStream(message), timer=timer, round_no=1)
        usage_line = next(line for line in buf.getvalue().splitlines() if " usage " in line)
        self.assertIn("input=0", usage_line)
        self.assertIn("cache_read=0", usage_line)
        self.assertIn("cache_write=0", usage_line)
        self.assertIn("output=0", usage_line)
        self.assertIn("cache_hit_pct=n/a", usage_line)

    def test_no_usage_object_at_all_is_treated_as_zero(self):
        message = _FakeMessage(usage=None)
        timer = TurnTimer("abc123", start=100.0)
        with redirect_stdout(io.StringIO()) as buf:
            _drain(lambda: _FakeStream(message), timer=timer, round_no=1)
        usage_line = next(line for line in buf.getvalue().splitlines() if " usage " in line)
        self.assertIn("input=0", usage_line)
        self.assertIn("cache_read=0", usage_line)
        self.assertIn("cache_write=0", usage_line)
        self.assertIn("output=0", usage_line)
        self.assertIn("cache_hit_pct=n/a", usage_line)

    def test_zero_denominator_reports_n_a_not_a_crash(self):
        # input, cache_read and cache_write all zero: nothing to divide by.
        message = _FakeMessage(
            usage=_FakeUsage(
                input_tokens=0,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
                output_tokens=12,
            )
        )
        timer = TurnTimer("abc123", start=100.0)
        with redirect_stdout(io.StringIO()) as buf:
            _drain(lambda: _FakeStream(message), timer=timer, round_no=1)
        usage_line = next(line for line in buf.getvalue().splitlines() if " usage " in line)
        self.assertIn("cache_hit_pct=n/a", usage_line)

    def test_none_timer_does_not_raise_and_prints_nothing(self):
        message = _FakeMessage(
            usage=_FakeUsage(
                input_tokens=10,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=90,
                output_tokens=5,
            )
        )
        with redirect_stdout(io.StringIO()) as buf:
            stream = _drain(lambda: _FakeStream(message), timer=None, round_no=1)
        self.assertEqual(buf.getvalue(), "")
        self.assertIs(stream.message, message)


class GenerationKwargsTests(unittest.TestCase):
    def setUp(self):
        self.service = ClaudeService()

    def test_haiku_is_sent_no_effort(self):
        self.service.MODEL = "claude-haiku-4-5"

        self.assertEqual(self.service._generation_kwargs(), {})

    def test_opus_5_is_turned_down_to_medium_effort(self):
        self.service.MODEL = "claude-opus-5"

        self.assertEqual(
            self.service._generation_kwargs(), {"output_config": {"effort": "medium"}}
        )

    def test_sonnet_5_is_turned_down_too(self):
        self.service.MODEL = "claude-sonnet-5"

        self.assertEqual(
            self.service._generation_kwargs(), {"output_config": {"effort": "medium"}}
        )

    def test_effort_is_configurable(self):
        with patch.dict(os.environ, {"NOVA_CLAUDE_EFFORT": "high"}):
            self.assertEqual(ClaudeService().effort, "high")

    def test_an_unknown_effort_falls_back_to_medium(self):
        with patch.dict(os.environ, {"NOVA_CLAUDE_EFFORT": "turbo"}):
            self.assertEqual(ClaudeService().effort, "medium")

    def test_the_output_ceiling_leaves_room_for_thinking(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_MAX_TOKENS", None)
            self.assertEqual(ClaudeService().max_tokens, 8192)
