import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

import requests

if TYPE_CHECKING:
    import numpy as np

ELEVEN_LABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
DEFAULT_ELEVEN_LABS_STT_MODEL_ID = "scribe_v2"
DEFAULT_WHISPER_MODEL_SIZE = "distil-large-v3" #NOTE: Options are base, and distil-large-v3
DEFAULT_COMPUTE_TYPE = "int8"
DEFAULT_MLX_WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"

SAMPLE_RATE = 16000


@dataclass(frozen=True)
class TranscriptSegment:
    """A span of transcript, timed in seconds from the start of the audio given."""

    start: float
    end: float
    text: str

    def shifted(self, seconds: float) -> "TranscriptSegment":
        """Same segment expressed relative to a different origin."""
        return TranscriptSegment(
            start=self.start + seconds, end=self.end + seconds, text=self.text
        )


def _platform_default_provider() -> str:
    """Best local provider for the machine this process is running on."""
    if sys.platform == "darwin" and platform.machine() == "arm64":
        return "mlx_whisper"  # Apple Silicon GPU via MLX
    return "faster_whisper"  # CTranslate2 picks CUDA when available, else CPU


# CTranslate2 4.x is built against CUDA 12 and cuDNN 9 and requests these by
# bare name the first time it uses the GPU.
_REQUIRED_CUDA_DLLS = ("cublas64_12.dll", "cudnn64_9.dll")

# Preload order matters: cuBLAS depends on cuBLASLt, cuDNN on both.
_CUDA_DLL_PATTERNS = ("cublasLt64_*.dll", "cublas64_*.dll", "cudnn64_*.dll")

_cuda_setup: dict | None = None


def _nvidia_wheel_dll_dirs() -> list[Path]:
    """DLL directories inside the installed nvidia-*-cu12 wheels, if any."""
    try:
        import nvidia
    except ImportError:
        return []  # wheels not installed
    dirs: list[Path] = []
    for base in nvidia.__path__:
        for candidate in sorted(Path(base).glob("*/bin")):
            if any(candidate.glob("*.dll")):
                dirs.append(candidate)
    return dirs


def _setup_cuda_libraries() -> dict:
    """
    Make the pip-installed CUDA libraries usable by CTranslate2 on Windows.

    The nvidia-cublas-cu12 / nvidia-cudnn-cu12 wheels keep their DLLs in
    site-packages/nvidia/*/bin, a directory Windows does not search. Adding it
    to the search path is not enough on its own, because CTranslate2 asks for
    cuBLAS by bare name and Python 3.8+ dropped PATH from DLL resolution, so
    each library is also loaded here by absolute path: Windows resolves a later
    request for the same base name to the module already in the process, which
    sidesteps the search path entirely.

    Runs once per process; the returned report drives the device choice and
    scripts/check_asr_env.py.
    """
    global _cuda_setup
    if _cuda_setup is not None:
        return _cuda_setup

    report: dict = {"wheel_dirs": [], "preloaded": [], "unloadable": {}}
    if sys.platform != "win32":
        _cuda_setup = report
        return report

    import ctypes

    for directory in _nvidia_wheel_dll_dirs():
        os.add_dll_directory(str(directory))  # so each DLL can find its siblings
        report["wheel_dirs"].append(str(directory))

    for directory in report["wheel_dirs"]:
        for pattern in _CUDA_DLL_PATTERNS:
            for dll in sorted(Path(directory).glob(pattern)):
                try:
                    ctypes.WinDLL(str(dll))
                    report["preloaded"].append(dll.name)
                except OSError as exc:
                    report["unloadable"][dll.name] = str(exc)

    _cuda_setup = report
    return report


def missing_cuda_libraries() -> list[str]:
    """CUDA libraries CTranslate2 needs that cannot be loaded the way it asks."""
    if sys.platform != "win32":
        return []
    import ctypes

    missing = []
    for name in _REQUIRED_CUDA_DLLS:
        try:
            ctypes.WinDLL(name)
        except OSError:
            missing.append(name)
    return missing


def _resolve_whisper_device() -> tuple[str, str]:
    """
    Pick the CTranslate2 device and precision for this machine.

    "auto" resolves to CUDA only when the GPU will really work — a device is
    visible and the CUDA libraries load. Anything short of that falls back to
    CPU, because a model built on a GPU it cannot use fails at inference time
    instead of at startup, which shows up as every transcription failing.
    """
    import ctranslate2

    requested = (os.getenv("WHISPER_DEVICE") or "auto").strip().lower()
    compute_type = (os.getenv("WHISPER_COMPUTE_TYPE") or DEFAULT_COMPUTE_TYPE).strip()
    device = requested

    if requested in ("auto", "cuda"):
        _setup_cuda_libraries()
        if ctranslate2.get_cuda_device_count() < 1:
            if requested == "cuda":
                print("[asr] WHISPER_DEVICE=cuda but no CUDA device is visible; using CPU.")
            device = "cpu"
        elif missing := missing_cuda_libraries():
            print(
                f"[asr] CUDA GPU found, but {', '.join(missing)} could not be loaded; "
                "using CPU. Run `uv sync` to install the NVIDIA library wheels, "
                "and check that your NVIDIA driver is up to date."
            )
            device = "cpu"
        else:
            device = "cuda"

    # int8 keeps memory low and is supported everywhere; a device that cannot do
    # the requested precision would otherwise fail when the model is built.
    try:
        supported = ctranslate2.get_supported_compute_types(device)
    except Exception:  # noqa: BLE001 - never block startup on a capability probe
        supported = set()
    if supported and compute_type not in supported:
        fallback = "int8" if "int8" in supported else "float32"
        print(
            f"[asr] compute type '{compute_type}' is unsupported on {device}; "
            f"using '{fallback}'."
        )
        compute_type = fallback

    return device, compute_type


class ASRService:
    """Speech-to-text with switchable providers.

    Providers:
        - "auto" (default): "mlx_whisper" on Apple Silicon Macs, otherwise
          "faster_whisper" (which itself uses CUDA when available, else CPU),
          so the same .env works on macOS and Windows/Linux machines.
        - "mlx_whisper": runs locally on the Apple Silicon GPU via MLX,
          with Silero VAD pre-filtering to suppress hallucinations on silence.
        - "faster_whisper": runs locally via CTranslate2 (CUDA or CPU), no
          ffmpeg needed. Tune with WHISPER_DEVICE ("auto"/"cuda"/"cpu") and
          WHISPER_COMPUTE_TYPE ("int8"/"float16"/...).
        - "elevenlabs": ElevenLabs Scribe API. Scribe has no downloadable weights,
          so this provider requires ELEVEN_LABS_API_KEY and internet access.

    Select with the ASR_PROVIDER env var or the `provider` constructor arg.
    """

    def __init__(self, provider: str | None = None) -> None:
        self.provider = (provider or os.getenv("ASR_PROVIDER") or "auto").strip().lower()
        if self.provider == "auto":
            self.provider = _platform_default_provider()
        if self.provider not in ("mlx_whisper", "faster_whisper", "elevenlabs"):
            raise ValueError(
                f"Unknown ASR provider '{self.provider}'. "
                "Expected 'auto', 'mlx_whisper', 'faster_whisper', or 'elevenlabs'."
            )

        if self.provider == "mlx_whisper":
            import mlx_whisper  # fail fast at startup if the dependency is missing

            self.mlx_model_repo = os.getenv("MLX_WHISPER_MODEL", DEFAULT_MLX_WHISPER_MODEL)
        elif self.provider == "elevenlabs":
            self.eleven_labs_api_key = os.getenv("ELEVEN_LABS_API_KEY") or os.getenv("ELEVEN_LABS_API")
            if not self.eleven_labs_api_key:
                raise ValueError("ELEVEN_LABS_API_KEY is not set")
            self.eleven_labs_model_id = os.getenv(
                "ELEVEN_LABS_STT_MODEL_ID", DEFAULT_ELEVEN_LABS_STT_MODEL_ID
            )
        else:
            from faster_whisper import WhisperModel

            model_size = os.getenv("WHISPER_MODEL_SIZE", DEFAULT_WHISPER_MODEL_SIZE)
            device, compute_type = _resolve_whisper_device()
            print(f"[asr] faster-whisper on {device} ({compute_type}), model {model_size}")
            self.whisper = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe_file_path(self, file_path: str | Path, language: str | None = None) -> str:
        if self.provider == "elevenlabs":
            with open(file_path, "rb") as audio:
                return self._transcribe_eleven_labs(audio, language)
        if self.provider == "mlx_whisper":
            return self._transcribe_mlx(str(file_path), language)
        return self._transcribe_whisper(str(file_path), language)

    def transcribe(self, file: BinaryIO, language: str | None = None) -> str:
        # Accepts raw binary streams and FastAPI UploadFile objects (which wrap the stream in .file)
        audio = getattr(file, "file", file)
        if self.provider == "elevenlabs":
            return self._transcribe_eleven_labs(audio, language)
        if self.provider == "mlx_whisper":
            return self._transcribe_mlx(audio, language)
        return self._transcribe_whisper(audio, language)

    # ---------- timed transcription ----------

    @staticmethod
    def decode_audio(audio: "str | Path | BinaryIO") -> "np.ndarray":
        """
        Decode anything ffmpeg-free into 16 kHz mono float32 samples.

        Exposed so callers that need the raw timeline — meeting capture slices
        the tail off a growing recording — can decode once and reuse it rather
        than handing a path to each method separately.
        """
        from faster_whisper.audio import decode_audio

        return decode_audio(audio, sampling_rate=SAMPLE_RATE)

    def transcribe_segments(
        self,
        audio: "str | Path | BinaryIO | np.ndarray",
        language: str | None = None,
    ) -> list[TranscriptSegment]:
        """
        Transcribe to timed segments rather than one flat string.

        Timestamps are relative to the start of the audio passed in and account
        for VAD trimming: the local providers transcribe speech-only audio with
        the silence removed, so raw Whisper timestamps are in *trimmed* time and
        would drift further out of true with every silent gap. They are mapped
        back before returning.
        """
        if self.provider == "elevenlabs":
            return self._segments_eleven_labs(audio, language)
        if self.provider == "mlx_whisper":
            return self._segments_mlx(audio, language)
        return self._segments_whisper(audio, language)

    def _segments_mlx(
        self, audio: "str | Path | BinaryIO | np.ndarray", language: str | None
    ) -> list[TranscriptSegment]:
        import mlx_whisper
        import numpy as np
        from faster_whisper.vad import (
            SpeechTimestampsMap,
            VadOptions,
            collect_chunks,
            get_speech_timestamps,
        )

        samples = audio if isinstance(audio, np.ndarray) else self.decode_audio(audio)
        speech_chunks = get_speech_timestamps(samples, VadOptions())
        if not speech_chunks:
            return []
        audio_chunks, _ = collect_chunks(samples, speech_chunks)
        trimmed = np.concatenate(audio_chunks)

        result = mlx_whisper.transcribe(
            trimmed,
            path_or_hf_repo=self.mlx_model_repo,
            language=language,
            condition_on_previous_text=False,
        )

        # Undo the VAD trimming so the times mean something to the caller.
        timestamps = SpeechTimestampsMap(speech_chunks, SAMPLE_RATE)
        segments: list[TranscriptSegment] = []
        for raw in result.get("segments") or []:
            text = (raw.get("text") or "").strip()
            if not text:
                continue
            segments.append(
                TranscriptSegment(
                    start=timestamps.get_original_time(float(raw.get("start", 0.0))),
                    end=timestamps.get_original_time(
                        float(raw.get("end", 0.0)), is_end=True
                    ),
                    text=text,
                )
            )
        return segments

    def _segments_whisper(
        self, audio: "str | Path | BinaryIO | np.ndarray", language: str | None
    ) -> list[TranscriptSegment]:
        # faster-whisper restores timestamps itself when vad_filter is on, so
        # this path must NOT map them a second time.
        segments, _ = self.whisper.transcribe(
            audio, language=language, beam_size=5, vad_filter=True
        )
        return [
            TranscriptSegment(
                start=float(segment.start),
                end=float(segment.end),
                text=segment.text.strip(),
            )
            for segment in segments
            if segment.text and segment.text.strip()
        ]

    def _segments_eleven_labs(
        self, audio: "str | Path | BinaryIO | np.ndarray", language: str | None
    ) -> list[TranscriptSegment]:
        """
        Scribe returns word-level times; group them into sentence-ish segments.

        Splits on a pause longer than _WORD_GAP_SECONDS or on sentence-ending
        punctuation, which is close enough to what the local providers emit for
        the callers that consume these.
        """
        handle = audio
        opened = None
        if isinstance(audio, (str, Path)):
            opened = open(audio, "rb")
            handle = opened
        try:
            payload = self._eleven_labs_request(handle, language)
        finally:
            if opened is not None:
                opened.close()

        words = payload.get("words") or []
        if not words:
            text = (payload.get("text") or "").strip()
            return [TranscriptSegment(0.0, 0.0, text)] if text else []

        segments: list[TranscriptSegment] = []
        buffer: list[str] = []
        start = end = 0.0
        for word in words:
            if word.get("type") not in (None, "word"):
                continue
            token = (word.get("text") or "").strip()
            if not token:
                continue
            word_start = float(word.get("start", 0.0))
            word_end = float(word.get("end", word_start))
            if not buffer:
                start = word_start
            elif word_start - end > _WORD_GAP_SECONDS:
                segments.append(TranscriptSegment(start, end, " ".join(buffer)))
                buffer, start = [], word_start
            buffer.append(token)
            end = word_end
            if token.endswith((".", "?", "!")):
                segments.append(TranscriptSegment(start, end, " ".join(buffer)))
                buffer = []
        if buffer:
            segments.append(TranscriptSegment(start, end, " ".join(buffer)))
        return segments

    # ---------- flat transcription ----------

    def _transcribe_mlx(self, audio: str | BinaryIO, language: str | None) -> str:
        import mlx_whisper
        import numpy as np
        from faster_whisper.vad import VadOptions, collect_chunks, get_speech_timestamps

        # mlx_whisper has no built-in VAD and hallucinates text on silence/noise,
        # so reuse faster-whisper's bundled Silero VAD to keep only speech samples.
        samples = audio if isinstance(audio, np.ndarray) else self.decode_audio(audio)
        speech_chunks = get_speech_timestamps(samples, VadOptions())
        if not speech_chunks:
            return ""
        audio_chunks, _ = collect_chunks(samples, speech_chunks)
        samples = np.concatenate(audio_chunks)

        result = mlx_whisper.transcribe(
            samples,
            path_or_hf_repo=self.mlx_model_repo,
            language=language,
            condition_on_previous_text=False,
        )
        return (result.get("text") or "").strip()

    def _transcribe_whisper(self, audio: str | BinaryIO, language: str | None) -> str:
        segments, _ = self.whisper.transcribe(
            audio,
            language=language,
            beam_size=5,
            vad_filter=True,
        )
        # segments is a lazy generator; joining consumes it and runs the transcription
        return " ".join(segment.text.strip() for segment in segments).strip()

    def _transcribe_eleven_labs(self, audio: BinaryIO, language: str | None) -> str:
        return (self._eleven_labs_request(audio, language).get("text") or "").strip()

    def _eleven_labs_request(self, audio: BinaryIO, language: str | None) -> dict:
        data: dict[str, str] = {
            "model_id": self.eleven_labs_model_id,
            "tag_audio_events": "false",
            "diarize": "false",
        }
        if language:
            data["language_code"] = language
        response = requests.post(
            ELEVEN_LABS_STT_URL,
            headers={"xi-api-key": self.eleven_labs_api_key},
            files={"file": audio},
            data=data,
            timeout=120,
        )
        if not response.ok:
            raise RuntimeError(
                f"ElevenLabs STT failed ({response.status_code}). "
                f"Check ELEVEN_LABS_API_KEY. Response: {response.text[:1000]}"
            )
        return response.json()


# Pause long enough to read as a new sentence when the provider gives us words
# but no segment boundaries.
_WORD_GAP_SECONDS = 0.8
