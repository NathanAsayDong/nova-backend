"""
Which voice Nova speaks with, and what happens when that voice refuses a line.

The chain is ElevenLabs -> Cartesia -> Qwen3-TTS (local) -> OpenAI: each one
is tried in order, and a provider that refuses a clip before any audio goes
out is skipped for its own cooldown window while the others are tried on
their own schedule. Qwen3-TTS additionally requires CUDA, torch and the
qwen-tts package; this suite mocks all of that so it never touches a GPU.
"""

import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from src.service import tts_service
from src.service.eleven_labs_service import ElevenLabsService, _describe_failure
from src.service.cartesia_service import CartesiaService
from src.service.cartesia_service import _describe_failure as _cartesia_describe_failure
from src.service import qwen_tts_service

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
        "TTS_PROVIDER_COOLDOWN_SECONDS",
        "QWEN_TTS_COOLDOWN_SECONDS",
    ):
        env.setdefault(key, "")
    return patch.dict(os.environ, env, clear=False)


def _full_chain_env(**overrides):
    env = {**FULL_CHAIN_ENV, **overrides}
    env = {k: v for k, v in env.items() if v is not None}
    for key in (
        "TTS_PROVIDER",
        "TTS_MODEL",
        "ELEVEN_LABS_MODEL_ID",
        "ELEVEN_LABS_API",
        "TTS_PROVIDER_COOLDOWN_SECONDS",
        "QWEN_TTS_COOLDOWN_SECONDS",
    ):
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
        tts_service._ChainedProvider(
            name, MagicMock(), tts_service.DEFAULT_TTS_PROVIDER_COOLDOWN_SECONDS
        )
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


class CooldownTests(unittest.TestCase):
    """The three-hour (by default) cooldown clock: its default and env-var
    override, that a provider in cooldown is skipped without ever being
    called, and that it is retried once its cooldown has elapsed. All driven
    by a fake clock (`time.monotonic` patched to a controllable value) —
    nothing here sleeps."""

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

    def test_default_cooldown_is_three_hours(self):
        self.assertEqual(tts_service.DEFAULT_TTS_PROVIDER_COOLDOWN_SECONDS, 10800)
        with _env():
            service = tts_service.TTSService()
        self.assertTrue(all(p.cooldown_seconds == 10800 for p in service.chain))

    def test_cooldown_is_configurable_via_env_var(self):
        with _env(TTS_PROVIDER_COOLDOWN_SECONDS="60"):
            service = tts_service.TTSService()
        self.assertTrue(all(p.cooldown_seconds == 60 for p in service.chain))

    def test_invalid_cooldown_env_var_falls_back_to_the_three_hour_default(self):
        with _env(TTS_PROVIDER_COOLDOWN_SECONDS="not-a-number"):
            service = tts_service.TTSService()
        self.assertTrue(all(p.cooldown_seconds == 10800 for p in service.chain))

    def test_negative_cooldown_env_var_falls_back_to_the_three_hour_default(self):
        with _env(TTS_PROVIDER_COOLDOWN_SECONDS="-5"):
            service = tts_service.TTSService()
        self.assertTrue(all(p.cooldown_seconds == 10800 for p in service.chain))

    def test_a_provider_in_cooldown_is_skipped_with_no_network_attempt(self):
        service = self._service("elevenlabs", "cartesia", "openai")
        service.chain[1].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: iter([b"cartesia-audio"])
        )
        clock = [1_000.0]
        with patch.object(tts_service.time, "monotonic", side_effect=lambda: clock[0]):
            # ElevenLabs already failed earlier and is down for three hours.
            service.chain[0].down_until = clock[0] + 10800

            audio = list(service.stream_text_to_speech("Hello."))

        self.assertEqual(audio, [b"cartesia-audio"])
        service.chain[0].service.stream_text_to_speech.assert_not_called()

    def test_provider_is_retried_once_its_cooldown_expires(self):
        service = self._service("elevenlabs", "openai")
        service.chain[0].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: self._refuses("ElevenLabs TTS failed (401)")()
        )
        service.chain[1].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: iter([b"openai-audio"])
        )
        clock = [1_000.0]
        with patch.object(tts_service.time, "monotonic", side_effect=lambda: clock[0]):
            # First line: ElevenLabs fails for real and is put into a
            # three-hour cooldown measured from this fake "now".
            audio = list(service.stream_text_to_speech("One."))
            self.assertEqual(audio, [b"openai-audio"])
            self.assertEqual(service.chain[0].down_until, clock[0] + 10800)

            # Just short of three hours later: still skipped, no attempt.
            clock[0] += 10800 - 1
            service.chain[0].service.stream_text_to_speech.reset_mock()
            list(service.stream_text_to_speech("Two."))
            service.chain[0].service.stream_text_to_speech.assert_not_called()

            # The cooldown has now elapsed: ElevenLabs is tried again.
            clock[0] += 2
            service.chain[0].service.stream_text_to_speech.side_effect = (
                lambda *a, **k: iter([b"elevenlabs-audio"])
            )
            audio = list(service.stream_text_to_speech("Three."))

        self.assertEqual(audio, [b"elevenlabs-audio"])
        service.chain[0].service.stream_text_to_speech.assert_called_once()


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
        env.setdefault("CARTESIA_API_VERSION", "")
        env.setdefault("CARTESIA_EMOTION", "")
        return patch.dict(os.environ, env, clear=False)

    def test_missing_api_key_raises_value_error(self):
        with patch.dict(os.environ, {"CARTESIA_API_KEY": ""}, clear=False):
            with self.assertRaises(ValueError):
                CartesiaService()

    def test_sonic_3_is_the_default_model_and_overridable(self):
        with self._env():
            self.assertEqual(CartesiaService().model_id, "sonic-3")
        with self._env(CARTESIA_MODEL_ID="sonic-3.6"):
            self.assertEqual(CartesiaService().model_id, "sonic-3.6")

    def test_default_api_version_header_is_sent(self):
        with self._env():
            service = CartesiaService()
        self.assertEqual(service.api_version, "2026-08-14")
        self.assertEqual(service.session.headers["Cartesia-Version"], "2026-08-14")

    def test_api_version_is_overridable(self):
        with self._env(CARTESIA_API_VERSION="2099-01-01"):
            service = CartesiaService()
        self.assertEqual(service.session.headers["Cartesia-Version"], "2099-01-01")

    def test_content_is_the_default_emotion(self):
        with self._env():
            self.assertEqual(CartesiaService().emotion, "content")

    def test_emotion_env_var_accepts_excited(self):
        with self._env(CARTESIA_EMOTION="excited"):
            self.assertEqual(CartesiaService().emotion, "excited")

    def test_emotion_env_var_accepts_content_explicitly(self):
        with self._env(CARTESIA_EMOTION="content"):
            self.assertEqual(CartesiaService().emotion, "content")

    def test_emotion_env_var_is_case_insensitive(self):
        with self._env(CARTESIA_EMOTION="EXCITED"):
            self.assertEqual(CartesiaService().emotion, "excited")

    def test_invalid_emotion_falls_back_to_content(self):
        for invalid in ("angry", "ecstatic", "not-a-real-emotion", "  "):
            with self._env(CARTESIA_EMOTION=invalid):
                self.assertEqual(
                    CartesiaService().emotion,
                    "content",
                    f"expected fallback to content for {invalid!r}",
                )

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

    def test_request_body_carries_the_configured_emotion(self):
        with self._env(CARTESIA_EMOTION="excited"):
            service = CartesiaService()
        response = MagicMock(ok=True)
        response.__enter__.return_value = response
        response.iter_content.return_value = iter([b"mp3"])
        service.session.post = MagicMock(return_value=response)

        list(service.stream_text_to_speech("Now."))

        body = service.session.post.call_args.kwargs["json"]
        self.assertEqual(body["generation_config"], {"emotion": "excited"})

    def test_request_body_falls_back_to_content_in_generation_config(self):
        with self._env(CARTESIA_EMOTION="bogus"):
            service = CartesiaService()
        response = MagicMock(ok=True)
        response.__enter__.return_value = response
        response.iter_content.return_value = iter([b"mp3"])
        service.session.post = MagicMock(return_value=response)

        list(service.stream_text_to_speech("Now."))

        body = service.session.post.call_args.kwargs["json"]
        self.assertEqual(body["generation_config"], {"emotion": "content"})

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


class _FakeTorch(types.ModuleType):
    """Minimal stand-in for `torch`, with a controllable `cuda.is_available()`."""

    def __init__(self, cuda_available: bool):
        super().__init__("torch")
        cuda_ns = types.SimpleNamespace(is_available=lambda: cuda_available)
        self.cuda = cuda_ns
        self.bfloat16 = "bfloat16-sentinel"


def _install_fake_modules(cuda_available: bool = True, qwen_tts_present: bool = True):
    """
    Patch sys.modules so qwen_tts_service's lazy imports succeed (or fail)
    without needing a real torch/CUDA/qwen-tts install. Returns the patcher;
    caller is responsible for stop()ing it (use as a context manager via
    `with _install_fake_modules(...):`).
    """
    modules = dict(sys.modules)
    modules["torch"] = _FakeTorch(cuda_available)
    if qwen_tts_present:
        fake_qwen_tts = types.ModuleType("qwen_tts")
        fake_qwen_tts.Qwen3TTS = MagicMock()
        modules["qwen_tts"] = fake_qwen_tts
    elif "qwen_tts" in modules:
        del modules["qwen_tts"]
    return patch.dict(sys.modules, modules, clear=True)


class QwenTTSProviderSelectionTests(unittest.TestCase):
    """Chain ordering and the missing-dependency path, with torch/CUDA/qwen_tts
    faked out — nothing here touches a real GPU or downloads anything."""

    def test_qwen_slots_between_cartesia_and_openai_when_available(self):
        with _full_chain_env(), _install_fake_modules(cuda_available=True, qwen_tts_present=True):
            service = tts_service.TTSService()
        self.assertEqual(
            [p.name for p in service.chain], ["elevenlabs", "cartesia", "qwen", "openai"]
        )
        self.assertIsInstance(service.chain[2].service, qwen_tts_service.QwenTTSService)

    def test_missing_cuda_skips_qwen_without_breaking_the_chain(self):
        with _full_chain_env(), _install_fake_modules(cuda_available=False, qwen_tts_present=True):
            service = tts_service.TTSService()
        self.assertEqual([p.name for p in service.chain], ["elevenlabs", "cartesia", "openai"])

    def test_missing_qwen_tts_package_skips_qwen_without_breaking_the_chain(self):
        with _full_chain_env(), _install_fake_modules(cuda_available=True, qwen_tts_present=False):
            service = tts_service.TTSService()
        self.assertEqual([p.name for p in service.chain], ["elevenlabs", "cartesia", "openai"])

    def test_missing_torch_skips_qwen_without_breaking_the_chain(self):
        modules = dict(sys.modules)
        modules.pop("torch", None)
        with _full_chain_env(), patch.dict(sys.modules, modules, clear=True):
            with patch("builtins.__import__", side_effect=_raise_for_torch):
                service = tts_service.TTSService()
        self.assertEqual([p.name for p in service.chain], ["elevenlabs", "cartesia", "openai"])

    def test_qwen_opt_out_still_works_via_openai(self):
        """TTS_PROVIDER=openai is a full opt-out: Qwen (like ElevenLabs and
        Cartesia) is skipped even when its dependencies are fully available."""
        with _env(TTS_PROVIDER="openai"), _install_fake_modules():
            service = tts_service.TTSService()
        self.assertEqual([p.name for p in service.chain], ["openai"])


def _raise_for_torch(name, *args, **kwargs):
    if name == "torch":
        raise ImportError("No module named 'torch'")
    return _REAL_IMPORT(name, *args, **kwargs)


_REAL_IMPORT = __import__


class QwenTTSCooldownTests(unittest.TestCase):
    def test_default_cooldown_is_sixty_seconds(self):
        self.assertEqual(qwen_tts_service.DEFAULT_QWEN_TTS_COOLDOWN_SECONDS, 60)
        with patch.dict(os.environ, {"QWEN_TTS_COOLDOWN_SECONDS": ""}, clear=False):
            self.assertEqual(qwen_tts_service._qwen_cooldown_seconds(), 60)

    def test_cooldown_is_configurable_via_env_var(self):
        with patch.dict(os.environ, {"QWEN_TTS_COOLDOWN_SECONDS": "15"}, clear=False):
            self.assertEqual(qwen_tts_service._qwen_cooldown_seconds(), 15)

    def test_invalid_cooldown_env_var_falls_back_to_the_default(self):
        with patch.dict(os.environ, {"QWEN_TTS_COOLDOWN_SECONDS": "nope"}, clear=False):
            self.assertEqual(qwen_tts_service._qwen_cooldown_seconds(), 60)

    def test_negative_cooldown_env_var_falls_back_to_the_default(self):
        with patch.dict(os.environ, {"QWEN_TTS_COOLDOWN_SECONDS": "-1"}, clear=False):
            self.assertEqual(qwen_tts_service._qwen_cooldown_seconds(), 60)

    def test_qwen_link_uses_its_own_cooldown_not_the_shared_one(self):
        """Qwen's cooldown (60s default) is independent of
        TTS_PROVIDER_COOLDOWN_SECONDS, which only governs the paid providers."""
        with (
            _full_chain_env(TTS_PROVIDER_COOLDOWN_SECONDS="10800"),
            _install_fake_modules(cuda_available=True, qwen_tts_present=True),
        ):
            service = tts_service.TTSService()
        by_name = {p.name: p for p in service.chain}
        self.assertEqual(by_name["elevenlabs"].cooldown_seconds, 10800)
        self.assertEqual(by_name["cartesia"].cooldown_seconds, 10800)
        self.assertEqual(by_name["qwen"].cooldown_seconds, 60)

    def test_qwen_cooldown_is_independently_overridable(self):
        with (
            _full_chain_env(
                TTS_PROVIDER_COOLDOWN_SECONDS="10800", QWEN_TTS_COOLDOWN_SECONDS="5"
            ),
            _install_fake_modules(cuda_available=True, qwen_tts_present=True),
        ):
            service = tts_service.TTSService()
        by_name = {p.name: p for p in service.chain}
        self.assertEqual(by_name["qwen"].cooldown_seconds, 5)
        self.assertEqual(by_name["elevenlabs"].cooldown_seconds, 10800)


class QwenTTSFallthroughTests(unittest.TestCase):
    """Qwen's place in the fallback chain: Cartesia falling through reaches
    Qwen before OpenAI, and Qwen failing falls through to OpenAI in turn."""

    def _service(self, *names: str) -> tts_service.TTSService:
        with _full_chain_env(), _install_fake_modules(cuda_available=True, qwen_tts_present=True):
            service = tts_service.TTSService()
        _mock_chain(service, *names)
        return service

    def _refuses(self, message: str):
        def refused():
            raise RuntimeError(message)
            yield b""  # pragma: no cover

        return refused

    def test_cartesia_failure_falls_through_to_qwen_not_openai(self):
        service = self._service("elevenlabs", "cartesia", "qwen", "openai")
        service.chain[0].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: self._refuses("ElevenLabs TTS failed (401)")()
        )
        service.chain[1].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: self._refuses("Cartesia TTS failed (429)")()
        )
        service.chain[2].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: iter([b"qwen-audio"])
        )
        audio = list(service.stream_text_to_speech("Hello."))
        self.assertEqual(audio, [b"qwen-audio"])
        service.chain[3].service.stream_text_to_speech.assert_not_called()

    def test_qwen_failure_falls_through_to_openai(self):
        service = self._service("elevenlabs", "cartesia", "qwen", "openai")
        for link in service.chain[:3]:
            link.service.stream_text_to_speech.side_effect = (
                lambda *a, **k: self._refuses("refused")()
            )
        service.chain[3].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: iter([b"openai-audio"])
        )
        audio = list(service.stream_text_to_speech("Hello."))
        self.assertEqual(audio, [b"openai-audio"])

    def test_qwen_in_cooldown_is_skipped_without_being_called(self):
        service = self._service("elevenlabs", "cartesia", "qwen", "openai")
        service.chain[0].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: self._refuses("ElevenLabs TTS failed (401)")()
        )
        service.chain[1].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: self._refuses("Cartesia TTS failed (429)")()
        )
        service.chain[2].down_until = float("inf")
        service.chain[3].service.stream_text_to_speech.side_effect = (
            lambda *a, **k: iter([b"openai-audio"])
        )
        audio = list(service.stream_text_to_speech("Hello."))
        self.assertEqual(audio, [b"openai-audio"])
        service.chain[2].service.stream_text_to_speech.assert_not_called()


class QwenTTSGenerationTests(unittest.TestCase):
    """QwenTTSService.stream_text_to_speech itself, with the model and mp3
    encoder both mocked — no torch, no CUDA, no real audio."""

    def _service(self) -> qwen_tts_service.QwenTTSService:
        with _full_chain_env(), _install_fake_modules(cuda_available=True, qwen_tts_present=True):
            return qwen_tts_service.QwenTTSService()

    def test_output_mime_type_is_mp3_like_the_other_providers(self):
        service = self._service()
        self.assertEqual(service.output_mime_type(), "audio/mpeg")

    def test_stream_text_to_speech_yields_encoded_mp3_chunks(self):
        service = self._service()

        fake_model = object()
        fake_encoder = MagicMock()
        fake_encoder.encode.side_effect = lambda chunk: b"mp3-" + chunk
        fake_encoder.flush.return_value = b"mp3-tail"

        with (
            patch.object(qwen_tts_service, "_get_model", return_value=fake_model),
            patch.object(qwen_tts_service, "_mp3_encoder", return_value=fake_encoder),
            patch.object(
                qwen_tts_service,
                "_generate_pcm_chunks",
                return_value=iter([b"pcm1", b"pcm2"]),
            ),
        ):
            chunks = list(service.stream_text_to_speech("Hello there."))

        self.assertEqual(chunks, [b"mp3-pcm1", b"mp3-pcm2", b"mp3-tail"])

    def test_missing_lameenc_raises_clean_error(self):
        service = self._service()
        with (
            patch.object(qwen_tts_service, "_get_model", return_value=object()),
            patch.dict(sys.modules, {"lameenc": None}),
        ):
            with self.assertRaisesRegex(RuntimeError, "lameenc"):
                list(service.stream_text_to_speech("Hello."))


if __name__ == "__main__":
    unittest.main()
