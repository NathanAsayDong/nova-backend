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

Known-unverified: this environment has no CUDA GPU, so the actual qwen_tts
streaming call shape in `_generate_pcm_chunks` below was written against the
Qwen3-TTS repo's documented API rather than exercised against real hardware.
See docs/QWEN_TTS.md and the PR description for exactly what to check on the
tower.
"""

import os
import threading
import time
from collections.abc import Iterator
from typing import Any

from src.harness.turn_timer import TurnTimer, mark as _mark_timing

# CustomVoice is the smallest/fastest checkpoint in the Qwen3-TTS family and
# the one that fits comfortably in the ~4.5GB of VRAM free on the tower
# alongside everything else already using the 3080. Override with
# QWEN_TTS_MODEL (e.g. a 1.7B checkpoint) once more VRAM is free, or the Base
# checkpoint if voice cloning turns out simpler to wire than CustomVoice's
# preset-voice API.
DEFAULT_QWEN_TTS_MODEL = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"

# A placeholder preset voice name; set QWEN_TTS_VOICE to whichever preset (or
# cloned speaker id, if using the Base checkpoint) Nova should actually use.
DEFAULT_QWEN_TTS_VOICE = "default"
DEFAULT_QWEN_TTS_DEVICE = "cuda"

# Qwen3-TTS's documented native output rate for the 12Hz checkpoints. Override
# with QWEN_TTS_SAMPLE_RATE if a different checkpoint family uses another one.
DEFAULT_QWEN_TTS_SAMPLE_RATE = 24000
DEFAULT_QWEN_TTS_MP3_BIT_RATE = 128

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
        from qwen_tts import Qwen3TTS  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "The `qwen-tts` package is not installed. Install the optional "
            "`qwen` extra and the Qwen3-TTS package — see docs/QWEN_TTS.md."
        ) from exc

    dtype = torch.bfloat16 if dtype_name == "bfloat16" else None
    try:
        return Qwen3TTS.from_pretrained(model_name, device=device, torch_dtype=dtype)
    except Exception as exc:
        raise RuntimeError(
            f"Could not load Qwen3-TTS weights for {model_name!r}: {exc}. "
            "Confirm the checkpoint has been downloaded (see "
            "docs/QWEN_TTS.md) and that QWEN_TTS_MODEL names a valid "
            "Hugging Face repo id."
        ) from exc


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


def _generate_pcm_chunks(model: Any, text: str, voice: str, sample_rate: int) -> Iterator[bytes]:
    """
    Adapter over qwen_tts's streaming generation call.

    Assumed shape: `model.stream_generate(text=..., voice=..., sample_rate=...)`
    yields successive mono frames, each either raw int16 PCM bytes or an
    array-like of floats in [-1, 1] / int16 samples. This was written against
    the Qwen3-TTS repo's documented "dual-track streaming" API, not verified
    against real hardware (no CUDA GPU in this environment) — see
    docs/QWEN_TTS.md. If the installed qwen-tts version's API differs, this
    is the only function that needs to change.
    """
    import numpy as np

    for piece in model.stream_generate(text=text, voice=voice, sample_rate=sample_rate):
        if isinstance(piece, (bytes, bytearray)):
            yield bytes(piece)
            continue
        arr = np.asarray(piece)
        if arr.dtype != np.int16:
            arr = (np.clip(arr, -1.0, 1.0) * 32767.0).astype(np.int16)
        yield arr.tobytes()


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
        self.device = (os.getenv("QWEN_TTS_DEVICE") or DEFAULT_QWEN_TTS_DEVICE).strip().lower()
        self.sample_rate = int(os.getenv("QWEN_TTS_SAMPLE_RATE") or DEFAULT_QWEN_TTS_SAMPLE_RATE)
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
            f"device {self.device}"
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
        unused — chunks here are whatever the model/encoder produce as they
        are generated, the same streaming-as-you-go behavior as the other
        providers, just not sliced to a fixed byte size.
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
        encoder = _mp3_encoder(self.sample_rate, self.bit_rate)

        total_bytes = 0
        n_chunks = 0
        first_byte_marked = False

        with _model_lock:
            for pcm_chunk in _generate_pcm_chunks(model, text, self.voice, self.sample_rate):
                mp3_bytes = bytes(encoder.encode(pcm_chunk))
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
