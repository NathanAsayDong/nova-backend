import os
import time
from collections.abc import Iterator

DEFAULT_OPENAI_TTS_MODEL = "gpt-4o-mini-tts"
DEFAULT_OPENAI_TTS_VOICE = "cedar"
DEFAULT_OPENAI_TTS_FORMAT = "mp3"
OPENAI_TTS_INSTRUCTIONS = (
    "You are a refined, highly capable AI assistant. "
    "Use a British accent and a calm, confident, slightly witty delivery. "
    "Prioritize clarity and natural prosody."
)

# After the primary provider refuses a clip, how long to send lines straight to
# the fallback. A refusal is usually a plan or quota problem that will not fix
# itself between sentences, and retrying it first would add a failed round trip
# to every line Nova says.
PRIMARY_COOLDOWN_SECONDS = 600

ELEVEN_LABS_ALIASES = {"elevenlabs", "eleven-labs", "eleven_labs", "11labs", "eleven"}


def _requested_provider() -> str:
    """
    "elevenlabs" (the default) or "openai", from TTS_PROVIDER.

    TTS_MODEL=elevenlabs is still honoured, because that is how ElevenLabs used
    to be switched on; any other TTS_MODEL value names an OpenAI model and so
    implies the OpenAI provider when TTS_PROVIDER is unset.
    """
    provider = (os.getenv("TTS_PROVIDER") or "").strip().lower()
    if provider:
        return "elevenlabs" if provider in ELEVEN_LABS_ALIASES else provider

    legacy_model = (os.getenv("TTS_MODEL") or "").strip().lower()
    if legacy_model and legacy_model not in ELEVEN_LABS_ALIASES:
        return "openai"
    return "elevenlabs"


class OpenAITTS:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_APIKEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        model = (os.getenv("TTS_MODEL") or "").strip()
        self.model = (
            model
            if model and model.lower() not in ELEVEN_LABS_ALIASES
            else DEFAULT_OPENAI_TTS_MODEL
        )
        self.voice = DEFAULT_OPENAI_TTS_VOICE
        self.response_format = DEFAULT_OPENAI_TTS_FORMAT

    def stream_text_to_speech(
        self, text: str, chunk_size: int = 4096, previous_text: str | None = None
    ) -> Iterator[bytes]:
        with self.client.audio.speech.with_streaming_response.create(
            model=self.model,
            voice=self.voice,
            input=text,
            response_format=self.response_format,
            stream_format="audio",
            instructions=OPENAI_TTS_INSTRUCTIONS,
        ) as response:
            for audio_chunk in response.iter_bytes(chunk_size=chunk_size):
                if audio_chunk:
                    yield audio_chunk

    def output_mime_type(self) -> str:
        return "audio/mpeg"


class TTSService:
    """
    Nova's voice. ElevenLabs by default, OpenAI as the fallback.

    The fallback matters because the voice is the whole interface on a voice
    turn: if ElevenLabs refuses a clip (plan lapsed, quota spent, network
    blip) before any audio has gone out, the same line is spoken through
    OpenAI rather than Nova going silent. Both produce MP3, so the client
    never knows. Once ElevenLabs has started streaming a clip, a failure is
    raised as before — splicing a second voice into half a sentence is worse
    than stopping.
    """

    def __init__(self) -> None:
        self.primary = None
        self.fallback = None
        self._primary_down_until = 0.0

        if _requested_provider() == "openai":
            self.primary = OpenAITTS()
        else:
            try:
                from src.service.eleven_labs_service import ElevenLabsService

                self.primary = ElevenLabsService()
            except ValueError as exc:
                print(f"ElevenLabs TTS unavailable ({exc}); using OpenAI TTS.")
                self.primary = OpenAITTS()
            else:
                try:
                    self.fallback = OpenAITTS()
                except RuntimeError:
                    self.fallback = None

        self.provider = "openai" if isinstance(self.primary, OpenAITTS) else "elevenlabs"
        print(f"TTS provider: {self.provider}" + (" (OpenAI fallback)" if self.fallback else ""))

    def stream_text_to_speech(
        self, text: str, chunk_size: int = 4096, previous_text: str | None = None
    ) -> Iterator[bytes]:
        if self.fallback is not None and time.monotonic() < self._primary_down_until:
            yield from self.fallback.stream_text_to_speech(text, chunk_size=chunk_size)
            return

        chunks = self.primary.stream_text_to_speech(
            text, chunk_size=chunk_size, previous_text=previous_text
        )
        try:
            first = next(chunks, None)
        except Exception as exc:
            if self.fallback is None:
                raise
            self._primary_down_until = time.monotonic() + PRIMARY_COOLDOWN_SECONDS
            print(
                f"{self.provider} TTS failed; using OpenAI for the next "
                f"{PRIMARY_COOLDOWN_SECONDS // 60} minutes: {exc}"
            )
            yield from self.fallback.stream_text_to_speech(text, chunk_size=chunk_size)
            return

        if first is not None:
            yield first
        yield from chunks

    def text_to_speech(self, text: str) -> tuple[bytes, str]:
        audio_bytes = b"".join(self.stream_text_to_speech(text))
        return audio_bytes, self.output_mime_type()

    def output_mime_type(self) -> str:
        return self.primary.output_mime_type()
