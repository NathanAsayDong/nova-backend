from collections.abc import Iterator
import os
import requests

DEFAULT_ELEVEN_LABS_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_ELEVEN_LABS_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_ELEVEN_LABS_OPTIMIZE_STREAMING_LATENCY = 3
DEFAULT_ELEVEN_LABS_STABILITY = 0.55
DEFAULT_ELEVEN_LABS_SIMILARITY_BOOST = 0.75
DEFAULT_ELEVEN_LABS_STYLE = 0.50
DEFAULT_ELEVEN_LABS_USE_SPEAKER_BOOST = True
DEFAULT_ELEVEN_LABS_SPEED = 1.02


class ElevenLabsService:
    def __init__(self):
        self.api_key = os.getenv("ELEVEN_LABS_API_KEY") or os.getenv("ELEVEN_LABS_API")
        if not self.api_key:
            raise ValueError("ELEVEN_LABS_API_KEY is not set")

        self.voice_id = os.getenv("ELEVEN_LABS_VOICE_ID")
        if not self.voice_id:
            raise ValueError("ELEVEN_LABS_VOICE_ID is not set")

        self.model_id = DEFAULT_ELEVEN_LABS_MODEL_ID
        self.output_format = DEFAULT_ELEVEN_LABS_OUTPUT_FORMAT
        self.optimize_streaming_latency = DEFAULT_ELEVEN_LABS_OPTIMIZE_STREAMING_LATENCY

        self.stability = DEFAULT_ELEVEN_LABS_STABILITY
        self.similarity_boost = DEFAULT_ELEVEN_LABS_SIMILARITY_BOOST
        self.style = DEFAULT_ELEVEN_LABS_STYLE
        self.use_speaker_boost = DEFAULT_ELEVEN_LABS_USE_SPEAKER_BOOST
        self.speed = DEFAULT_ELEVEN_LABS_SPEED

        print(f"Using voice id: {self.voice_id}")

    def stream_text_to_speech(self, text: str, chunk_size: int = 4096) -> Iterator[bytes]:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
        headers = {
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
            "Accept": "audio/mpeg",
        }
        data = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost,
                "style": self.style,
                "use_speaker_boost": self.use_speaker_boost,
                "speed": self.speed,
            },
        }
        params = {
            "output_format": self.output_format,
            "optimize_streaming_latency": self.optimize_streaming_latency,
        }
        response = requests.post(url, headers=headers, params=params, json=data, stream=True, timeout=60)
        if not response.ok:
            # Try to surface a helpful error without dumping huge bodies.
            body_preview = ""
            try:
                body_preview = response.text[:1000]
            except Exception:
                body_preview = "<unreadable body>"
            raise RuntimeError(
                f"ElevenLabs TTS failed ({response.status_code}). "
                f"Check ELEVEN_LABS_API_KEY / ELEVEN_LABS_VOICE_ID. "
                f"Response: {body_preview}"
            )

        yield from response.iter_content(chunk_size=chunk_size)

    def text_to_speech(self, text: str) -> tuple[bytes, str]:
        audio_bytes = b"".join(self.stream_text_to_speech(text))
        return audio_bytes, self.output_mime_type()

    def output_mime_type(self) -> str:
        # With mp3_* formats, ElevenLabs returns an MP3 stream.
        return "audio/mpeg"
