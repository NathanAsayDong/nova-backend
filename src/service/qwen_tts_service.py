"""
Qwen3-TTS (https://github.com/QwenLM/Qwen3-TTS, Apache 2.0) run locally on the
tower's own GPU, as a link in TTSService's fallback chain between Cartesia and
OpenAI.

Why it sits where it does: ElevenLabs and Cartesia are paid APIs that can run
out of quota or have a plan lapse — problems that are typically same-day
things to notice and fix, hence their hours-long cooldown. A local model has
no quota to run out, but it does depend on the GPU actually being free, the
weights being on disk, and the optional `qwen-tts` package being installed —
none of which is guaranteed on every box this code runs on. When one of those
is missing, construction raises a clean RuntimeError/ValueError so
TTSService's chain-builder (`_build_provider`) simply skips this provider and
falls through to OpenAI, the same way a missing ELEVEN_LABS_API_KEY does today.

Heavy imports (torch, qwen_tts, lameenc) are deferred to inside functions, not
the module top, and the model itself is loaded lazily on first use and cached
process-wide — so installing nova-backend without the optional `qwen` extra
never fails on import, and constructing TTSService() at app startup never
pays the (multi-second, multi-GB) model load cost before it is needed. See
README / docs/QWEN_TTS.md for install steps.

API: `qwen_tts.Qwen3TTSModel.from_pretrained(...)` and
`model.generate_custom_voice(text=, language=, speaker=)`, which returns the
whole utterance as `(wavs, sample_rate)` — the documented Python API has no
chunk-yielding streaming call, so a line is synthesized in full and then
mp3-encoded and yielded in slices. Matches the qwen-tts README (PyPI 0.1.1);
not yet exercised on the tower's GPU — see docs/QWEN_TTS.md.
"""

import os
import threading
import time
from collections.abc import Iterator
from typing import Any

from src.harness.turn_timer import TurnTimer, mark as _mark_timing

# CustomVoice (preset voices, no cloning) is the decided checkpoint: the
# smallest/fastest in the Qwen3-TTS family, fits comfortably in the ~4.5GB of
# VRAM free on the tower alongside everything else already using the 3080,
# and its preset-voice API is simpler to wire than the Base checkpoint's
# voice-cloning flow, which this provider does not implement. Override with
# QWEN_TTS_MODEL (e.g. a 1.7B CustomVoice checkpoint) once more VRAM is free.
DEFAULT_QWEN_TTS_MODEL = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"

# CustomVoice preset speaker. The checkpoint ships nine (Vivian, Serena,
# Uncle_Fu, Dylan, Eric, Ryan, Aiden, Ono_Anna, Sohee); Ryan and Aiden are the
# native-English ones. Override with QWEN_TTS_VOICE.
DEFAULT_QWEN_TTS_VOICE = "Ryan"
# Passed as `language=`; "Auto" lets the model detect it per line.
DEFAULT_QWEN_TTS_LANGUAGE = "English"
DEFAULT_QWEN_TTS_DEVICE = "cuda"
DEFAULT_QWEN_TTS_MP3_BIT_RATE = 128

# How much audio (in seconds) goes into each mp3 chunk yielded downstream.
_MP3_SLICE_SECONDS = 0.5

# Local inference, so a refusal almost always means "the model/GPU isn't
# usable right now" (OOM, driver hiccup, still loading) rather than a
# quota/plan problem worth waiting hours to clear — unlike ElevenLabs/Cartesia,
# whose default is DEFAULT_TTS_PROVIDER_COOLDOWN_SECONDS (three hours, see
# tts_service.py). Retry soon. Override with QWEN_TTS_COOLDOWN_SECONDS.
DEFAULT_QWEN_TTS_COOLDOWN_SECONDS = 60


def _qwen_cooldown_seconds() -> float:
    raw = (os.getenv("QWEN_TTS_COOLDOWN_SECONDS") or "").strip()
    if not raw:
        return DEFAULT_QWEN_TTS_COOLDOWN_SECONDS
    try:
        value = float(raw)
    except ValueError:
        print(
            f"QWEN_TTS_COOLDOWN_SECONDS={raw!r} is not a number; using "
            f"{DEFAULT_QWEN_TTS_COOLDOWN_SECONDS}."
        )
        return DEFAULT_QWEN_TTS_COOLDOWN_SECONDS
    if value < 0:
        print(
            f"QWEN_TTS_COOLDOWN_SECONDS={raw!r} is negative; using "
            f"{DEFAULT_QWEN_TTS_COOLDOWN_SECONDS}."
        )
        return DEFAULT_QWEN_TTS_COOLDOWN_SECONDS
    return value


# One model resident in process memory at a time, guarded by a lock both for
# loading (so two threads racing to construct the first request don't load it
# twice) and for generation (a 3080 with ~4.5GB free has no room for two
# concurrent generate() calls, and nothing in qwen_tts is assumed thread-safe).
_model_lock = threading.Lock()
_model_cache: dict[tuple[str, str, str], Any] = {}


def _load_model(model_name: str, device: str, dtype_name: str) -> Any:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "torch is not importable; Qwen3-TTS needs torch with a CUDA "
            "build. See docs/QWEN_TTS.md for the Windows install steps."
        ) from exc

    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is not available (torch.cuda.is_available() is False); "
            "Qwen3-TTS needs a CUDA GPU. Set QWEN_TTS_DEVICE=cpu to force "
            "CPU inference (slow, not recommended) or fix the CUDA install."
        )

    try:
        from qwen_tts import Qwen3TTSModel  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "The `qwen-tts` package is not installed (`uv pip install qwen-tts`) "
            "— see docs/QWEN_TTS.md."
        ) from exc

    kwargs: dict[str, Any] = {"device_map": _device_map(device)}
    if dtype_name == "bfloat16":
        kwargs["dtype"] = torch.bfloat16
    attn = _attn_implementation()
    if attn:
        kwargs["attn_implementation"] = attn
    try:
        return Qwen3TTSModel.from_pretrained(model_name, **kwargs)
    except Exception as exc:
        if "attn_implementation" in kwargs and not os.getenv("QWEN_TTS_ATTN"):
            # The model class may not accept the auto-picked attention
            # backend; retry with whatever it defaults to.
            kwargs.pop("attn_implementation")
            try:
                return Qwen3TTSModel.from_pretrained(model_name, **kwargs)
            except Exception as retry_exc:
                exc = retry_exc
        raise RuntimeError(
            f"Could not load Qwen3-TTS weights for {model_name!r}: {exc}. "
            "Confirm the checkpoint has been downloaded (see "
            "docs/QWEN_TTS.md) and that QWEN_TTS_MODEL names a valid "
            "Hugging Face repo id."
        ) from exc


def _device_map(device: str) -> str:
    # qwen-tts takes a transformers-style device_map; "cuda" alone means the
    # first GPU. "cuda:1", "cpu", etc. pass through unchanged.
    return "cuda:0" if device == "cuda" else device


def _attn_implementation() -> str | None:
    """FlashAttention 2 when flash-attn is installed (the README's
    recommendation, lower VRAM), else PyTorch's built-in SDPA. QWEN_TTS_ATTN
    overrides; set it to "default" to pass nothing and let the model pick."""
    override = (os.getenv("QWEN_TTS_ATTN") or "").strip()
    if override:
        return None if override.lower() == "default" else override
    import importlib.util

    return "flash_attention_2" if importlib.util.find_spec("flash_attn") else "sdpa"


def _get_model(model_name: str, device: str, dtype_name: str) -> Any:
    key = (model_name, device, dtype_name)
    with _model_lock:
        cached = _model_cache.get(key)
        if cached is None:
            cached = _load_model(model_name, device, dtype_name)
            _model_cache[key] = cached
        return cached


def warmup(model_name: str | None = None, device: str | None = None) -> None:
    """
    Load the model ahead of the first real request.

    Blocking — call it from a background thread/task at app startup (guarded
    by, e.g., QWEN_TTS_WARMUP=1) rather than inline in an async path. Any
    failure (no GPU, package not installed, weights missing) is caught and
    logged, never raised: a failed warmup must not crash startup, and the
    provider still gets the same clean-error treatment on first real use via
    TTSService's fallback chain.
    """
    try:
        _get_model(
            model_name or os.getenv("QWEN_TTS_MODEL") or DEFAULT_QWEN_TTS_MODEL,
            (device or os.getenv("QWEN_TTS_DEVICE") or DEFAULT_QWEN_TTS_DEVICE).strip().lower(),
            "bfloat16",
        )
        print("Qwen3-TTS warmup complete.")
    except Exception as exc:
        print(f"Qwen3-TTS warmup skipped: {exc}")


def _mp3_encoder(sample_rate: int, bit_rate: int) -> Any:
    try:
        import lameenc
    except ImportError as exc:
        raise RuntimeError(
            "mp3 encoding requires the `lameenc` package (part of the "
            "optional `qwen` extra) so Qwen3-TTS's output matches the mp3 "
            "container ElevenLabs/Cartesia/OpenAI already hand the rest of "
            "the pipeline. See docs/QWEN_TTS.md."
        ) from exc
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(bit_rate)
    encoder.set_in_sample_rate(sample_rate)
    encoder.set_channels(1)
    encoder.set_quality(2)
    return encoder


def _synthesize(model: Any, text: str, speaker: str, language: str) -> tuple[bytes, int]:
    """
    Run one CustomVoice generation and return (mono int16 PCM bytes, sample rate).

    `generate_custom_voice` returns `(wavs, sr)` where `wavs[0]` is the
    waveform for our single input — a float array (numpy or torch) in
    [-1, 1], or int16 samples. The sample rate comes from the model rather
    than being assumed.
    """
    import numpy as np

    wavs, sample_rate = model.generate_custom_voice(
        text=text, language=language, speaker=speaker
    )
    wav = wavs[0]
    if hasattr(wav, "detach"):  # torch tensor
        wav = wav.detach().float().cpu().numpy()
    arr = np.asarray(wav).reshape(-1)
    if arr.dtype != np.int16:
        arr = (np.clip(arr.astype(np.float32), -1.0, 1.0) * 32767.0).astype(np.int16)
    return arr.tobytes(), int(sample_rate)


class QwenTTSService:
    """
    Local Qwen3-TTS, streamed the same shape as ElevenLabsService/CartesiaService
    so it slots into TTSService's fallback chain without special-casing.

    Construction only does cheap checks (torch importable, CUDA available,
    qwen_tts importable) — no weights are downloaded or loaded here, so a box
    without a GPU or without the optional dependencies installed fails fast
    and quietly skips this provider instead of hanging the chain on the first
    real request. The actual model load is lazy (first call to
    stream_text_to_speech) and cached process-wide; see `_get_model`.
    """

    def __init__(self) -> None:
        self.model_name = os.getenv("QWEN_TTS_MODEL") or DEFAULT_QWEN_TTS_MODEL
        self.voice = os.getenv("QWEN_TTS_VOICE") or DEFAULT_QWEN_TTS_VOICE
        self.language = os.getenv("QWEN_TTS_LANGUAGE") or DEFAULT_QWEN_TTS_LANGUAGE
        self.device = (os.getenv("QWEN_TTS_DEVICE") or DEFAULT_QWEN_TTS_DEVICE).strip().lower()
        self.bit_rate = int(
            os.getenv("QWEN_TTS_MP3_BIT_RATE") or DEFAULT_QWEN_TTS_MP3_BIT_RATE
        )

        try:
            import torch
        except ImportError as exc:
            raise RuntimeError(
                "torch is not installed; Qwen3-TTS needs the optional `qwen` "
                "setup — see docs/QWEN_TTS.md."
            ) from exc

        if self.device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA is not available (torch.cuda.is_available() is False); "
                "Qwen3-TTS needs a CUDA GPU. Set QWEN_TTS_DEVICE=cpu to force "
                "CPU (slow) or fix the CUDA install."
            )

        try:
            import qwen_tts  # noqa: F401  (import-only availability check)
        except ImportError as exc:
            raise RuntimeError(
                "The `qwen-tts` package is not installed; see "
                "docs/QWEN_TTS.md for the optional local-TTS setup."
            ) from exc

        print(
            f"Qwen3-TTS: model {self.model_name}, voice {self.voice}, "
            f"language {self.language}, device {self.device}"
        )

    def stream_text_to_speech(
        self,
        text: str,
        chunk_size: int = 4096,
        previous_text: str | None = None,
        timer: "TurnTimer | None" = None,
    ) -> Iterator[bytes]:
        """
        Stream `text` as mp3 chunks, generated locally.

        `previous_text` is accepted for interface parity with the other
        providers but unused: Qwen3-TTS's per-line API has no equivalent of
        ElevenLabs' `previous_text` continuity field. `chunk_size` is also
        unused. qwen-tts's Python API returns a whole line at once, so the
        line is synthesized first, then mp3-encoded and yielded in
        half-second slices; first-byte latency is the full generation time.
        """
        _mark_timing(
            timer,
            "tts_request_sent",
            provider="qwen",
            model=self.model_name,
            chars=len(text),
        )
        request_started_at = time.monotonic()
        model = _get_model(self.model_name, self.device, "bfloat16")

        with _model_lock:
            pcm, sample_rate = _synthesize(model, text, self.voice, self.language)
        encoder = _mp3_encoder(sample_rate, self.bit_rate)

        total_bytes = 0
        n_chunks = 0
        first_byte_marked = False
        slice_bytes = max(2, int(sample_rate * _MP3_SLICE_SECONDS) * 2)  # int16 mono

        for start in range(0, len(pcm), slice_bytes):
            mp3_bytes = bytes(encoder.encode(pcm[start : start + slice_bytes]))
            if not mp3_bytes:
                continue
            total_bytes += len(mp3_bytes)
            n_chunks += 1
            if not first_byte_marked:
                first_byte_marked = True
                _mark_timing(
                    timer,
                    "first_tts_byte",
                    provider="qwen",
                    wait_ms=round((time.monotonic() - request_started_at) * 1000),
                )
            yield mp3_bytes
        tail = bytes(encoder.flush())

        if tail:
            total_bytes += len(tail)
            n_chunks += 1
            yield tail

        _mark_timing(
            timer,
            "tts_done",
            provider="qwen",
            chars=len(text),
            bytes=total_bytes,
            chunks=n_chunks,
            total_ms=round((time.monotonic() - request_started_at) * 1000),
        )

    def text_to_speech(self, text: str) -> tuple[bytes, str]:
        audio_bytes = b"".join(self.stream_text_to_speech(text))
        return audio_bytes, self.output_mime_type()

    def output_mime_type(self) -> str:
        # mp3, same container as ElevenLabs/Cartesia/OpenAI (see
        # tts_service.TTSService.output_mime_type, which always reports the
        # *first* provider in the chain regardless of which one actually
        # answered) — so the client's declared mimeType is correct no matter
        # which provider in the chain spoke a given line.
        return "audio/mpeg"
