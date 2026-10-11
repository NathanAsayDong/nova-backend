"""
Which voice Nova speaks with, and what happens when that voice refuses a line.

ElevenLabs is the default; OpenAI is opt-in and is also the fallback, so a
lapsed ElevenLabs plan degrades the voice instead of silencing it.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from src.service import tts_service
from src.service.eleven_labs_service import ElevenLabsService, _describe_failure

ELEVEN_ENV = {
    "ELEVEN_LABS_API_KEY": "test-eleven-key",
    "ELEVEN_LABS_VOICE_ID": "test-voice",
    "OPENAI_API_KEY": "test-key",
}


def _env(**overrides):
    env = {**ELEVEN_ENV, **overrides}
    env = {k: v for k, v in env.items() if v is not None}
    for key in ("TTS_PROVIDER", "TTS_MODEL", "ELEVEN_LABS_MODEL_ID", "ELEVEN_LABS_API"):
        env.setdefault(key, "")
    return patch.dict(os.environ, env, clear=False)


class ProviderSelectionTests(unittest.TestCase):
    def test_elevenlabs_is_the_default(self):
        with _env():
            service = tts_service.TTSService()
        self.assertEqual(service.provider, "elevenlabs")
        self.assertIsInstance(service.fallback, tts_service.OpenAITTS)

    def test_tts_provider_openai_opts_out(self):
        with _env(TTS_PROVIDER="openai"):
            service = tts_service.TTSService()
        self.assertEqual(service.provider, "openai")
        self.assertIsNone(service.fallback)

    def test_legacy_tts_model_elevenlabs_still_selects_elevenlabs(self):
        with _env(TTS_MODEL="elevenlabs"):
            self.assertEqual(tts_service.TTSService().provider, "elevenlabs")

    def test_legacy_openai_model_name_selects_openai(self):
        with _env(TTS_MODEL="gpt-4o-mini-tts"):
            service = tts_service.TTSService()
        self.assertEqual(service.provider, "openai")
        self.assertEqual(service.primary.model, "gpt-4o-mini-tts")

    def test_missing_elevenlabs_config_falls_back_to_openai(self):
        with _env(ELEVEN_LABS_VOICE_ID=""):
            service = tts_service.TTSService()
        self.assertEqual(service.provider, "openai")

    def test_flash_is_the_default_model_and_overridable(self):
        with _env():
            self.assertEqual(ElevenLabsService().model_id, "eleven_flash_v2_5")
        with _env(ELEVEN_LABS_MODEL_ID="eleven_turbo_v2_5"):
            self.assertEqual(ElevenLabsService().model_id, "eleven_turbo_v2_5")


class FallbackTests(unittest.TestCase):
    def _service(self, primary_chunks, fallback_chunks=(b"openai",)):
        with _env():
            service = tts_service.TTSService()
        service.primary = MagicMock()
        service.primary.stream_text_to_speech.side_effect = lambda *a, **k: primary_chunks()
        service.fallback = MagicMock()
        service.fallback.stream_text_to_speech.side_effect = lambda *a, **k: iter(fallback_chunks)
        return service

    def test_primary_audio_is_streamed_and_previous_text_passed_through(self):
        service = self._service(lambda: iter([b"a", b"b"]))
        audio = list(service.stream_text_to_speech("Second.", previous_text="First."))
        self.assertEqual(audio, [b"a", b"b"])
        _, kwargs = service.primary.stream_text_to_speech.call_args
        self.assertEqual(kwargs["previous_text"], "First.")
        service.fallback.stream_text_to_speech.assert_not_called()

    def test_failure_before_any_audio_speaks_the_line_with_openai(self):
        def refused():
            raise RuntimeError("ElevenLabs TTS failed (401)")
            yield b""  # pragma: no cover

        service = self._service(refused)
        self.assertEqual(list(service.stream_text_to_speech("Hello.")), [b"openai"])

    def test_after_a_refusal_lines_skip_the_primary_until_the_cooldown_ends(self):
        def refused():
            raise RuntimeError("ElevenLabs TTS failed (401)")
            yield b""  # pragma: no cover

        service = self._service(refused)
        list(service.stream_text_to_speech("One."))
        list(service.stream_text_to_speech("Two."))
        self.assertEqual(service.primary.stream_text_to_speech.call_count, 1)
        self.assertEqual(service.fallback.stream_text_to_speech.call_count, 2)

        service._primary_down_until = 0.0
        list(service.stream_text_to_speech("Three."))
        self.assertEqual(service.primary.stream_text_to_speech.call_count, 2)

    def test_failure_mid_clip_is_raised_not_spliced(self):
        def dies_midway():
            yield b"a"
            raise RuntimeError("connection reset")

        service = self._service(dies_midway)
        chunks = service.stream_text_to_speech("Hello.")
        self.assertEqual(next(chunks), b"a")
        with self.assertRaises(RuntimeError):
            next(chunks)
        service.fallback.stream_text_to_speech.assert_not_called()


class ElevenLabsRequestTests(unittest.TestCase):
    def test_previous_text_is_sent_and_trimmed_to_its_tail(self):
        with _env():
            service = ElevenLabsService()
        response = MagicMock(ok=True)
        response.__enter__.return_value = response
        response.iter_content.return_value = iter([b"mp3"])
        service.session.post = MagicMock(return_value=response)

        audio = list(service.stream_text_to_speech("Now.", previous_text="x" * 600 + "end."))

        self.assertEqual(audio, [b"mp3"])
        body = service.session.post.call_args.kwargs["json"]
        self.assertEqual(body["model_id"], "eleven_flash_v2_5")
        self.assertTrue(body["previous_text"].endswith("end."))
        self.assertEqual(len(body["previous_text"]), 500)

    def test_cloned_voice_refusal_says_what_to_fix(self):
        response = MagicMock(status_code=401, text='{"detail":{"status":"ivc_not_permitted"}}')
        response.json.return_value = {"detail": {"status": "ivc_not_permitted"}}
        message = _describe_failure(response, "voice-123")
        self.assertIn("instant voice clone", message)
        self.assertIn("voice-123", message)


if __name__ == "__main__":
    unittest.main()
