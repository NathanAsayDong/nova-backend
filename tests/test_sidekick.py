"""
Sidekick mode: Nova overhears the conversation around the glasses and decides
on its own when to chime in.

Covers the decision layer (gate parsing, cooldown, be-quiet phrases), the
`[[pass]]` sentinel in the agent loop, the `look` tool's restriction to the
glasses, the direct-turn counter, and the /ws/sidekick socket end to end with
a fake transcriber, gate, agent loop and TTS.
"""

import threading
import time
import unittest
import uuid
import wave
from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from prompting.prompt_source_prompt import SIDEKICK_PASS, PromptSourceEnum
from src.controller import nova_controller, sidekick_controller
from src.harness.agent_loop import AgentLoop, is_sidekick_pass
from src.middleware.auth_gate import AuthGate, is_exempt
from src.model.conversation import Conversation
from src.model.message import MessageRole
from src.service import sidekick_service
from src.service.claude_service import TurnStream
from src.service.sidekick_service import (
    COOLDOWN_SECONDS,
    GateDecision,
    SidekickService,
    SidekickSession,
    has_be_quiet_phrase,
    parse_gate_reply,
)
from src.service.tool_service import ToolService
from src.service.vision_service import VisionService

PCM_MIME = "audio/pcm;rate=16000;channels=1"


# ---------- the decision layer ----------


class GateReplyTests(unittest.TestCase):
    def test_a_strict_yes(self):
        decision = parse_gate_reply('{"speak": true, "why": "wrong capital", "look": false}')
        self.assertEqual(decision, GateDecision(speak=True, why="wrong capital", look=False))

    def test_a_fenced_reply_is_tolerated(self):
        decision = parse_gate_reply('```json\n{"speak": true, "why": "", "look": true}\n```')
        self.assertTrue(decision.speak)
        self.assertTrue(decision.look)

    def test_anything_but_a_real_boolean_is_no(self):
        for reply in (
            '{"speak": "true"}',
            '{"why": "missing speak"}',
            "Yes, I think Nova should speak.",
            "",
            "[true]",
            '{"speak": 1}',
        ):
            with self.subTest(reply=reply):
                self.assertFalse(parse_gate_reply(reply).speak)

    def test_look_defaults_to_false(self):
        self.assertFalse(parse_gate_reply('{"speak": true}').look)

    def test_the_gate_runs_on_its_own_cheap_model(self):
        captured = {}

        class FakeClaude:
            def get_response(self, prompt):
                captured["prompt"] = prompt
                return SimpleNamespace(
                    content=[SimpleNamespace(type="text", text='{"speak": true, "why": "x", "look": false}')]
                )

        gate = sidekick_service.SidekickGate(FakeClaude())
        decision = gate.decide("we're playing chess", 75.0, ["Castle early."])
        self.assertTrue(decision.speak)
        self.assertIn("we're playing chess", captured["prompt"])
        self.assertIn("Castle early.", captured["prompt"])
        self.assertIn("75", captured["prompt"])
        self.assertEqual(sidekick_service.SidekickGate.MODEL, "claude-haiku-5-5")


class SessionTests(unittest.TestCase):
    def test_cooldown_holds_for_sixty_seconds_after_a_remark(self):
        session = SidekickSession(uuid.uuid4(), now=0.0)
        self.assertFalse(session.cooling_down(now=5.0))
        session.note_remark("Take the knight.", now=10.0)
        self.assertTrue(session.cooling_down(now=10.0 + COOLDOWN_SECONDS - 1))
        self.assertFalse(session.cooling_down(now=10.0 + COOLDOWN_SECONDS + 1))

    def test_the_transcript_is_bounded_in_time_and_lines(self):
        session = SidekickSession(uuid.uuid4(), now=0.0)
        session.add("old", now=0.0)
        session.add("new", now=400.0)
        self.assertEqual(session.lines, ["new"])
        for i in range(100):
            session.add(f"line {i}", now=401.0)
        self.assertEqual(len(session.lines), sidekick_service.TRANSCRIPT_MAX_LINES)

    def test_the_gate_reads_only_the_last_two_minutes(self):
        session = SidekickSession(uuid.uuid4(), now=0.0)
        session.add("three minutes ago", now=0.0)
        session.add("just now", now=180.0)
        self.assertEqual(session.recent(now=180.0), "just now")

    def test_wipe_forgets_everything_overheard(self):
        session = SidekickSession(uuid.uuid4())
        session.add("my PIN is 1234")
        session.note_remark("Don't say that out loud.")
        session.wipe()
        self.assertEqual(session.lines, [])
        self.assertEqual(session.remarks, [])

    def test_the_interjection_prompt_asks_for_a_look_when_the_gate_did(self):
        session = SidekickSession(uuid.uuid4())
        session.add("what should I play here")
        prompt = session.interjection_prompt(GateDecision(True, "board position", True))
        self.assertIn("<overheard>\nwhat should I play here\n</overheard>", prompt)
        self.assertIn("Chime in now.", prompt)
        self.assertIn("look tool", prompt)
        self.assertNotIn(
            "look tool", session.interjection_prompt(GateDecision(True, "", False))
        )
        self.assertEqual(
            session.persisted_prompt(), "(Sidekick, overheard) what should I play here"
        )

    def test_session_expires_after_an_hour(self):
        session = SidekickSession(uuid.uuid4(), now=0.0)
        self.assertFalse(session.expired(now=59 * 60))
        self.assertTrue(session.expired(now=60 * 60))


class BeQuietPhraseTests(unittest.TestCase):
    def test_be_quiet_phrases(self):
        for text in (
            "Nova, be quiet.",
            "okay nova be quiet please",
            "Stop sidekick!",
            "Nova shut up",
            "turn off sidekick",
        ):
            with self.subTest(text=text):
                self.assertTrue(has_be_quiet_phrase(text))

    def test_ordinary_talk_is_not_a_stop(self):
        for text in ("be quiet, the baby's asleep", "a supernova be quiet", "quiet please"):
            with self.subTest(text=text):
                self.assertFalse(has_be_quiet_phrase(text))


# ---------- `look` belongs to the glasses ----------


class LookToolExclusionTests(unittest.TestCase):
    def test_look_only_on_the_glasses_and_sidekick(self):
        for source in PromptSourceEnum:
            with self.subTest(source=source.name):
                offered = "look" not in source.excluded_tools()
                self.assertEqual(
                    offered,
                    source
                    in (PromptSourceEnum.GLASSES_PROMPT, PromptSourceEnum.SIDEKICK_PROMPT),
                )

    def test_sidekick_cannot_start_meetings_or_end_the_session(self):
        excluded = PromptSourceEnum.SIDEKICK_PROMPT.excluded_tools()
        self.assertIn("start_meeting", excluded)
        self.assertIn("end_session", excluded)

    def test_sidekick_is_spoken_with_no_screen(self):
        self.assertTrue(PromptSourceEnum.SIDEKICK_PROMPT.wants_spoken_summary())
        self.assertFalse(PromptSourceEnum.SIDEKICK_PROMPT.has_screen())

    def test_sidekick_prompt_carries_the_one_sided_note_and_the_sentinel(self):
        prompt = str(PromptSourceEnum.SIDEKICK_PROMPT)
        self.assertIn("one-sided", prompt)
        self.assertIn(SIDEKICK_PASS, prompt)
        self.assertIn("<in_view>", prompt)

    def test_chat_and_voice_ui_are_never_offered_look(self):
        loop, _ = _agent_loop(tools=["look", "get_time"])
        seen = []

        def fake_stream(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            seen.append(sorted(t["name"] for t in tools or []))
            return TurnStream.completed(FakeMessage([FakeTextBlock("Okay.")]))

        loop.claude_service.stream_response = fake_stream
        for source in (PromptSourceEnum.CHAT_PROMPT, PromptSourceEnum.SPEECH_PROMPT):
            list(loop.conversation_loop_events("hi", uuid.uuid4(), prompt_source=source))
        list(
            loop.conversation_loop_events(
                "hi", uuid.uuid4(), prompt_source=PromptSourceEnum.GLASSES_PROMPT
            )
        )
        self.assertEqual(seen, [["get_time"], ["get_time"], ["get_time", "look"]])


# ---------- the pass sentinel in the agent loop ----------


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeMessage:
    content: list
    stop_reason: str = "end_turn"


@dataclass
class FakeToolUseBlock:
    id: str
    name: str
    input: dict
    type: str = "tool_use"


@dataclass
class FakeConversationService:
    conversations: dict = field(default_factory=dict)
    recorded: list = field(default_factory=list)

    def ensure_open_conversation(self, conversation_uuid):
        return self.conversations.setdefault(
            conversation_uuid, Conversation(id=1, uuid=conversation_uuid)
        )

    def load_history(self, conversation):
        return []

    def record_message(self, conversation, role, content):
        self.recorded.append((role, content))


class FakeToolDao:
    def __init__(self, names):
        self.names = names

    def get_all(self):
        return [
            SimpleNamespace(
                name=name,
                description=name,
                config={"input_schema": {"type": "object", "properties": {}}},
            )
            for name in self.names
        ]


def _agent_loop(tools=()):
    loop = AgentLoop()
    loop.memory_retrieval_enabled = False
    tool_service = ToolService.__new__(ToolService)
    tool_service.tool_dao = FakeToolDao(list(tools))
    loop.tool_service = tool_service
    conversations = FakeConversationService()
    loop.conversation_service = conversations
    loop._load_mcp_servers = lambda: None
    return loop, conversations


def _live(deltas, message):
    """A TurnStream that yields `deltas` as they would stream, then `message`."""

    class SdkStream:
        def __iter__(self):
            return iter([SimpleNamespace(type="text", text=d) for d in deltas])

        def get_final_message(self):
            return message

    class Manager:
        def __enter__(self):
            return SdkStream()

        def __exit__(self, *exc):
            return False

    return TurnStream(open_stream=Manager)


class PassSentinelTests(unittest.TestCase):
    def setUp(self):
        self.loop, self.conversations = _agent_loop(tools=["look"])
        self.conversation_id = uuid.uuid4()

    def _rounds(self, *streams):
        queue = list(streams)
        self.loop.claude_service.stream_response = lambda *a, **k: queue.pop(0)

    def _run(self, prompt="<overheard>\nhmm\n</overheard>\n\nChime in now."):
        return list(
            self.loop.conversation_loop_events(
                prompt,
                self.conversation_id,
                prompt_source=PromptSourceEnum.SIDEKICK_PROMPT,
                persist_prompt_as="(Sidekick, overheard) hmm",
            )
        )

    def test_sentinel_matching(self):
        self.assertTrue(is_sidekick_pass("[[pass]]"))
        self.assertTrue(is_sidekick_pass("  [[PASS]].\n"))
        self.assertFalse(is_sidekick_pass("[[pass]] but actually, castle."))
        self.assertFalse(is_sidekick_pass(""))

    def test_a_pass_is_silent_and_leaves_no_trace(self):
        self._rounds(_live(["[[", "pass", "]]"], FakeMessage([FakeTextBlock("[[pass]]")])))
        events = self._run()
        self.assertEqual(events, [{"type": "silent"}])
        self.assertEqual(self.conversations.recorded, [])
        self.assertEqual(self.loop.conversations[self.conversation_id], [])

    def test_a_pass_after_looking_still_persists_nothing(self):
        self.loop.tool_service.call_tool = lambda tool, args, context=None: "a chessboard"
        self._rounds(
            TurnStream.completed(
                FakeMessage([FakeToolUseBlock("t1", "look", {})], stop_reason="tool_use")
            ),
            _live(["[[pass]]"], FakeMessage([FakeTextBlock("[[pass]]")])),
        )
        events = self._run()
        self.assertEqual(
            [e["type"] for e in events], ["tool_call", "silent"]
        )
        self.assertEqual(self.conversations.recorded, [])
        self.assertEqual(self.loop.conversations[self.conversation_id], [])

    def test_a_remark_streams_and_keeps_only_the_line_that_prompted_it(self):
        remark = "Knight to e5 forks the queen and rook."
        self._rounds(_live(["Kn", "ight to e5 forks the queen and rook."], FakeMessage([FakeTextBlock(remark)])))
        events = self._run()
        spoken = [e["text"] for e in events if e["type"] == "speech_text"]
        self.assertEqual(" ".join(spoken), remark)
        self.assertNotIn({"type": "silent"}, events)
        self.assertEqual(
            self.conversations.recorded,
            [
                (MessageRole.USER, "(Sidekick, overheard) hmm"),
                (MessageRole.NOVA, remark),
            ],
        )
        history = self.loop.conversations[self.conversation_id]
        # The overheard excerpt the model read is not kept, even in memory.
        self.assertEqual(history[0], {"role": "user", "content": "(Sidekick, overheard) hmm"})

    def test_other_media_never_treat_the_sentinel_specially(self):
        self._rounds(TurnStream.completed(FakeMessage([FakeTextBlock("[[pass]]")])))
        events = list(
            self.loop.conversation_loop_events(
                "say [[pass]]", self.conversation_id, prompt_source=PromptSourceEnum.CHAT_PROMPT
            )
        )
        self.assertNotIn({"type": "silent"}, events)
        self.assertEqual(len(self.conversations.recorded), 2)


# ---------- the direct-turn counter on /ws/transcribe ----------


class DirectTurnCounterTests(unittest.TestCase):
    def test_a_voice_turn_counts_as_direct_while_it_runs(self):
        during = []

        class Loop:
            def new_conversation_id(self):
                return uuid.uuid4()

            def conversation_loop_events(self, *args, **kwargs):
                during.append(SidekickService.active_direct_turns)
                yield {"type": "text", "text": "It's noon."}

        def fake_transcribe(file_path, language, fast=False):
            return "What time is it?"

        async def no_tts(*args, **kwargs):
            return True

        app = FastAPI()
        app.include_router(nova_controller.router)
        patches = [
            patch.object(nova_controller, "transcribe_serialized", fake_transcribe),
            patch.object(nova_controller, "agent_loop", Loop()),
            patch.object(nova_controller, "stream_tts_audio", no_tts),
            patch.object(nova_controller.meeting_service, "get_active_meeting", lambda: None),
            patch.object(nova_controller.conversation_service, "get_conversation", lambda _: None),
            patch.object(nova_controller.conversation_service, "pop_stop_request", lambda _: None),
            patch.object(nova_controller, "_speculative_asr_enabled", lambda: False),
            patch.object(nova_controller, "_partial_is_due", lambda *_: False),
        ]
        for p in patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in patches])

        with TestClient(app).websocket_connect("/ws/transcribe") as ws:
            ws.receive_json()
            ws.send_json({"event": "start", "purpose": "turn", "mimeType": PCM_MIME, "client": "glasses"})
            while ws.receive_json()["type"] != "listening":
                pass
            ws.send_bytes(b"\x00\x00" * 800)
            ws.receive_json()
            ws.send_json({"event": "stop", "purpose": "turn"})
            while ws.receive_json()["type"] != "done":
                pass

        self.assertEqual(during, [1])
        self.assertEqual(SidekickService.active_direct_turns, 0)


# ---------- /ws/sidekick ----------


class FakeGate:
    def __init__(self, decision=GateDecision(True, "chess move", False)):
        self.decision = decision
        self.calls: list[tuple[str, float | None]] = []

    def decide(self, transcript, seconds_since_remark, remarks):
        self.calls.append((transcript, seconds_since_remark))
        return self.decision


class FakeSidekickLoop:
    def __init__(self):
        self.calls: list[dict] = []
        self.events = [
            {"type": "speech_text", "text": "Take the knight.", "role": "final"},
            {"type": "text", "text": "Take the knight."},
            {"type": "text_final", "text": "Take the knight."},
        ]
        self.release: threading.Event | None = None

    def new_conversation_id(self):
        return uuid.uuid4()

    def conversation_loop_events(self, prompt, conversation_uuid, prompt_source=None, persist_prompt_as=None, **_):
        self.calls.append(
            {
                "prompt": prompt,
                "conversation": conversation_uuid,
                "source": prompt_source,
                "persist_prompt_as": persist_prompt_as,
                "cameras": dict(VisionService.cameras),
            }
        )
        for index, event in enumerate(self.events):
            if index == 1 and self.release is not None:
                self.release.wait(5)
            yield event


class SidekickSocketTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(sidekick_controller.router)
        self.app = app
        self.gate = FakeGate()
        self.loop = FakeSidekickLoop()
        self.transcripts: dict[bytes, str] = {}
        self.decoded: list[bytes] = []
        self.sessions: list[SidekickSession] = []
        sessions = self.sessions

        class RecordingSession(SidekickSession):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                sessions.append(self)

        def fake_transcribe(pcm):
            self.decoded.append(pcm)
            return self.transcripts.get(pcm, "")

        async def fake_tts(websocket, text, role="final", send_lock=None, previous_text=None, iteration=None):
            async with send_lock:
                await websocket.send_json({"type": "assistant_audio_stream_start", "streamId": "s", "role": role})
                await websocket.send_json({"type": "assistant_audio_stream_end", "streamId": "s"})
            return True

        self.patches = [
            patch.object(sidekick_controller, "transcribe_utterance", fake_transcribe),
            patch.object(sidekick_controller, "gate", self.gate),
            patch.object(sidekick_controller, "SidekickSession", RecordingSession),
            patch.object(nova_controller, "agent_loop", self.loop),
            patch.object(nova_controller, "stream_tts_audio", fake_tts),
            patch.object(nova_controller.conversation_service, "get_conversation", lambda _: None),
            patch.object(sidekick_service, "LULL_SECONDS", 0.05),
        ]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])
        self.addCleanup(setattr, SidekickService, "active_direct_turns", 0)

    def drain(self, ws, until_type, max_messages=40):
        seen = []
        for _ in range(max_messages):
            message = ws.receive_json()
            seen.append(message)
            if message["type"] == until_type:
                return seen
        self.fail(f"never saw {until_type!r}; saw {[m['type'] for m in seen]}")

    def say(self, ws, text: str, pcm: bytes | None = None) -> None:
        pcm = pcm or text.encode("utf-8").ljust(64, b"\x00")[:64]
        self.transcripts[pcm] = text
        ws.send_json({"event": "utterance_start"})
        ws.send_bytes(pcm[:32])
        ws.send_bytes(pcm[32:])
        ws.send_json({"event": "utterance_end"})

    def open(self, client, conversation_id=None):
        ws = client.websocket_connect("/ws/sidekick")
        session = ws.__enter__()
        ready = session.receive_json()
        self.assertEqual(ready["type"], "ready")
        start = {"event": "start"}
        if conversation_id:
            start["conversationId"] = conversation_id
        session.send_json(start)
        started = session.receive_json()
        self.assertEqual(started["type"], "sidekick_started")
        return ws, session, started["conversationId"]

    def test_ping(self):
        with TestClient(self.app).websocket_connect("/ws/sidekick") as ws:
            self.assertEqual(ws.receive_json()["type"], "ready")
            ws.send_json({"event": "ping"})
            self.assertEqual(ws.receive_json(), {"type": "pong"})

    def test_start_keeps_a_given_conversation(self):
        given = str(uuid.uuid4())
        ctx, ws, conversation_id = self.open(TestClient(self.app), given)
        try:
            self.assertEqual(conversation_id, given)
            # The glasses are the session's camera from the start.
            self.assertIn(given, VisionService.cameras)
        finally:
            ctx.__exit__(None, None, None)
        self.assertNotIn(given, VisionService.cameras)

    def test_an_utterance_is_heard_then_gated_then_spoken(self):
        ctx, ws, conversation_id = self.open(TestClient(self.app))
        try:
            self.say(ws, "should I take the knight or the bishop")
            heard = ws.receive_json()
            self.assertEqual(heard, {"type": "heard", "text": "should I take the knight or the bishop"})
            messages = self.drain(ws, "done")
        finally:
            ctx.__exit__(None, None, None)

        types = [m["type"] for m in messages]
        self.assertEqual(
            types,
            ["speech_text", "assistant_audio_stream_start", "assistant_audio_stream_end", "done"],
        )
        self.assertEqual(messages[0]["conversationId"], conversation_id)
        self.assertEqual(messages[-1]["assistantText"], "Take the knight.")
        self.assertEqual(messages[-1]["conversationId"], conversation_id)

        # Raw PCM reached the transcriber whole, frames joined.
        self.assertEqual(len(self.decoded), 1)
        self.assertEqual(len(self.decoded[0]), 64)

        self.assertEqual(len(self.gate.calls), 1)
        self.assertIn("knight or the bishop", self.gate.calls[0][0])
        call = self.loop.calls[0]
        self.assertEqual(call["source"], PromptSourceEnum.SIDEKICK_PROMPT)
        self.assertEqual(str(call["conversation"]), conversation_id)
        self.assertIn("<overheard>", call["prompt"])
        self.assertEqual(
            call["persist_prompt_as"],
            "(Sidekick, overheard) should I take the knight or the bishop",
        )
        self.assertIn(conversation_id, call["cameras"])

    def test_empty_transcripts_are_not_heard(self):
        ctx, ws, _ = self.open(TestClient(self.app))
        try:
            ws.send_json({"event": "utterance_start"})
            ws.send_bytes(b"\x00" * 64)
            ws.send_json({"event": "utterance_end"})
            ws.send_json({"event": "ping"})
            self.assertEqual(ws.receive_json(), {"type": "pong"})
            time.sleep(0.2)
            ws.send_json({"event": "ping"})
            self.assertEqual(ws.receive_json(), {"type": "pong"})
        finally:
            ctx.__exit__(None, None, None)
        self.assertEqual(self.gate.calls, [])

    def test_a_burst_of_utterances_reaches_the_gate_once(self):
        sidekick_service.LULL_SECONDS = 0.4
        ctx, ws, _ = self.open(TestClient(self.app))
        try:
            self.say(ws, "okay your move")
            self.say(ws, "I'm thinking rook")
            self.assertEqual(ws.receive_json()["type"], "heard")
            self.assertEqual(ws.receive_json()["type"], "heard")
            self.drain(ws, "done")
        finally:
            ctx.__exit__(None, None, None)
        self.assertEqual(len(self.gate.calls), 1)
        self.assertEqual(self.gate.calls[0][0], "okay your move\nI'm thinking rook")

    def test_the_gate_is_not_asked_during_the_cooldown(self):
        ctx, ws, _ = self.open(TestClient(self.app))
        try:
            self.say(ws, "first thing")
            self.drain(ws, "done")
            self.say(ws, "second thing")
            self.assertEqual(ws.receive_json()["type"], "heard")
            time.sleep(0.3)
            ws.send_json({"event": "ping"})
            self.assertEqual(ws.receive_json(), {"type": "pong"})
        finally:
            ctx.__exit__(None, None, None)
        self.assertEqual(len(self.gate.calls), 1)

    def test_the_gate_waits_out_a_direct_turn(self):
        SidekickService.begin_direct_turn()
        ctx, ws, _ = self.open(TestClient(self.app))
        try:
            self.say(ws, "hey what's the capital of Australia")
            self.assertEqual(ws.receive_json()["type"], "heard")
            time.sleep(0.4)
            self.assertEqual(self.gate.calls, [])
            SidekickService.end_direct_turn()
            self.drain(ws, "done")
        finally:
            ctx.__exit__(None, None, None)
        self.assertEqual(len(self.gate.calls), 1)

    def test_a_no_from_the_gate_says_nothing(self):
        self.gate.decision = GateDecision(False, "small talk", False)
        ctx, ws, _ = self.open(TestClient(self.app))
        try:
            self.say(ws, "nice weather")
            self.assertEqual(ws.receive_json()["type"], "heard")
            time.sleep(0.3)
            ws.send_json({"event": "ping"})
            self.assertEqual(ws.receive_json(), {"type": "pong"})
        finally:
            ctx.__exit__(None, None, None)
        self.assertEqual(len(self.gate.calls), 1)
        self.assertEqual(self.loop.calls, [])

    def test_a_pass_is_reported_as_silent_instead_of_done(self):
        self.loop.events = [{"type": "silent"}]
        ctx, ws, conversation_id = self.open(TestClient(self.app))
        try:
            self.say(ws, "hmm")
            self.assertEqual(ws.receive_json()["type"], "heard")
            self.assertEqual(ws.receive_json(), {"type": "silent", "conversationId": conversation_id})
            # A pass does not start the cooldown.
            self.assertIsNone(self.sessions[0].last_remark_at)
        finally:
            ctx.__exit__(None, None, None)

    def test_tool_calls_are_relayed(self):
        self.loop.events = [
            {"type": "tool_call", "tool": "look", "input": {}},
            {"type": "speech_text", "text": "Rook to d8.", "role": "final"},
            {"type": "text_final", "text": "Rook to d8."},
        ]
        ctx, ws, conversation_id = self.open(TestClient(self.app))
        try:
            self.say(ws, "what do I play")
            ws.receive_json()
            messages = self.drain(ws, "done")
        finally:
            ctx.__exit__(None, None, None)
        self.assertEqual(
            messages[0], {"type": "tool_call", "tool": "look", "input": {}, "conversationId": conversation_id}
        )

    def test_interrupted_stops_speaking_the_rest(self):
        self.loop.release = threading.Event()
        self.loop.events = [
            {"type": "speech_text", "text": "First,", "role": "status"},
            {"type": "speech_text", "text": "and second.", "role": "final"},
            {"type": "text_final", "text": "First, and second."},
        ]
        ctx, ws, _ = self.open(TestClient(self.app))
        try:
            self.say(ws, "go on")
            ws.receive_json()  # heard
            first = self.drain(ws, "assistant_audio_stream_end")
            self.assertEqual(first[0]["text"], "First,")
            ws.send_json({"event": "interrupted"})
            time.sleep(0.1)
            self.loop.release.set()
            rest = self.drain(ws, "done")
        finally:
            ctx.__exit__(None, None, None)
        self.assertEqual([m["type"] for m in rest], ["done"])
        self.assertEqual(rest[0]["message"], "Interrupted.")

    def test_be_quiet_ends_the_session_and_wipes_the_transcript(self):
        ctx, ws, conversation_id = self.open(TestClient(self.app))
        try:
            self.gate.decision = GateDecision(False, "", False)
            self.say(ws, "this is private")
            self.assertEqual(ws.receive_json()["type"], "heard")
            self.say(ws, "Nova, be quiet.")
            self.assertEqual(ws.receive_json(), {"type": "heard", "text": "Nova, be quiet."})
            self.assertEqual(ws.receive_json(), {"type": "sidekick_ended", "reason": "be_quiet"})
            self.assertEqual(self.sessions[0].lines, [])
            self.assertNotIn(conversation_id, VisionService.cameras)
            # The socket stays usable: utterances need a new start now.
            ws.send_json({"event": "utterance_start"})
            self.assertEqual(ws.receive_json()["type"], "error")
        finally:
            ctx.__exit__(None, None, None)

    def test_stop_ends_the_session(self):
        ctx, ws, _ = self.open(TestClient(self.app))
        try:
            ws.send_json({"event": "stop"})
            self.assertEqual(ws.receive_json(), {"type": "sidekick_ended", "reason": "stopped"})
        finally:
            ctx.__exit__(None, None, None)

    def test_the_session_ends_itself_after_the_cap(self):
        with patch.object(sidekick_service, "SESSION_MAX_SECONDS", 0.2):
            ctx, ws, _ = self.open(TestClient(self.app))
            try:
                self.assertEqual(ws.receive_json(), {"type": "sidekick_ended", "reason": "timeout"})
            finally:
                ctx.__exit__(None, None, None)

    def test_closing_the_socket_wipes_the_transcript(self):
        self.gate.decision = GateDecision(False, "", False)
        ctx, ws, conversation_id = self.open(TestClient(self.app))
        self.say(ws, "something overheard")
        self.assertEqual(ws.receive_json()["type"], "heard")
        self.assertEqual(self.sessions[0].lines, ["something overheard"])
        ctx.__exit__(None, None, None)
        for _ in range(50):
            if not self.sessions[0].lines:
                break
            time.sleep(0.02)
        self.assertEqual(self.sessions[0].lines, [])
        self.assertNotIn(conversation_id, VisionService.cameras)


class SidekickAuthTests(unittest.TestCase):
    def test_the_socket_is_gated(self):
        self.assertFalse(is_exempt("/ws/sidekick"))

        class NoSessions:
            def authenticate(self, token):
                return None

            def configured(self):
                return True

        app = FastAPI()
        app.include_router(sidekick_controller.router)
        app.add_middleware(AuthGate, auth_service=NoSessions())
        with self.assertRaises(WebSocketDisconnect) as refused:
            with TestClient(app).websocket_connect("/ws/sidekick?token=nope") as ws:
                ws.receive_json()
        self.assertEqual(refused.exception.code, 4401)


class TranscribeUtteranceTests(unittest.TestCase):
    def test_pcm_is_wrapped_as_wav_and_transcribed_in_the_background(self):
        seen = {}

        def fake(file_path, language, fast=False, background=False):
            with wave.open(str(file_path)) as wav:
                seen["rate"] = wav.getframerate()
                seen["frames"] = wav.readframes(wav.getnframes())
            seen["background"] = background
            return "  hello  "

        with patch.object(sidekick_controller, "transcribe_serialized", fake):
            text = sidekick_controller.transcribe_utterance(b"\x01\x00" * 100)
        self.assertEqual(text, "hello")
        self.assertEqual(seen, {"rate": 16000, "frames": b"\x01\x00" * 100, "background": True})


if __name__ == "__main__":
    unittest.main()
