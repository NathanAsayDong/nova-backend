"""
Silent mode: per-conversation suppression of live-reply TTS.

Covers the shared setter/getter on ConversationService (used by both the
`set_silent_mode` voice tool and the REST toggle), the REST surface on
conversation_controller, the registration of the voice tool, and the actual
TTS gating inside nova_controller's speak_queued_lines — the live-reply path
must be muted while silent, and a Sidekick 'speak' report must never consult
this flag at all.
"""

import os
import unittest
from unittest import mock
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-key")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC-fake")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "fake-auth-token")
os.environ.setdefault("TWILIO_PHONE_NUMBER", "+15550000000")
os.environ.setdefault("TWILIO_TARGET_NUMBER", "+15551111111")
os.environ.setdefault("PUBLIC_BASE_URL", "https://abc123.ngrok-free.app")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.controller import conversation_controller, nova_controller  # noqa: E402
from src.model.conversation import Conversation  # noqa: E402
from src.service.conversation_service import ConversationService  # noqa: E402


def build_service() -> ConversationService:
    return ConversationService.__new__(ConversationService)


class SilentModeServiceTests(unittest.TestCase):
    """The shared setter/getter both the tool and the REST route call."""

    def setUp(self):
        ConversationService._silent_mode.clear()
        self.addCleanup(ConversationService._silent_mode.clear)

    def test_defaults_to_off(self):
        service = build_service()
        self.assertFalse(service.is_silent(uuid4()))

    def test_round_trips_on_and_off(self):
        service = build_service()
        uuid = uuid4()

        result = service.set_silent_mode(str(uuid), True)

        self.assertEqual(result, {"status": "ok", "silentMode": True})
        self.assertTrue(service.is_silent(uuid))

        service.set_silent_mode(str(uuid), False)
        self.assertFalse(service.is_silent(uuid))

    def test_is_scoped_to_one_conversation(self):
        service = build_service()
        silenced, untouched = uuid4(), uuid4()
        service.set_silent_mode(str(silenced), True)

        self.assertTrue(service.is_silent(silenced))
        self.assertFalse(service.is_silent(untouched))

    def test_visible_across_service_instances(self):
        # The tool layer builds its own ConversationService per call, while
        # the controller and the REST route each hold a different one — the
        # flag has to cross that gap, same as end_session's stop request.
        uuid = uuid4()
        build_service().set_silent_mode(str(uuid), True)

        self.assertTrue(build_service().is_silent(uuid))

    def test_not_a_one_shot_unlike_stop_request(self):
        # Silent mode must keep applying for the rest of the conversation,
        # not just the turn that set it — reading it must not clear it.
        service = build_service()
        uuid = uuid4()
        service.set_silent_mode(str(uuid), True)

        self.assertTrue(service.is_silent(uuid))
        self.assertTrue(service.is_silent(uuid))


class ToolRegistrationTests(unittest.TestCase):
    """set_silent_mode is registered the same way as the other project tools."""

    def test_registered_with_a_required_boolean_and_injected_conversation_uuid(self):
        from scripts.register_project_tools import PROJECT_TOOLS

        definitions = {d["name"]: d for d in PROJECT_TOOLS}
        self.assertIn("set_silent_mode", definitions)

        config = definitions["set_silent_mode"]["config"]
        self.assertEqual(config["type"], "service_method")
        self.assertEqual(
            config["callable_path"],
            "src.service.conversation_service.ConversationService.set_silent_mode",
        )
        self.assertEqual(config["context_kwargs"], ["conversation_uuid"])

        schema = config["input_schema"]
        self.assertEqual(schema["properties"]["enabled"]["type"], "boolean")
        self.assertEqual(schema["required"], ["enabled"])
        self.assertFalse(schema["additionalProperties"])


class ConversationControllerSilentModeTests(unittest.TestCase):
    """The REST path the web/iOS toggle calls."""

    def setUp(self):
        ConversationService._silent_mode.clear()
        self.addCleanup(ConversationService._silent_mode.clear)

        app = FastAPI()
        app.include_router(conversation_controller.router)
        self.client = TestClient(app)
        self.conversation_uuid = uuid4()
        self.conversation = Conversation(uuid=self.conversation_uuid)

        patcher = patch.object(
            conversation_controller.conversation_service,
            "get_conversation",
            lambda _uuid: self.conversation,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_get_conversation_reports_silent_mode(self):
        response = self.client.get(f"/conversations/{self.conversation_uuid}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["silentMode"], False)

        ConversationService._silent_mode[self.conversation_uuid] = True
        response = self.client.get(f"/conversations/{self.conversation_uuid}")
        self.assertEqual(response.json()["silentMode"], True)

    def test_post_turns_it_on_through_the_shared_setter(self):
        response = self.client.post(
            f"/conversations/{self.conversation_uuid}/silent-mode",
            json={"enabled": True},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"conversationId": str(self.conversation_uuid), "silentMode": True},
        )
        self.assertTrue(
            conversation_controller.conversation_service.is_silent(self.conversation_uuid)
        )

    def test_post_turns_it_off(self):
        ConversationService._silent_mode[self.conversation_uuid] = True

        response = self.client.post(
            f"/conversations/{self.conversation_uuid}/silent-mode",
            json={"enabled": False},
        )
        self.assertEqual(response.json()["silentMode"], False)
        self.assertFalse(
            conversation_controller.conversation_service.is_silent(self.conversation_uuid)
        )

    def test_non_boolean_enabled_is_rejected(self):
        response = self.client.post(
            f"/conversations/{self.conversation_uuid}/silent-mode",
            json={"enabled": "yes"},
        )
        self.assertEqual(response.status_code, 400)

    def test_unknown_conversation_is_404(self):
        with patch.object(
            conversation_controller.conversation_service, "get_conversation", lambda _uuid: None
        ):
            response = self.client.post(
                f"/conversations/{uuid4()}/silent-mode", json={"enabled": True}
            )
        self.assertEqual(response.status_code, 404)


class FakeAgentLoop:
    """Answers every turn with one spoken sentence (a speech_text event)."""

    def __init__(self, lines: list[str]):
        self.lines = lines

    def new_conversation_id(self):
        return uuid4()

    def conversation_loop_events(
        self,
        prompt,
        conversation_uuid,
        prompt_source=None,
        conversation=None,
        images=None,
        timer=None,
    ):
        for line in self.lines:
            yield {"type": "speech_text", "text": line, "role": "final"}
        yield {"type": "text_final", "text": " ".join(self.lines)}


class SpeakQueuedLinesGatingTests(unittest.TestCase):
    """
    The one call site that must respect silent mode: speak_queued_lines in
    nova_controller, which feeds queued speech_text lines to stream_tts_audio.
    speech_text is still sent to the client as text either way — only the
    TTS call is gated.
    """

    def setUp(self):
        ConversationService._silent_mode.clear()
        self.addCleanup(ConversationService._silent_mode.clear)

        app = FastAPI()
        app.include_router(nova_controller.router)
        self.app = app
        self.spoken: list[str] = []

        async def fake_stream_tts_audio(
            websocket, text, role="final", send_lock=None, previous_text=None, timer=None
        ):
            self.spoken.append(text)
            return True

        self.agent = FakeAgentLoop(["Here is your answer."])
        self.patches = [
            patch.object(nova_controller, "transcribe_serialized", lambda *a, **k: "hello"),
            patch.object(nova_controller, "agent_loop", self.agent),
            patch.object(nova_controller, "stream_tts_audio", fake_stream_tts_audio),
            patch.object(nova_controller.meeting_service, "get_active_meeting", lambda: None),
            patch.object(nova_controller.conversation_service, "get_conversation", lambda _: None),
            patch.object(nova_controller.conversation_service, "pop_stop_request", lambda _: None),
        ]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])

    def _run_turn(self):
        with TestClient(self.app).websocket_connect("/ws/transcribe") as ws:
            ws.receive_json()  # ready
            ws.send_json({"event": "start", "purpose": "turn", "mimeType": "audio/webm"})
            ws.receive_json()  # listening
            ws.send_bytes(b"a" * 1000)
            ws.receive_json()  # chunk_received
            ws.send_json({"event": "stop", "purpose": "turn"})
            messages = []
            for _ in range(80):
                message = ws.receive_json()
                messages.append(message)
                if message["type"] == "done":
                    break
            return messages

    def test_speaks_normally_when_not_silent(self):
        messages = self._run_turn()

        self.assertEqual(self.spoken, ["Here is your answer."])
        speech_texts = [m["text"] for m in messages if m["type"] == "speech_text"]
        self.assertEqual(speech_texts, ["Here is your answer."])

    def test_mutes_tts_but_still_sends_text_when_silent(self):
        conversation_id = self.agent.new_conversation_id()
        # Pin the agent to a known conversation id so the test can silence it
        # ahead of the turn, the same way a prior tool call would have.
        with patch.object(self.agent, "new_conversation_id", lambda: conversation_id):
            ConversationService._silent_mode[conversation_id] = True
            messages = self._run_turn()

        self.assertEqual(self.spoken, [])
        speech_texts = [m["text"] for m in messages if m["type"] == "speech_text"]
        self.assertEqual(speech_texts, ["Here is your answer."])
        done = [m for m in messages if m["type"] == "done"][0]
        self.assertEqual(done["assistantText"], "Here is your answer.")


class TTSProviderNeverCalledWhenSilentTests(unittest.TestCase):
    """
    Silent mode must skip synthesis entirely, not synthesize audio and throw
    it away: no call to the TTS provider (ElevenLabs/Cartesia/OpenAI, behind
    TTSService.stream_text_to_speech) at all while silent, since that would
    burn API credits and latency for audio nobody hears. Unlike
    SpeakQueuedLinesGatingTests, this does NOT stub out stream_tts_audio —
    it runs the real function and mocks only the provider-facing call one
    level down, so the assertion holds even if stream_tts_audio itself is
    refactored, as long as the gate in speak_queued_lines still runs before
    stream_tts_audio is ever invoked.
    """

    def setUp(self):
        ConversationService._silent_mode.clear()
        self.addCleanup(ConversationService._silent_mode.clear)

        app = FastAPI()
        app.include_router(nova_controller.router)
        self.app = app

        def fake_stream_text_to_speech(text, chunk_size=4096, previous_text=None, timer=None):
            yield b"fake-audio-bytes"

        self.synthesize = mock.Mock(side_effect=fake_stream_text_to_speech)
        self.agent = FakeAgentLoop(["Here is your answer."])
        self.patches = [
            patch.object(nova_controller, "transcribe_serialized", lambda *a, **k: "hello"),
            patch.object(nova_controller, "agent_loop", self.agent),
            patch.object(nova_controller.tts_service, "stream_text_to_speech", self.synthesize),
            patch.object(nova_controller.meeting_service, "get_active_meeting", lambda: None),
            patch.object(nova_controller.conversation_service, "get_conversation", lambda _: None),
            patch.object(nova_controller.conversation_service, "pop_stop_request", lambda _: None),
        ]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])

    def _run_turn(self):
        with TestClient(self.app).websocket_connect("/ws/transcribe") as ws:
            ws.receive_json()  # ready
            ws.send_json({"event": "start", "purpose": "turn", "mimeType": "audio/webm"})
            ws.receive_json()  # listening
            ws.send_bytes(b"a" * 1000)
            ws.receive_json()  # chunk_received
            ws.send_json({"event": "stop", "purpose": "turn"})
            messages = []
            for _ in range(80):
                message = ws.receive_json()
                messages.append(message)
                if message["type"] == "done":
                    break
            return messages

    def test_provider_is_called_when_not_silent(self):
        # Sanity check: the mock is wired into the real call path, so the
        # negative assertion below actually means something.
        self._run_turn()
        self.synthesize.assert_called_once()

    def test_provider_is_never_called_while_silent(self):
        conversation_id = self.agent.new_conversation_id()
        with patch.object(self.agent, "new_conversation_id", lambda: conversation_id):
            ConversationService._silent_mode[conversation_id] = True
            messages = self._run_turn()

        self.synthesize.assert_not_called()
        # The text reply still goes out — only synthesis is skipped.
        speech_texts = [m["text"] for m in messages if m["type"] == "speech_text"]
        self.assertEqual(speech_texts, ["Here is your answer."])
        # No audio stream frames were sent at all, not even an empty one —
        # the frontend's own "refuse to play while silent" safety net
        # should never have anything to refuse here.
        audio_events = [m["type"] for m in messages if m["type"].startswith("assistant_audio_stream")]
        self.assertEqual(audio_events, [])


if __name__ == "__main__":
    unittest.main()
