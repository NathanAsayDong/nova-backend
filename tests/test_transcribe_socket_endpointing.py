"""
Integration coverage for the turn-detection half of /ws/transcribe.

Exercises the socket the way the browser drives it — start, chunks,
speech_pause, stop — with the ASR, TTS, and agent loop stubbed out, so the
assertions are about the endpointing protocol rather than about Whisper.
"""

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.controller import nova_controller
from src.service.endpointing_service import (
    DEFAULT_SILENCE_MS,
    MAX_SILENCE_MS,
    MIN_SILENCE_MS,
    STATEMENT_SILENCE_MS,
)


class FakeAgentLoop:
    """Answers every turn with one sentence and no tools."""

    def __init__(self):
        self.prompts: list[str] = []

    def new_conversation_id(self):
        import uuid

        return uuid.uuid4()

    def conversation_loop_events(self, prompt, conversation_uuid, prompt_source=None):
        self.prompts.append(prompt)
        yield {"type": "text", "text": "Understood."}


class TranscribeSocketTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(nova_controller.router)
        self.app = app

        # The fake ASR is content-addressed: what it returns depends on the
        # audio it was actually handed, not on call order. Tests send chunks of
        # distinct filler bytes ("aaa...", then "bbb..."), so the marker for a
        # buffer is the letters in it -- "a" for the audio present at the pause,
        # "ab" once a second chunk has arrived. A test can therefore assert
        # *which* audio the transcript came from, which is the whole question
        # when a transcription starts before the recording has finished.
        # A marker may map to a list instead of a string, for the cases where
        # the same audio is transcribed twice and the two results differ.
        self.asr_calls: list[str] = []
        self.transcripts: dict[str, str | list[str]] = {}

        def fake_transcribe(file_path, language):
            marker = "".join(sorted(set(file_path.read_bytes().decode())))
            self.asr_calls.append(marker)
            reply = self.transcripts.get(marker, f"audio[{marker}]")
            if isinstance(reply, list):
                return reply.pop(0) if reply else f"audio[{marker}]"
            return reply

        self.agent = FakeAgentLoop()

        self.patches = [
            patch.object(nova_controller, "transcribe_serialized", fake_transcribe),
            patch.object(nova_controller, "agent_loop", self.agent),
            # TTS and the meeting check are unrelated round trips here.
            patch.object(
                nova_controller, "stream_tts_audio", self._no_tts
            ),
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
        ]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])

    @staticmethod
    async def _no_tts(websocket, text, role="final"):
        return True

    # ---------- helpers ----------

    def drain(self, ws, until_type, max_messages=80):
        """Read messages until one of `until_type` arrives; return them all."""
        seen = []
        for _ in range(max_messages):
            message = ws.receive_json()
            seen.append(message)
            if message["type"] == until_type:
                return seen
        self.fail(f"never saw {until_type!r}; saw {[m['type'] for m in seen]}")

    def start_turn(self, ws):
        ws.receive_json()  # ready
        ws.send_json({"event": "start", "purpose": "turn", "mimeType": "audio/webm"})
        return self.drain(ws, "listening")[-1]

    # ---------- tests ----------

    def test_listening_carries_the_starting_silence_window(self):
        with TestClient(self.app).websocket_connect("/ws/transcribe") as ws:
            listening = self.start_turn(ws)
            self.assertEqual(listening["endpointMs"], DEFAULT_SILENCE_MS)

    def test_captions_carry_the_window_for_what_was_said(self):
        # A finished sentence should shorten the wait; a dangling function word
        # should lengthen it. Two captions over growing audio, two windows.
        self.transcripts = {
            "ab": "Send that to",
            "abcd": "Send that to Sophie.",
        }
        with TestClient(self.app).websocket_connect("/ws/transcribe") as ws:
            self.start_turn(ws)
            windows = []
            for pair in ((b"a", b"b"), (b"c", b"d")):
                for filler in pair:
                    ws.send_bytes(filler * 400)
                for message in self.drain(ws, "partial_transcript"):
                    if message["type"] == "partial_transcript":
                        windows.append((message["text"], message["endpointMs"]))

        self.assertEqual(windows[0], ("Send that to", MAX_SILENCE_MS))
        self.assertEqual(windows[1], ("Send that to Sophie.", STATEMENT_SILENCE_MS))

    def test_pause_transcribes_before_stop_is_sent(self):
        # The point of the whole exercise: by the time the client says stop,
        # the turn has already been transcribed. Speculation starts on the
        # chunk AFTER the pause — the flush that carries the words spoken
        # since the last cadence chunk — never on the buffer as it stood when
        # the pause arrived, which is missing the user's last words.
        self.transcripts = {"ab": "What is on my calendar?"}
        with TestClient(self.app).websocket_connect("/ws/transcribe") as ws:
            self.start_turn(ws)
            ws.send_bytes(b"a" * 1000)
            ws.receive_json()  # chunk_received

            ws.send_json({"event": "speech_pause"})
            ws.send_bytes(b"b" * 500)  # the client's on-pause flush
            ws.receive_json()  # chunk_received
            # Speculation completes and reports the freshest endpoint hint.
            hint = self.drain(ws, "partial_transcript")[-1]
            self.assertEqual(hint["text"], "What is on my calendar?")
            self.assertEqual(hint["endpointMs"], MIN_SILENCE_MS)

            ws.send_json({"event": "stop", "purpose": "turn"})
            messages = self.drain(ws, "done")

        transcripts = [m for m in messages if m["type"] == "user_transcript"]
        self.assertEqual(transcripts[0]["text"], "What is on my calendar?")
        # Exactly one ASR run for the turn, and over the FULL audio including
        # the post-pause flush. The stop reused it.
        self.assertEqual(self.asr_calls, ["ab"])
        self.assertEqual(self.agent.prompts, ["What is on my calendar?"])

    def test_pause_without_a_flush_falls_back_to_the_full_buffer(self):
        # No chunk ever followed the pause (flush failed, or stop won the
        # race): nothing speculative exists, so stop transcribes everything.
        self.transcripts = {"a": "Just checking."}
        with TestClient(self.app).websocket_connect("/ws/transcribe") as ws:
            self.start_turn(ws)
            ws.send_bytes(b"a" * 1000)
            ws.receive_json()
            ws.send_json({"event": "speech_pause"})
            ws.send_json({"event": "stop", "purpose": "turn"})
            messages = self.drain(ws, "done")

        transcripts = [m for m in messages if m["type"] == "user_transcript"]
        self.assertEqual(transcripts[0]["text"], "Just checking.")
        self.assertEqual(self.asr_calls, ["a"])

    def test_resume_discards_the_speculative_transcript(self):
        # The pause turned out to be mid-sentence, so what was transcribed at
        # the pause covers only part of the turn and must not be used.
        self.transcripts = {
            "ab": "Send that to",
            "abc": "Send that to Sophie tonight.",
        }
        with TestClient(self.app).websocket_connect("/ws/transcribe") as ws:
            self.start_turn(ws)
            ws.send_bytes(b"a" * 1000)
            ws.receive_json()

            ws.send_json({"event": "speech_pause"})
            ws.send_bytes(b"b" * 500)  # on-pause flush; speculation runs on "ab"
            ws.receive_json()
            self.drain(ws, "partial_transcript")  # the speculative hint

            ws.send_json({"event": "speech_resume"})
            ws.send_bytes(b"c" * 1000)
            ws.receive_json()

            ws.send_json({"event": "stop", "purpose": "turn"})
            messages = self.drain(ws, "done")

        transcripts = [m for m in messages if m["type"] == "user_transcript"]
        # The full buffer, not the half that existed when the pause fired.
        self.assertEqual(transcripts[0]["text"], "Send that to Sophie tonight.")
        self.assertEqual(self.asr_calls[-1], "abc")

    def test_a_turn_with_no_pause_still_transcribes_on_stop(self):
        # A client that never sends speech_pause (or has speculation off) must
        # keep working exactly as before.
        self.transcripts = {"a": "Just checking."}
        with TestClient(self.app).websocket_connect("/ws/transcribe") as ws:
            self.start_turn(ws)
            ws.send_bytes(b"a" * 1000)
            ws.receive_json()
            ws.send_json({"event": "stop", "purpose": "turn"})
            messages = self.drain(ws, "done")

        transcripts = [m for m in messages if m["type"] == "user_transcript"]
        self.assertEqual(transcripts[0]["text"], "Just checking.")
        self.assertEqual(self.asr_calls, ["a"])

    def test_an_empty_speculative_result_falls_back_to_the_full_buffer(self):
        # Whisper found nothing at the pause. The tail may have held the only
        # speech, so transcribe the whole buffer rather than trusting silence.
        # Same audio both times: empty on the speculative pass, words on the
        # retry, so the fallback is what produced the transcript.
        self.transcripts = {"ab": ["", "Actually, never mind."]}
        with TestClient(self.app).websocket_connect("/ws/transcribe") as ws:
            self.start_turn(ws)
            ws.send_bytes(b"a" * 1000)
            ws.receive_json()
            ws.send_json({"event": "speech_pause"})
            ws.send_bytes(b"b" * 500)
            ws.receive_json()
            ws.send_json({"event": "stop", "purpose": "turn"})
            messages = self.drain(ws, "done")

        transcripts = [m for m in messages if m["type"] == "user_transcript"]
        self.assertEqual(transcripts[0]["text"], "Actually, never mind.")
        self.assertEqual(self.asr_calls, ["ab", "ab"])

    def test_pause_is_ignored_outside_a_recording(self):
        with TestClient(self.app).websocket_connect("/ws/transcribe") as ws:
            ws.receive_json()  # ready
            ws.send_json({"event": "speech_pause"})
            ws.send_json({"event": "ping"})
            self.assertEqual(ws.receive_json()["type"], "pong")
        self.assertEqual(self.asr_calls, [])

    def test_a_new_recording_discards_the_previous_speculative_result(self):
        self.transcripts = {"a": "Stale.", "c": "Fresh transcript."}
        with TestClient(self.app).websocket_connect("/ws/transcribe") as ws:
            self.start_turn(ws)
            ws.send_bytes(b"a" * 1000)
            ws.receive_json()
            ws.send_json({"event": "speech_pause"})

            # Restart without ever stopping: the browser does this when a turn
            # is abandoned.
            ws.send_json(
                {"event": "start", "purpose": "turn", "mimeType": "audio/webm"}
            )
            self.drain(ws, "listening")
            ws.send_bytes(b"c" * 1000)
            ws.receive_json()
            ws.send_json({"event": "stop", "purpose": "turn"})
            messages = self.drain(ws, "done")

        transcripts = [m for m in messages if m["type"] == "user_transcript"]
        # The restart cleared the buffer, so the second turn is the "b" audio
        # alone — the speculative result from before it must not leak through.
        self.assertEqual(transcripts[0]["text"], "Fresh transcript.")

    def test_abort_discards_the_buffer(self):
        # A click opened a turn; the client aborted it. The noise must not
        # leak into the next real turn's audio.
        self.transcripts = {"b": "Real question."}
        with TestClient(self.app).websocket_connect("/ws/transcribe") as ws:
            self.start_turn(ws)
            ws.send_bytes(b"a" * 500)  # the click
            ws.receive_json()
            ws.send_json({"event": "abort"})

            ws.send_json(
                {"event": "start", "purpose": "turn", "mimeType": "audio/webm"}
            )
            self.drain(ws, "listening")
            ws.send_bytes(b"b" * 1000)
            ws.receive_json()
            ws.send_json({"event": "stop", "purpose": "turn"})
            messages = self.drain(ws, "done")

        transcripts = [m for m in messages if m["type"] == "user_transcript"]
        self.assertEqual(transcripts[0]["text"], "Real question.")
        # Only the real turn was ever transcribed, and without the click audio.
        self.assertEqual(self.asr_calls, ["b"])


if __name__ == "__main__":
    unittest.main()
