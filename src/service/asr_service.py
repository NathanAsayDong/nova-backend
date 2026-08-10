import os
from pathlib import Path
from typing import BinaryIO

import requests

ELEVEN_LABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
DEFAULT_ELEVEN_LABS_STT_MODEL_ID = "scribe_v2"
DEFAULT_WHISPER_MODEL_SIZE = "distil-large-v3" #NOTE: Options are base, and distil-large-v3
DEFAULT_MLX_WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"


class ASRService:
    """Speech-to-text with switchable providers.

    Providers:
        - "mlx_whisper" (default): runs locally on the Apple Silicon GPU via MLX,
          with Silero VAD pre-filtering to suppress hallucinations on silence.
        - "faster_whisper": runs locally on CPU via CTranslate2, no ffmpeg needed.
        - "elevenlabs": ElevenLabs Scribe API. Scribe has no downloadable weights,
          so this provider requires ELEVEN_LABS_API_KEY and internet access.

    Select with the ASR_PROVIDER env var or the `provider` constructor arg.
    """

    def __init__(self, provider: str | None = None) -> None:
        self.provider = (provider or os.getenv("ASR_PROVIDER") or "mlx_whisper").strip().lower()
        if self.provider not in ("mlx_whisper", "faster_whisper", "elevenlabs"):
            raise ValueError(
                f"Unknown ASR provider '{self.provider}'. "
                "Expected 'mlx_whisper', 'faster_whisper', or 'elevenlabs'."
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
            # int8 quantization keeps memory low; "auto" picks CUDA when available, else CPU
            self.whisper = WhisperModel(model_size, device="auto", compute_type="int8")

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

    def _transcribe_mlx(self, audio: str | BinaryIO, language: str | None) -> str:
        import mlx_whisper
        import numpy as np
        from faster_whisper.audio import decode_audio
        from faster_whisper.vad import VadOptions, collect_chunks, get_speech_timestamps

        # mlx_whisper has no built-in VAD and hallucinates text on silence/noise,
        # so reuse faster-whisper's bundled Silero VAD to keep only speech samples.
        samples = decode_audio(audio, sampling_rate=16000)
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
        return (response.json().get("text") or "").strip()
