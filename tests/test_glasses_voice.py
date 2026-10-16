"""
Coverage for the glasses client on /ws/transcribe.

The iOS app captures raw 16-bit PCM from the glasses' Bluetooth mic and sends
it headerless, and marks its turns `client: "glasses"` so they run under a
prompt written for an ear with no screen.
"""

import io
import unittest
import uuid
import wave
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from prompting.prompt_source_prompt import PromptSourceEnum
from src.controller import nova_controller
from src.controller.audio_ws import audio_file_bytes, is_raw_pcm, suffix_for_mime
from src.harness.agent_loop import AgentLoop
from src.harness.spoken_reply import NO_SCREEN_LINE, SCREEN_ONLY_LINE
from src.service.vision_service import ImageStore, VisionImage, VisionService

PCM_MIME = "audio/pcm;rate=16000;channels=1"


class AudioFileBytesTests(unittest.TestCase):
    def test_container_formats_pass_through(self):
        self.assertEqual(audio_file_bytes("audio/webm;codecs=opus", b"xyz"), b"xyz")
        self.assertEqual(suffix_for_mime("audio/webm"), ".webm")

    def test_pcm_is_recognised_with_or_without_parameters(self):
        self.assertTrue(is_raw_pcm(PCM_MIME))
        self.assertTrue(is_raw_pcm("audio/pcm"))
        self.assertTrue(is_raw_pcm("audio/L16;rate=8000"))
        self.assertFalse(is_raw_pcm("audio/mp4"))
        self.assertEqual(suffix_for_mime(PCM_MIME), ".wav")

    def test_pcm_gets_a_wav_header_sized_to_the_buffer(self):
        pcm = b"\x01\x00" * 1600
        with wave.open(io.BytesIO(audio_file_bytes(PCM_MIME, pcm))) as wav:
            self.assertEqual(wav.getframerate(), 16000)
            self.assertEqual(wav.getnchannels(), 1)
            self.assertEqual(wav.getsampwidth(), 2)
            self.assertEqual(wav.readframes(wav.getnframes()), pcm)

    def test_rate_comes_from_the_mime_parameters(self):
        data = audio_file_bytes("audio/pcm;rate=8000", b"\x00\x00" * 10)
        with wave.open(io.BytesIO(data)) as wav:
            self.assertEqual(wav.getframerate(), 8000)

    def test_a_half_sample_at_the_end_is_dropped(self):
        data = audio_file_bytes(PCM_MIME, b"\x00\x00\x00")
        with wave.open(io.BytesIO(data)) as wav:
            self.assertEqual(wav.getnframes(), 1)


class GlassesPromptSourceTests(unittest.TestCase):
    def test_glasses_turns_are_spoken(self):
        self.assertTrue(PromptSourceEnum.GLASSES_PROMPT.wants_spoken_summary())
        self.assertTrue(PromptSourceEnum.SPEECH_PROMPT.wants_spoken_summary())
        self.assertFalse(PromptSourceEnum.CALL_PROMPT.wants_spoken_summary())

    def test_only_glasses_have_no_screen(self):
        self.assertFalse(PromptSourceEnum.GLASSES_PROMPT.has_screen())
        self.assertTrue(PromptSourceEnum.SPEECH_PROMPT.has_screen())

    def test_an_unsayable_answer_does_not_point_at_a_screen(self):
        table = "| a | b |\n|---|---|\n| 1 | 2 |"
        self.assertEqual(
            AgentLoop._spoken_track(
                PromptSourceEnum.GLASSES_PROMPT, table, required=True
            ),
            NO_SCREEN_LINE,
        )
        self.assertEqual(
            AgentLoop._spoken_track(
                PromptSourceEnum.SPEECH_PROMPT, table, required=True
            ),
            SCREEN_ONLY_LINE,
        )

    def test_client_hint_selects_the_prompt(self):
        self.assertIs(
            nova_controller.voice_prompt_source("glasses"),
            PromptSourceEnum.GLASSES_PROMPT,
        )
        self.assertIs(
            nova_controller.voice_prompt_source(None), PromptSourceEnum.SPEECH_PROMPT
        )
        self.assertIs(
            nova_controller.voice_prompt_source("web"), PromptSourceEnum.SPEECH_PROMPT
        )


class FakeAgentLoop:
    def __init__(self):
        self.prompt_sources: list[PromptSourceEnum] = []
        self.images: list = []
        # Cameras registered while the turn ran, seen from inside it.
        self.cameras_during_turn: list[list[str]] = []

    def new_conversation_id(self):
        return uuid.uuid4()

    def conversation_loop_events(
        self, prompt, conversation_uuid, prompt_source=None, conversation=None, images=None
    ):
        self.prompt_sources.append(prompt_source)
        self.images.append(images)
        self.cameras_during_turn.append(list(VisionService.cameras))
        yield {"type": "text", "text": "Understood."}


class GlassesSocketTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(nova_controller.router)
        self.app = app
        self.agent = FakeAgentLoop()
        self.decoded: list[tuple[str, int, bytes]] = []

        def fake_transcribe(file_path, language, fast=False):
            # Whatever reaches the decoder has to be a file it can open.
            with wave.open(str(file_path)) as wav:
                frames = wav.readframes(wav.getnframes())
                self.decoded.append((file_path.suffix, wav.getframerate(), frames))
            return "What time is it?"

        async def no_tts(websocket, text, role="final", send_lock=None, previous_text=None):
            return True

        self.patches = [
            patch.object(nova_controller, "transcribe_serialized", fake_transcribe),
            patch.object(nova_controller, "agent_loop", self.agent),
            patch.object(nova_controller, "stream_tts_audio", no_tts),
            patch.object(
                nova_controller.meeting_service, "get_active_meeting", lambda: None
            ),
            patch.object(
                nova_controller.conversation_service, "get_conversation", lambda _: None
            ),
            patch.object(
                nova_controller.conversation_service,
                "pop_stop_request",
                lambda _: None,
            ),
            # Speculation and captions would decode the same buffer early; the
            # stop path alone is enough to prove the framing.
            patch.object(nova_controller, "_speculative_asr_enabled", lambda: False),
            patch.object(nova_controller, "_partial_is_due", lambda *_: False),
        ]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])

    def drain(self, ws, until_type, max_messages=80):
        seen = []
        for _ in range(max_messages):
            message = ws.receive_json()
            seen.append(message)
            if message["type"] == until_type:
                return seen
        self.fail(f"never saw {until_type!r}; saw {[m['type'] for m in seen]}")

    def run_turn(self, start: dict, chunks: list[bytes], stop: dict | None = None) -> list[dict]:
        with TestClient(self.app).websocket_connect("/ws/transcribe") as ws:
            ws.receive_json()  # ready
            ws.send_json({"event": "start", "purpose": "turn", **start})
            self.drain(ws, "listening")
            for chunk in chunks:
                ws.send_bytes(chunk)
                ws.receive_json()  # chunk_received
            ws.send_json({"event": "stop", "purpose": "turn", **(stop or {})})
            return self.drain(ws, "done")

    def test_pcm_turn_from_glasses_is_decoded_and_runs_the_glasses_prompt(self):
        # 3201 bytes in two chunks: a sample split across the chunk boundary
        # and a dangling half sample at the end.
        pcm = bytes(range(256)) * 12 + b"\x01" * 129
        messages = self.run_turn(
            {"mimeType": PCM_MIME, "client": "glasses"}, [pcm[:1001], pcm[1001:]]
        )

        transcripts = [m for m in messages if m["type"] == "user_transcript"]
        self.assertEqual(transcripts[0]["text"], "What time is it?")
        suffix, rate, frames = self.decoded[0]
        self.assertEqual((suffix, rate), (".wav", 16000))
        self.assertEqual(frames, pcm[:-1])
        self.assertEqual(self.agent.prompt_sources, [PromptSourceEnum.GLASSES_PROMPT])

    def test_a_turn_without_a_client_hint_keeps_the_voice_ui_prompt(self):
        self.run_turn({"mimeType": PCM_MIME}, [b"\x00\x00" * 800])
        self.assertEqual(self.agent.prompt_sources, [PromptSourceEnum.SPEECH_PROMPT])

    def test_stop_with_image_ids_hands_the_photos_to_the_turn(self):
        saved = VisionService.store
        VisionService.store = ImageStore()
        self.addCleanup(setattr, VisionService, "store", saved)
        VisionService.store.put(
            VisionImage("img-1", b"jpeg", 4, 4, people=[{"name": "Tom", "confidence": 0.7}])
        )
        self.run_turn(
            {"mimeType": PCM_MIME, "client": "glasses"},
            [b"\x00\x00" * 800],
            stop={"imageIds": ["img-1", "expired", 7]},
        )
        images = self.agent.images[0]
        self.assertEqual([b["type"] for b in images], ["image", "text"])
        self.assertIn("Tom", images[-1]["text"])
        self.assertIn("didn't arrive", images[-1]["text"])

    def test_a_turn_without_image_ids_has_no_images(self):
        self.run_turn({"mimeType": PCM_MIME, "client": "glasses"}, [b"\x00\x00" * 800])
        self.assertEqual(self.agent.images, [None])

    def test_glasses_turns_register_their_camera_only_while_running(self):
        self.run_turn({"mimeType": PCM_MIME, "client": "glasses"}, [b"\x00\x00" * 800])
        self.assertEqual(len(self.agent.cameras_during_turn[0]), 1)
        self.assertEqual(VisionService.cameras, {})
        self.run_turn({"mimeType": PCM_MIME}, [b"\x00\x00" * 800])
        self.assertEqual(self.agent.cameras_during_turn[1], [])


if __name__ == "__main__":
    unittest.main()


class GlassesCannotRecordMeetingsTests(unittest.TestCase):
    """A meeting started from the glasses records nothing and locks every
    later voice turn out, so the glasses are never offered start_meeting."""

    def _tools_offered(self, prompt_source):
        from src.model.tool import Tool
        from src.service.tool_service import ToolService
        from src.service.claude_service import TurnStream
        from tests.test_conversation_loop import (
            FakeConversationService,
            FakeMessage,
            FakeTextBlock,
        )

        schema = {"type": "object", "properties": {}}

        class Dao:
            def get_all(self):
                return [
                    Tool(id=1, name="start_meeting", description="", config={"input_schema": schema}),
                    Tool(id=2, name="stop_meeting", description="", config={"input_schema": schema}),
                ]

        agent_loop = AgentLoop()
        agent_loop.memory_retrieval_enabled = False
        tool_service = ToolService.__new__(ToolService)
        tool_service.tool_dao = Dao()
        agent_loop.tool_service = tool_service
        agent_loop.conversation_service = FakeConversationService()
        offered = []

        def fake_stream(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            offered.extend(tool["name"] for tool in tools or [])
            return TurnStream.completed(FakeMessage(content=[FakeTextBlock(text="Okay.")]))

        agent_loop.claude_service.stream_response = fake_stream
        list(agent_loop.conversation_loop_events("take notes on this meeting", uuid.uuid4(), prompt_source=prompt_source))
        return offered

    def test_glasses_are_not_offered_start_meeting(self):
        offered = self._tools_offered(PromptSourceEnum.GLASSES_PROMPT)
        self.assertNotIn("start_meeting", offered)
        self.assertIn("stop_meeting", offered)

    def test_the_web_voice_ui_still_is(self):
        self.assertIn("start_meeting", self._tools_offered(PromptSourceEnum.SPEECH_PROMPT))

    def test_the_glasses_prompt_says_why(self):
        self.assertIn("cannot record", str(PromptSourceEnum.GLASSES_PROMPT))
