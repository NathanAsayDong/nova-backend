"""
Sidekick mode: Nova overhears the conversation around the glasses and decides
on its own when to chime in.

The phone streams every utterance that was not addressed to Nova to
/ws/sidekick (src/controller/sidekick_controller.py). This module is the
decision layer behind that socket:

  SidekickSession   the rolling transcript of what was overheard, in memory
                    only, plus when Nova last spoke up. Nothing here is ever
                    written to the database; the controller wipes it when the
                    session ends. Only the interjection turns themselves are
                    persisted, by the agent loop, as Nova's remark and the
                    line that prompted it.
  SidekickGate      a cheap model that reads the last couple of minutes and
                    answers one question: is there something worth saying?
                    Strict JSON, and anything else counts as "no".
  SidekickService   the class-level count of direct /ws/transcribe turns in
                    progress, so the sidekick never starts talking while the
                    user is talking to Nova on purpose.

The timing rules — wait for a lull, respect the cooldown, defer to direct
turns — are enforced by the controller using the helpers here.
"""

from __future__ import annotations

import asyncio
import json
import re
import threading
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator
from uuid import UUID

# How long the room has to be quiet after the last utterance before the gate
# is asked. Long enough that Nova does not cut into a pause mid-thought.
LULL_SECONDS = 1.5
# Balanced chattiness: at most one unprompted remark this often.
COOLDOWN_SECONDS = 30.0
# A remark that asked a question suspends the cooldown for this long, so the
# gate can act on the answer right away instead of waiting out COOLDOWN_SECONDS.
EXPECTS_REPLY_OVERRIDE_SECONDS = 5.0
# Server-side backstop for the phone's own auto-off.
SESSION_MAX_SECONDS = 60 * 60

# What the session keeps, whichever limit is hit first.
TRANSCRIPT_WINDOW_SECONDS = 5 * 60
TRANSCRIPT_MAX_LINES = 60
# What the gate and the interjection read: the recent past only.
GATE_WINDOW_SECONDS = 2 * 60
# Remarks the gate is shown so it does not suggest the same thing twice.
REMARKS_KEPT = 5

# How often an idle Sidekick connection checks for finished background work
# (background agent / coding task / scheduled task completions) to announce
# right away, instead of waiting for Nate's next turn. Short, because the
# point is for the announcement to feel immediate; cheap, because it is one
# already-indexed unviewed-updates read (see update_pending_notification_idx
# in scripts/migrations/010_update_notification_fields.sql).
COMPLETION_POLL_SECONDS = 5.0

# How long speak_completion waits for the live connection's event loop to
# actually speak before giving up and letting the caller treat it as
# unreachable (deferred, not failed — see UpdateDeliveryService._deliver_speak).
COMPLETION_SPEECH_TIMEOUT_SECONDS = 8.0

GATE_MODEL = "claude-haiku-5-5"

GATE_PROMPT = """You decide whether Nova, a voice assistant the user wears on smart glasses, \
should speak up unprompted. Nova is quietly overhearing the conversation around the user; \
nobody addressed it.

Nova is meant to be an engaged sidekick, not a silent recorder. Say speak=true when a short \
remark would help or add something right now, for example:
- the user wonders aloud or asks a question of anyone ("I wonder…", "what was…", "how do \
I…", "where's…"), even if it was not aimed at Nova,
- the user is planning, deciding, comparing, or choosing something (what to eat, buy, do, \
say, where to go) and Nova has a useful suggestion,
- the user is working through a task or problem (work, code, cooking, fixing, shopping, \
money, travel, a game) and Nova knows a tip, a next step, or a shortcut,
- something said is wrong, or there is a relevant fact, number, or detail Nova knows,
- a timely reminder or heads-up,
- a natural opening for encouragement or a quick dry joke when the mood is light.
Say speak=false for idle small talk with nothing to add, private or emotional matters, an \
argument, mid-flow moments where a remark would interrupt, or anything Nova already \
remarked on. When it is a close call and the user is engaged in something Nova could help \
with, lean toward speak=true.

The transcript is mostly one-sided: the glasses isolate the wearer's voice, so other people \
are faint or missing. Set look=true when seeing the situation (a board, cards, a screen, a \
menu) would materially change the advice.

Seconds since Nova last spoke up: {since}
Nova's recent remarks:
{remarks}

<overheard>
{transcript}
</overheard>

Reply with one JSON object and nothing else:
{{"speak": true or false, "why": "a few words", "look": true or false}}"""

# Said in the ambient transcript, these end the session. Matched on
# normalised words, so "Nova, be quiet!" and "nova be quiet" are the same.
_BE_QUIET_PHRASES = (
    "nova be quiet",
    "be quiet nova",
    "nova quiet",
    "quiet nova",
    "nova shut up",
    "shut up nova",
    "nova hush",
    "hush nova",
    "nova stop sidekick",
    "stop sidekick",
    "sidekick off",
    "turn off sidekick",
    "end sidekick",
    "nova stop listening",
)


def _normalize(text: str) -> str:
    words = re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).split()
    return " ".join(words)


def has_be_quiet_phrase(text: str) -> bool:
    """Whether an overheard line asks Sidekick to stop."""
    padded = f" {_normalize(text)} "
    return any(f" {phrase} " in padded for phrase in _BE_QUIET_PHRASES)


@dataclass(frozen=True)
class GateDecision:
    speak: bool
    why: str = ""
    look: bool = False


_NO = GateDecision(speak=False, why="unreadable gate reply")


def parse_gate_reply(text: str) -> GateDecision:
    """
    The gate's verdict, strictly.

    The reply must be one JSON object (a ```json fence is tolerated) whose
    `speak` is a real boolean. Anything else — prose, a string "true", a
    missing key — is a no: a confused gate must never make Nova talk.
    """
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    try:
        parsed = json.loads(cleaned)
    except (TypeError, ValueError):
        return _NO
    if not isinstance(parsed, dict) or not isinstance(parsed.get("speak"), bool):
        return _NO
    why = parsed.get("why")
    look = parsed.get("look")
    return GateDecision(
        speak=parsed["speak"],
        why=why.strip() if isinstance(why, str) else "",
        look=look is True,
    )


class SidekickGate:
    """The cheap model that decides whether to interject."""

    MODEL = GATE_MODEL

    def __init__(self, claude_service: Any = None) -> None:
        self._claude_service = claude_service

    def _claude(self):
        if self._claude_service is None:
            from src.service.claude_service import ClaudeService

            service = ClaudeService()
            # Its own instance, so the main loop's model is untouched.
            service.MODEL = self.MODEL
            # A yes/no question needs no searching.
            service.web_search_enabled = False
            self._claude_service = service
        return self._claude_service

    def decide(
        self, transcript: str, seconds_since_remark: float | None, remarks: list[str]
    ) -> GateDecision:
        since = "never" if seconds_since_remark is None else f"{seconds_since_remark:.0f}"
        prompt = GATE_PROMPT.format(
            since=since,
            remarks="\n".join(f"- {r}" for r in remarks) or "(none)",
            transcript=transcript,
        )
        response = self._claude().get_response(prompt)
        reply = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        return parse_gate_reply(reply)


class SidekickSession:
    """
    One Sidekick session's memory: what was overheard and what Nova said.

    In memory only. `wipe` is called when the session ends, however it ends.
    """

    def __init__(self, conversation_uuid: UUID, now: float | None = None) -> None:
        self.conversation_uuid = conversation_uuid
        self.started_at = time.monotonic() if now is None else now
        self.last_remark_at: float | None = None
        # Set by `note_remark` when the last remark asked a question; while
        # now is before this, `cooling_down` ignores COOLDOWN_SECONDS.
        self._expects_reply_until: float | None = None
        self._lines: deque[tuple[float, str]] = deque()
        self._remarks: deque[str] = deque(maxlen=REMARKS_KEPT)

    @property
    def lines(self) -> list[str]:
        return [text for _, text in self._lines]

    def add(self, text: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self._lines.append((now, text.strip()))
        self._prune(now)

    def _prune(self, now: float) -> None:
        while self._lines and (
            len(self._lines) > TRANSCRIPT_MAX_LINES
            or now - self._lines[0][0] > TRANSCRIPT_WINDOW_SECONDS
        ):
            self._lines.popleft()

    def recent(self, now: float | None = None, window: float = GATE_WINDOW_SECONDS) -> str:
        """The last `window` seconds, one line per utterance."""
        now = time.monotonic() if now is None else now
        self._prune(now)
        return "\n".join(text for at, text in self._lines if now - at <= window)

    def last_line(self) -> str:
        return self._lines[-1][1] if self._lines else ""

    def seconds_since_remark(self, now: float | None = None) -> float | None:
        if self.last_remark_at is None:
            return None
        now = time.monotonic() if now is None else now
        return now - self.last_remark_at

    def cooling_down(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        if self._expects_reply_until is not None and now < self._expects_reply_until:
            return False
        since = self.seconds_since_remark(now)
        return since is not None and since < COOLDOWN_SECONDS

    def note_remark(
        self, text: str, now: float | None = None, *, expects_reply: bool = False
    ) -> None:
        now = time.monotonic() if now is None else now
        self.last_remark_at = now
        self._expects_reply_until = (
            now + EXPECTS_REPLY_OVERRIDE_SECONDS if expects_reply else None
        )
        if text.strip():
            self._remarks.append(text.strip())

    @property
    def remarks(self) -> list[str]:
        return list(self._remarks)

    def expired(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        return now - self.started_at >= SESSION_MAX_SECONDS

    def wipe(self) -> None:
        self._lines.clear()
        self._remarks.clear()

    def interjection_prompt(self, decision: GateDecision, now: float | None = None) -> str:
        """What the interjection turn is asked, under SIDEKICK_PROMPT."""
        parts = [f"<overheard>\n{self.recent(now)}\n</overheard>", "Chime in now."]
        if decision.why:
            parts.append(f"(Why now: {decision.why}.)")
        if decision.look:
            parts.append(
                "Seeing the situation would help: call the look tool before you answer."
            )
        return "\n\n".join(parts)

    def persisted_prompt(self) -> str:
        """What the transcript keeps of an interjection's prompt: one line."""
        return f"(Sidekick, overheard) {self.last_line()}"


class SidekickService:
    """Process-wide sidekick state shared with the voice socket."""

    # Direct /ws/transcribe turns in progress. While any is, the gate waits:
    # Nova never volunteers a remark over an answer the user asked for.
    active_direct_turns: int = 0
    _lock = threading.Lock()

    # The live /ws/sidekick connections in this process (see
    # SidekickConnection in src/controller/sidekick_controller.py, which
    # registers itself here on `start` and unregisters on `end`). Same
    # pattern as VisionService.register_camera: a connection that owns a
    # live websocket hands this process-wide registry a way to reach it,
    # rather than this module importing the controller (which would be a
    # cycle) or trying to hold the websocket itself.
    _connections: list[Any] = []
    # The API process's event loop, bound once at startup (see main.py's
    # lifespan, same as CodingService.bind_loop / VisionService.bind_loop).
    # UpdateDeliveryService.deliver_pending runs on a schedule that may be a
    # different OS process (worker.py) with no such loop bound at all — in
    # that case `loop` stays None and speak_completion below simply reports
    # "nothing to speak through", which is the correct, honest answer from
    # that process.
    loop: Any = None

    @classmethod
    def begin_direct_turn(cls) -> None:
        with cls._lock:
            cls.active_direct_turns += 1

    @classmethod
    def end_direct_turn(cls) -> None:
        with cls._lock:
            cls.active_direct_turns = max(0, cls.active_direct_turns - 1)

    @classmethod
    @contextmanager
    def direct_turn(cls) -> Iterator[None]:
        cls.begin_direct_turn()
        try:
            yield
        finally:
            cls.end_direct_turn()

    @classmethod
    def direct_turn_active(cls) -> bool:
        with cls._lock:
            return cls.active_direct_turns > 0

    @classmethod
    def bind_loop(cls, loop: Any) -> None:
        """Attach this process's event loop, so speak_completion can schedule onto it."""
        cls.loop = loop

    @classmethod
    def register_connection(cls, connection: Any) -> None:
        """A /ws/sidekick session just started: it can now be spoken through."""
        with cls._lock:
            if connection not in cls._connections:
                cls._connections.append(connection)

    @classmethod
    def unregister_connection(cls, connection: Any) -> None:
        with cls._lock:
            if connection in cls._connections:
                cls._connections.remove(connection)

    @classmethod
    def _idle_connection(cls) -> Any | None:
        """
        A live sidekick connection free to speak right now, or None.

        "Sidekick on" is simply a connection with a session (the app has an
        active /ws/sidekick session); "idle" is that session not currently
        mid-interjection and no direct /ws/transcribe turn in progress
        anywhere in the process — exactly the gate `_gate_after_lull` already
        gives ambient remarks, reused rather than re-derived here.
        """
        if cls.active_direct_turns > 0:
            return None
        with cls._lock:
            candidates = list(cls._connections)
        for connection in candidates:
            try:
                if connection.is_idle():
                    return connection
            except Exception:
                continue
        return None

    @classmethod
    def speak_completion(
        cls, text: str, timeout: float = COMPLETION_SPEECH_TIMEOUT_SECONDS
    ) -> bool:
        """
        Speak a finished-work report through a live, idle sidekick session,
        bypassing the ordinary ambient-remark cooldown — a completion
        announcement is not the chatty, rate-limited kind of remark
        COOLDOWN_SECONDS exists to throttle, and holding it back 30 seconds
        would make a "the agent is done" report arrive stale.

        Returns whether it was actually spoken. False covers every reason it
        couldn't be (sidekick off, mid-conversation, no loop bound in this
        process, the speech itself failing) uniformly, on purpose: the
        caller's job either way is the same — leave the update for the
        existing next-turn injection or a later delivery pass, never raise.
        """
        text = (text or "").strip()
        if not text:
            return False
        connection = cls._idle_connection()
        if connection is None or cls.loop is None:
            return False
        try:
            future = asyncio.run_coroutine_threadsafe(
                connection.speak_now(text, bypass_cooldown=True), cls.loop
            )
            return bool(future.result(timeout=timeout))
        except Exception as exc:
            print(f"[sidekick] speak_completion failed: {exc}")
            return False
