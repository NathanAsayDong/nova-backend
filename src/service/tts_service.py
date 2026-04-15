import os
from collections.abc import Iterator

DEFAULT_OPENAI_TTS_MODEL = "gpt-4o-mini-tts"
DEFAULT_OPENAI_TTS_VOICE = "cedar"
DEFAULT_OPENAI_TTS_FORMAT = "mp3"
DEFAULT_ELEVEN_LABS_OUTPUT_FORMAT = "mp3_44100_128"


class TTSService:
    def __init__(self) -> None:
        requested_model = os.getenv("TTS_MODEL") or DEFAULT_OPENAI_TTS_MODEL
        provider_hint = (requested_model or "").strip().lower()
        eleven_aliases = {"elevenlabs", "eleven-labs", "eleven_labs", "11labs", "eleven"}

        self._delegate = None
        if provider_hint in eleven_aliases:
            from src.service.eleven_labs_service import ElevenLabsService

            self._delegate = ElevenLabsService()
            self.model = provider_hint
            self.voice = "elevenlabs"
            self.response_format = DEFAULT_ELEVEN_LABS_OUTPUT_FORMAT
            return

        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_APIKEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = requested_model
        self.voice = DEFAULT_OPENAI_TTS_VOICE
        self.response_format = DEFAULT_OPENAI_TTS_FORMAT

    def _mime_type_for_format(self) -> str:
        if self._delegate is not None:
            return self._delegate.output_mime_type()

        format_to_mime = {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "opus": "audio/opus",
            "aac": "audio/aac",
            "flac": "audio/flac",
            "pcm": "audio/pcm",
        }
        return format_to_mime.get(self.response_format, "audio/mpeg")

    def stream_text_to_speech(self, text: str, chunk_size: int = 4096) -> Iterator[bytes]:
        if self._delegate is not None:
            yield from self._delegate.stream_text_to_speech(text, chunk_size=chunk_size)
            return

        with self.client.audio.speech.with_streaming_response.create(
            model=self.model,
            voice=self.voice,
            input=text,
            response_format=self.response_format,
            stream_format="audio",
            instructions=(
                "You are a refined, highly capable AI assistant. "
                "Use a British accent and a calm, confident, slightly witty delivery. "
                "Prioritize clarity and natural prosody."
            ),
        ) as response:
            for audio_chunk in response.iter_bytes(chunk_size=chunk_size):
                if audio_chunk:
                    yield audio_chunk

    def text_to_speech(self, text: str) -> tuple[bytes, str]:
        audio_bytes = b"".join(self.stream_text_to_speech(text))
        return audio_bytes, self._mime_type_for_format()

    def output_mime_type(self) -> str:
        return self._mime_type_for_format()
