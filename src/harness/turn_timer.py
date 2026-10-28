"""
Per-turn latency instrumentation for the voice pipeline.

Created at the `stop` event in `transcribe_socket` and threaded explicitly
through `conversation_loop_events`, `TurnStream`, and the TTS calls, because
the agent loop's generator runs on a worker thread (`iter_in_thread`) and the
TTS pull runs via `asyncio.to_thread` — neither a module global nor a
contextvar reliably follows one turn across those thread handoffs. An
explicit object passed down the call chain does, since it is just an
ordinary argument living in frames that resume on whichever thread happens
to be free.

Logging only. Every mark is a `print()` with a `[timing]` prefix; nothing
here changes behavior, ordering, or timing of the turn itself, and nothing
here ever raises — a bug in a mark call must not cost the user their turn.

Disable with `NOVA_TIMING_LOGS=0`. On by default, so a bare redeploy gets
the timeline with no config.
"""

import logging
import os
import threading
import time
from logging.handlers import RotatingFileHandler
from typing import Any

_FILE_LOGGER_NAME = "nova.turn_timer"


def _default_log_path() -> str:
    # src/harness/turn_timer.py -> repo root is two levels up from src/.
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(repo_root, "logs", "turn_timing.log")


def _build_file_logger() -> "logging.Logger | None":
    # Lazily configured, module-wide RotatingFileHandler so every TurnTimer
    # instance shares one open file handle. Any failure here (bad path,
    # read-only filesystem, etc.) must not block import or turn processing —
    # timing just falls back to console-only output.
    try:
        logger = logging.getLogger(_FILE_LOGGER_NAME)
        if logger.handlers:
            return logger
        log_path = os.getenv("NOVA_TIMING_LOG_FILE") or _default_log_path()
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        handler = RotatingFileHandler(
            log_path, maxBytes=5 * 1024 * 1024, backupCount=3
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        return logger
    except Exception:
        return None


_FILE_LOGGER = _build_file_logger()


def _emit(line: str) -> None:
    """Console + log-file sink for a single `[timing]` line.

    Mirrors the existing `[turn]`-style print() logging in
    nova_controller.py for console output, and additionally writes to
    logs/turn_timing.log (or NOVA_TIMING_LOG_FILE) via RotatingFileHandler.
    Both destinations are best-effort: a failure writing to either one is
    swallowed so it can never break a turn.
    """
    try:
        print(line)
    except Exception:
        pass
    if _FILE_LOGGER is not None:
        try:
            _FILE_LOGGER.info(line)
        except Exception:
            pass

# Stage pairs for the SUMMARY line, in the order they're meant to read: the
# path from "user stopped talking" to "first sound the user hears". A stage
# whose two marks were never both hit in this turn prints "n/a" rather than
# a crash or a nonsense negative number.
_SUMMARY_STAGES = (
    ("stop_received", "transcript_ready", "stop->transcript"),
    ("transcript_ready", "model_request_sent", "transcript->model_request"),
    ("model_request_sent", "first_text_delta", "model_request->first_token"),
    ("first_text_delta", "first_speech_line", "first_token->first_speech_line"),
    ("first_speech_line", "first_tts_byte", "first_speech_line->first_tts_byte"),
    ("first_tts_byte", "first_audio_sent", "first_tts_byte->first_audio_sent"),
)


def _timing_enabled() -> bool:
    raw = os.getenv("NOVA_TIMING_LOGS")
    if raw is None:
        return True
    return raw.strip().lower() not in {"false", "0", "no", "off"}


class TurnTimer:
    """
    Marks elapsed time since a voice turn's `stop` event, with a running delta.

    `mark(name, **fields)` prints one `[timing]` line and never raises.
    `summary()` prints one line of stage-to-stage deltas at turn end. Both
    are cheap (a monotonic clock read and a print) and safe to call from
    multiple threads — the event relay and the TTS speaker run concurrently
    on the same turn — behind a small lock.
    """

    def __init__(self, turn_id: str, start: float | None = None) -> None:
        self.turn_id = turn_id
        self._enabled = _timing_enabled()
        self._t0 = start if start is not None else time.monotonic()
        self._last = self._t0
        self._lock = threading.Lock()
        # name -> ms since t0, first occurrence only. A name marked more than
        # once (e.g. "model_request_sent" on round 2) still prints every
        # time, but only its first timing feeds the SUMMARY stages below.
        self._marks: dict[str, float] = {}
        # Prompt-cache fields off the round-1 "usage" mark, captured so
        # SUMMARY can report them without re-deriving anything. None until
        # (and unless) a round=1 usage mark arrives.
        self._round1_usage: dict[str, Any] | None = None

    def mark(self, mark_name: str, **fields: Any) -> None:
        # The positional parameter is `mark_name`, not `name` — several call
        # sites log a `name=` field (tool name, TTS provider name), and that
        # would collide with a parameter literally called `name`.
        if not self._enabled:
            return
        try:
            with self._lock:
                now = time.monotonic()
                elapsed_ms = (now - self._t0) * 1000
                delta_ms = (now - self._last) * 1000
                self._last = now
                self._marks.setdefault(mark_name, elapsed_ms)
                if (
                    mark_name == "usage"
                    and self._round1_usage is None
                    and fields.get("round") == 1
                ):
                    self._round1_usage = {
                        "cache_read": fields.get("cache_read", 0),
                        "cache_write": fields.get("cache_write", 0),
                        "cache_hit_pct": fields.get("cache_hit_pct", "n/a"),
                    }
            line = (
                f"[timing] turn={self.turn_id} t=+{elapsed_ms:.0f}ms "
                f"(+{delta_ms:.0f}ms) {mark_name}"
            )
            if fields:
                line += " " + " ".join(f"{key}={value}" for key, value in fields.items())
            _emit(line)
        except Exception as exc:
            try:
                _emit(f"[timing] turn={self.turn_id} mark {mark_name!r} failed (ignored): {exc}")
            except Exception:
                pass

    def summary(self) -> None:
        if not self._enabled:
            return
        try:
            with self._lock:
                marks = dict(self._marks)
                round1_usage = self._round1_usage
            parts = []
            for start_name, end_name, label in _SUMMARY_STAGES:
                start_ms = marks.get(start_name)
                end_ms = marks.get(end_name)
                if start_ms is None or end_ms is None:
                    parts.append(f"{label}=n/a")
                else:
                    parts.append(f"{label}={end_ms - start_ms:.0f}ms")

            stop_ms = marks.get("stop_received", 0.0)
            first_audio_ms = marks.get("first_audio_sent")
            stop_to_audio = (
                f"{first_audio_ms - stop_ms:.0f}ms" if first_audio_ms is not None else "n/a"
            )
            done_ms = marks.get("done")
            total = f"{done_ms - stop_ms:.0f}ms" if done_ms is not None else "n/a"

            if round1_usage is None:
                cache_read = cache_write = cache_hit_pct = "n/a"
            else:
                cache_read = round1_usage["cache_read"]
                cache_write = round1_usage["cache_write"]
                cache_hit_pct = round1_usage["cache_hit_pct"]

            line = (
                f"[timing] turn={self.turn_id} SUMMARY "
                + " ".join(parts)
                + f" stop->first_audio_sent={stop_to_audio} total={total}"
                + f" cache_read={cache_read} cache_write={cache_write}"
                + f" cache_hit_pct={cache_hit_pct}"
            )
            _emit(line)
        except Exception as exc:
            try:
                _emit(f"[timing] turn={self.turn_id} summary failed (ignored): {exc}")
            except Exception:
                pass


def mark(timer: "TurnTimer | None", mark_name: str, **fields: Any) -> None:
    """`timer.mark(mark_name, **fields)`, or a no-op when `timer` is None."""
    if timer is not None:
        timer.mark(mark_name, **fields)
