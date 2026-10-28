import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from src.harness.turn_timer import TurnTimer, mark


class TurnTimerTests(unittest.TestCase):
    def test_mark_output_format(self):
        timer = TurnTimer("abc123", start=100.0)
        with patch("time.monotonic", return_value=100.25):
            with redirect_stdout(io.StringIO()) as buf:
                timer.mark("stop_received", speculative_ready=True)
        line = buf.getvalue().strip()
        self.assertIn("[timing] turn=abc123", line)
        self.assertIn("t=+250ms", line)
        self.assertIn("(+250ms)", line)
        self.assertIn("stop_received", line)
        self.assertIn("speculative_ready=True", line)

    def test_second_mark_delta_is_since_previous_mark(self):
        timer = TurnTimer("abc123", start=100.0)
        with patch("time.monotonic", return_value=100.25):
            timer.mark("stop_received")
        with redirect_stdout(io.StringIO()) as buf:
            with patch("time.monotonic", return_value=100.4):
                timer.mark("transcript_ready")
        line = buf.getvalue().strip()
        self.assertIn("t=+400ms", line)
        self.assertIn("(+150ms)", line)

    def test_repeated_mark_name_only_feeds_summary_once(self):
        """The SUMMARY stage uses the FIRST time a name was marked."""
        timer = TurnTimer("abc123", start=100.0)
        with patch("time.monotonic", return_value=100.1):
            timer.mark("model_request_sent", round=1)
        with patch("time.monotonic", return_value=100.2):
            timer.mark("first_text_delta", round=1)
        with patch("time.monotonic", return_value=100.9):
            # A later round's model_request_sent must not overwrite the
            # first one used for the model_request->first_token stage.
            timer.mark("model_request_sent", round=2)
        with redirect_stdout(io.StringIO()) as buf:
            timer.summary()
        line = buf.getvalue().strip()
        self.assertIn("model_request->first_token=100ms", line)

    def test_summary_reports_n_a_for_missing_stages(self):
        timer = TurnTimer("abc123", start=100.0)
        with patch("time.monotonic", return_value=100.5):
            timer.mark("stop_received")
        with redirect_stdout(io.StringIO()) as buf:
            timer.summary()
        line = buf.getvalue().strip()
        self.assertIn("SUMMARY", line)
        self.assertIn("stop->transcript=n/a", line)
        self.assertIn("transcript->model_request=n/a", line)
        self.assertIn("stop->first_audio_sent=n/a", line)
        self.assertIn("total=n/a", line)

    def test_summary_computes_full_stage_chain_and_total(self):
        timer = TurnTimer("abc123", start=0.0)
        schedule = {
            "stop_received": 0.0,
            "transcript_ready": 0.1,
            "model_request_sent": 0.2,
            "first_text_delta": 0.3,
            "first_speech_line": 0.35,
            "first_tts_byte": 0.5,
            "first_audio_sent": 0.6,
            "done": 1.0,
        }
        for name, at in schedule.items():
            with patch("time.monotonic", return_value=at):
                timer.mark(name)
        with redirect_stdout(io.StringIO()) as buf:
            timer.summary()
        line = buf.getvalue().strip()
        self.assertIn("stop->transcript=100ms", line)
        self.assertIn("transcript->model_request=100ms", line)
        self.assertIn("model_request->first_token=100ms", line)
        self.assertIn("first_token->first_speech_line=50ms", line)
        self.assertIn("first_speech_line->first_tts_byte=150ms", line)
        self.assertIn("first_tts_byte->first_audio_sent=100ms", line)
        self.assertIn("stop->first_audio_sent=600ms", line)
        self.assertIn("total=1000ms", line)

    def test_disabled_by_env_var_suppresses_all_output(self):
        with patch.dict("os.environ", {"NOVA_TIMING_LOGS": "0"}):
            timer = TurnTimer("abc123", start=100.0)
            with redirect_stdout(io.StringIO()) as buf:
                timer.mark("stop_received")
                timer.summary()
        self.assertEqual(buf.getvalue(), "")

    def test_mark_never_raises_even_if_printing_fails(self):
        timer = TurnTimer("abc123")
        with patch("builtins.print", side_effect=RuntimeError("boom")):
            try:
                timer.mark("stop_received")
            except Exception as exc:  # pragma: no cover - test fails via assert below
                self.fail(f"mark() raised: {exc}")

    def test_module_level_mark_helper_is_a_noop_for_none(self):
        # Must not raise, and must not print anything.
        with redirect_stdout(io.StringIO()) as buf:
            mark(None, "stop_received", speculative_ready=True)
        self.assertEqual(buf.getvalue(), "")

    def test_module_level_mark_helper_delegates_to_timer(self):
        timer = TurnTimer("abc123", start=100.0)
        with patch("time.monotonic", return_value=100.1):
            with redirect_stdout(io.StringIO()) as buf:
                mark(timer, "stop_received")
        self.assertIn("[timing] turn=abc123", buf.getvalue())

    def test_usage_mark_prints_like_other_marks(self):
        timer = TurnTimer("abc123", start=100.0)
        with patch("time.monotonic", return_value=100.25):
            with redirect_stdout(io.StringIO()) as buf:
                timer.mark(
                    "usage",
                    round=1,
                    input=412,
                    cache_read=18230,
                    cache_write=0,
                    output=131,
                    cache_hit_pct=98,
                )
        line = buf.getvalue().strip()
        self.assertIn("[timing] turn=abc123", line)
        self.assertIn("t=+250ms", line)
        self.assertIn("usage", line)
        self.assertIn("round=1", line)
        self.assertIn("input=412", line)
        self.assertIn("cache_read=18230", line)
        self.assertIn("cache_write=0", line)
        self.assertIn("output=131", line)
        self.assertIn("cache_hit_pct=98", line)

    def test_summary_includes_round1_cache_fields_from_usage_mark(self):
        timer = TurnTimer("abc123", start=100.0)
        with patch("time.monotonic", return_value=100.3):
            timer.mark(
                "usage",
                round=1,
                input=100,
                cache_read=900,
                cache_write=0,
                output=50,
                cache_hit_pct=90,
            )
        with redirect_stdout(io.StringIO()) as buf:
            timer.summary()
        line = buf.getvalue().strip()
        self.assertIn("cache_read=900", line)
        self.assertIn("cache_write=0", line)
        self.assertIn("cache_hit_pct=90", line)

    def test_summary_cache_fields_are_n_a_when_usage_never_marked(self):
        timer = TurnTimer("abc123", start=100.0)
        with redirect_stdout(io.StringIO()) as buf:
            timer.summary()
        line = buf.getvalue().strip()
        self.assertIn("cache_read=n/a", line)
        self.assertIn("cache_write=n/a", line)
        self.assertIn("cache_hit_pct=n/a", line)

    def test_summary_ignores_usage_marks_from_rounds_after_the_first(self):
        """Only round=1 usage feeds SUMMARY; later rounds must not override."""
        timer = TurnTimer("abc123", start=100.0)
        with patch("time.monotonic", return_value=100.9):
            timer.mark(
                "usage",
                round=2,
                input=10,
                cache_read=990,
                cache_write=0,
                output=5,
                cache_hit_pct=99,
            )
        with redirect_stdout(io.StringIO()) as buf:
            timer.summary()
        line = buf.getvalue().strip()
        self.assertIn("cache_read=n/a", line)
        self.assertIn("cache_write=n/a", line)
        self.assertIn("cache_hit_pct=n/a", line)

    def test_summary_uses_first_round1_usage_mark_only(self):
        timer = TurnTimer("abc123", start=100.0)
        with patch("time.monotonic", return_value=100.3):
            timer.mark(
                "usage",
                round=1,
                input=100,
                cache_read=900,
                cache_write=0,
                output=50,
                cache_hit_pct=90,
            )
        with patch("time.monotonic", return_value=100.9):
            # A later "usage round=1" mark (shouldn't normally happen, but
            # must not clobber the first reading if it does) is ignored.
            timer.mark(
                "usage",
                round=1,
                input=1,
                cache_read=1,
                cache_write=1,
                output=1,
                cache_hit_pct=33,
            )
        with redirect_stdout(io.StringIO()) as buf:
            timer.summary()
        line = buf.getvalue().strip()
        self.assertIn("cache_read=900", line)
        self.assertIn("cache_hit_pct=90", line)


if __name__ == "__main__":
    unittest.main()
