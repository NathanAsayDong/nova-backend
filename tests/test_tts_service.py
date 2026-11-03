"""
Which voice Nova speaks with, and what happens when that voice refuses a line.

The chain is ElevenLabs -> Cartesia -> OpenAI: each one is tried in order,
and a provider that refuses a clip before any audio goes out is skipped for
its own cooldown window while the others are tried on their own schedule.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from src.service import tts_service
from src.service.eleven_labs_service import ElevenLabsService, _describe_failure
from src.service.cartesia_service import CartesiaService
from src.service.cartesia_service import _describe_failure as _cartesia_describe_failure

ELEVEN_ENV = {
    "ELEVEN_LABS_API_KEY": "test-eleven-key",
    "ELEVEN_LABS_VOICE_ID": "test-voice",
    "OPENAI_API_KEY": "test-key",
}

FULL_CHAIN_ENV = {
    **ELEVEN_ENV,
    "CARTESIA_API_KEY": "test-cartesia-key",
    "CARTESIA_VOICE_ID": "test-cartesia-voice",
}


def _env(**overrides):
    env = {**ELEVEN_ENV, **overrides}
    env = {k: v for k, v in env.items() if v is not None}
    for key in (
        "TTS_PROVIDER",
        "TTS_MODEL",
        "ELEVEN_LABS_MODEL_ID",
        "ELEVEN_LABS_API",
        "CARTESIA_API_KEY",
        "CARTESIA_VOICE_ID",
    ):
        env.setdefault(key, "")
    return patch.dict(os.environ, env, clear=False)


def _full_chain_env(**overrides):
    env = {**FULL_CHAIN_ENV, **overrides}
    env = {k: v for k, v in env.items() if v is not None}
    for key in ("TTS_PROVIDER", "TTS_MODEL", "ELEVEN_LABS_MODEL_ID", "ELEVEN_LABS_API"):
        env.setdefault(key, "")
    return patch.dict(os.environ, env, clear=False)


def _mock_chain(service: tts_service.TTSService, *names: str) -> None:
    """Replace every provider in `service`'s chain with a MagicMock, so a
    test can drive `stream_text_to_speech` without any of it reaching the
    network — construction (which does hit the network as part of each
    provider's own setup, e.g. a session) already happened against real
    credentials during __init__, but nothing beyond that must run for real.
    """
    service.chain = [
        tts_service._ChainedProvider(name, MagicMock(), tts_service.TTS_FALLBACK_COOLDOWN_SECONDS)
        for name in names
    ]
    service.primary = service.chain[0].service
    service.fallback = service.chain[1].service if len(service.chain) > 1 else None


class ProviderSelectionTests(unittest.TestCase):
    def test_elevenlabs_is_the_default(self):
        with _env():
            service = tts_service.TTSService()
        self.assertEqual(service.provider, "elevenlabs")
        self.assertEqual([p.name for p in service.chain], ["elevenlabs", "openai"])
        self.assertIsInstance(service.fallback, tts_service.OpenAITTS)

    def test_full_chain_is_elevenlabs_then_cartesia_then_openai(self):
        with _full_chain_env():
            service = tts_service.TTSService()
        self.assertEqual([p.name for p in service.chain], ["elevenlabs", "cartesia", "openai"])
        self.assertIsInstance(service.chain[1].service, CartesiaService)

    def test_tts_provider_openai_opts_out(self):
        with _env(TTS_PROVIDER="openai"):
            service = tts_service.TTSService()
        self.assertEqual(service.provider, "openai")
        self.assertIsNone(service.fallback)
        self.assertEqual([p.name for p in service.chain], ["openai"])

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
        self.assertIsNone(service.fallback)

    def test_missing_cartesia_key_skips_it_without_breaking_the_chain(self):
        with _env():  # no CARTESIA_API_KEY
            service = tts_service.TTSService()
        self.assertEqual([p.name for p in service.chain], ["elevenlabs", "openai"])

    def test_flash_is_the_default_model_and_overridable(self):
        with _env():
            self.assertEqual(ElevenLabsService().model_id, "eleven_flash_v2_5")
        with _env(ELEVEN_LABS_MODEL_ID="eleven_turbo_v2_5"):
            self.assertEqual(ElevenLabsService().model_id, "eleven_turbo_v2_5")


class FallbackChainTests(unittest.TestCase):
    """Chain behavior, driven entirely through mocked providers so nothing
    here ever makes a real network call."""

    def _service(self, *names: str) -> tts_service.TTSService:
        with _env():
            service = tts_service.TTSService()
        _mock_chain(service, *names)
        return service

    def _refuses(self, message: str):
        def refused():
            raise RuntimeError(message)
            yield b""  # pragma: no cover

        return refused

    def test_primary_audio_is_streamed_and_previous_text_passed_through(self):
        service = self._service("elevenlabs", "cartesia", "openai")
        service.chain[0].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: iter([b"a", b"b"])
        )
        audio = list(service.stream_text_to_speech("Second.", previous_text="First."))
        self.assertEqual(audio, [b"a", b"b"])
        _, kwargs = service.chain[0].service.stream_text_to_speech.call_args
        self.assertEqual(kwargs["previous_text"], "First.")
        service.chain[1].service.stream_text_to_speech.assert_not_called()
        service.chain[2].service.stream_text_to_speech.assert_not_called()

    def test_elevenlabs_failure_falls_through_to_cartesia_not_openai(self):
        service = self._service("elevenlabs", "cartesia", "openai")
        service.chain[0].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: self._refuses("ElevenLabs TTS failed (401)")()
        )
        service.chain[1].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: iter([b"cartesia-audio"])
        )
        audio = list(service.stream_text_to_speech("Hello."))
        self.assertEqual(audio, [b"cartesia-audio"])
        service.chain[2].service.stream_text_to_speech.assert_not_called()

    def test_cartesia_also_failing_falls_through_to_openai(self):
        service = self._service("elevenlabs", "cartesia", "openai")
        service.chain[0].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: self._refuses("ElevenLabs TTS failed (401)")()
        )
        service.chain[1].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: self._refuses("Cartesia TTS failed (429)")()
        )
        service.chain[2].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: iter([b"openai-audio"])
        )
        audio = list(service.stream_text_to_speech("Hello."))
        self.assertEqual(audio, [b"openai-audio"])

    def test_after_elevenlabs_refuses_cartesia_is_tried_fresh_every_line(self):
        """Cartesia's own cooldown is independent of ElevenLabs': ElevenLabs
        being down does not itself put Cartesia in cooldown, so every line
        after the ElevenLabs failure still reaches Cartesia for real."""
        service = self._service("elevenlabs", "cartesia", "openai")
        service.chain[0].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: self._refuses("ElevenLabs TTS failed (401)")()
        )
        service.chain[1].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: iter([b"cartesia-audio"])
        )
        list(service.stream_text_to_speech("One."))
        list(service.stream_text_to_speech("Two."))
        self.assertEqual(service.chain[0].service.stream_text_to_speech.call_count, 1)
        self.assertEqual(service.chain[1].service.stream_text_to_speech.call_count, 2)
        service.chain[2].service.stream_text_to_speech.assert_not_called()

    def test_a_provider_in_cooldown_is_skipped_without_being_called(self):
        service = self._service("elevenlabs", "cartesia", "openai")
        service.chain[0].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: self._refuses("ElevenLabs TTS failed (401)")()
        )
        service.chain[1].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: iter([b"cartesia-audio"])
        )
        list(service.stream_text_to_speech("One."))  # ElevenLabs now in cooldown
        service.chain[0].service.stream_text_to_speech.reset_mock()
        list(service.stream_text_to_speech("Two."))
        service.chain[0].service.stream_text_to_speech.assert_not_called()

        service.chain[0].down_until = 0.0
        list(service.stream_text_to_speech("Three."))
        self.assertEqual(service.chain[0].service.stream_text_to_speech.call_count, 1)

    def test_each_providers_cooldown_is_independent(self):
        """ElevenLabs recovering (cooldown reset) does not reset Cartesia's
        own cooldown, and vice versa."""
        service = self._service("elevenlabs", "cartesia", "openai")
        service.chain[0].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: self._refuses("ElevenLabs TTS failed (401)")()
        )
        service.chain[1].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: self._refuses("Cartesia TTS failed (429)")()
        )
        service.chain[2].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: iter([b"openai-audio"])
        )
        list(service.stream_text_to_speech("One."))  # both elevenlabs and cartesia now cooling

        # ElevenLabs recovers; Cartesia is still down.
        service.chain[0].down_until = 0.0
        service.chain[0].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: iter([b"elevenlabs-audio"])
        )
        service.chain[1].service.stream_text_to_speech.reset_mock()
        audio = list(service.stream_text_to_speech("Two."))
        self.assertEqual(audio, [b"elevenlabs-audio"])
        service.chain[1].service.stream_text_to_speech.assert_not_called()

    def test_every_provider_exhausted_raises_the_last_error(self):
        service = self._service("elevenlabs", "openai")
        service.chain[0].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: self._refuses("ElevenLabs TTS failed (401)")()
        )
        service.chain[1].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: self._refuses("OpenAI TTS failed (500)")()
        )
        with self.assertRaisesRegex(RuntimeError, "OpenAI TTS failed"):
            list(service.stream_text_to_speech("Hello."))

    def test_failure_mid_clip_is_raised_not_spliced(self):
        def dies_midway():
            yield b"a"
            raise RuntimeError("connection reset")

        service = self._service("elevenlabs", "openai")
        service.chain[0].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: dies_midway()
        )
        chunks = service.stream_text_to_speech("Hello.")
        self.assertEqual(next(chunks), b"a")
        with self.assertRaises(RuntimeError):
            next(chunks)
        service.chain[1].service.stream_text_to_speech.assert_not_called()


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


class CartesiaRequestTests(unittest.TestCase):
    CARTESIA_ENV = {"CARTESIA_API_KEY": "test-cartesia-key", "CARTESIA_VOICE_ID": "test-voice"}

    def _env(self, **overrides):
        env = {**self.CARTESIA_ENV, **overrides}
        env = {k: v for k, v in env.items() if v is not None}
        env.setdefault("CARTESIA_MODEL_ID", "")
        return patch.dict(os.environ, env, clear=False)

    def test_missing_api_key_raises_value_error(self):
        with patch.dict(os.environ, {"CARTESIA_API_KEY": ""}, clear=False):
            with self.assertRaises(ValueError):
                CartesiaService()

    def test_sonic_2_is_the_default_model_and_overridable(self):
        with self._env():
            self.assertEqual(CartesiaService().model_id, "sonic-2")
        with self._env(CARTESIA_MODEL_ID="sonic-english"):
            self.assertEqual(CartesiaService().model_id, "sonic-english")

    def test_request_uses_voice_id_and_mp3_output_format(self):
        with self._env():
            service = CartesiaService()
        response = MagicMock(ok=True)
        response.__enter__.return_value = response
        response.iter_content.return_value = iter([b"mp3"])
        service.session.post = MagicMock(return_value=response)

        audio = list(service.stream_text_to_speech("Now."))

        self.assertEqual(audio, [b"mp3"])
        body = service.session.post.call_args.kwargs["json"]
        self.assertEqual(body["voice"], {"mode": "id", "id": "test-voice"})
        self.assertEqual(body["output_format"]["container"], "mp3")
        self.assertEqual(body["transcript"], "Now.")

    def test_failure_response_raises_with_status_and_body(self):
        with self._env():
            service = CartesiaService()
        response = MagicMock(ok=False, status_code=429, text="rate limited")
        response.__enter__.return_value = response
        service.session.post = MagicMock(return_value=response)

        with self.assertRaisesRegex(RuntimeError, "429"):
            list(service.stream_text_to_speech("Now."))

    def test_describe_failure_flags_rate_limit(self):
        response = MagicMock(status_code=429, text="rate limited")
        message = _cartesia_describe_failure(response, "voice-123")
        self.assertIn("rate limit", message.lower())


if __name__ == "__main__":
    unittest.main()
