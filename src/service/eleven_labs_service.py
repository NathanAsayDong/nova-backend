from collections.abc import Iterator
import os
import time
import requests

from src.harness.turn_timer import TurnTimer, mark as _mark_timing

# Flash is ElevenLabs' low-latency model: ~150ms to first audio against ~1.3s
# for multilingual_v2 (measured from the Mac, 2026-10-11). Nova speaks a reply
# a sentence or two at a time as it is written, so that wait is paid on every
# sentence, not once per turn. Override with ELEVEN_LABS_MODEL_ID — e.g.
# eleven_turbo_v2_5 for a little more quality at ~70ms more latency.
DEFAULT_ELEVEN_LABS_MODEL_ID = "eleven_flash_v2_5"
DEFAULT_ELEVEN_LABS_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_ELEVEN_LABS_STABILITY = 0.55
DEFAULT_ELEVEN_LABS_SIMILARITY_BOOST = 0.75
DEFAULT_ELEVEN_LABS_STYLE = 0.50
DEFAULT_ELEVEN_LABS_USE_SPEAKER_BOOST = True
DEFAULT_ELEVEN_LABS_SPEED = 1.02

# Connect fast or fail fast (so the caller can fall back); once connected, a
# long clip may take a while to finish streaming.
REQUEST_TIMEOUT_SECONDS = (5, 30)

# How much of the previous line to send as context. ElevenLabs only uses it to
# shape the intonation of the start of this clip, so the tail is what matters.
MAX_PREVIOUS_TEXT_CHARS = 500


class ElevenLabsService:
    def __init__(self):
        self.api_key = os.getenv("ELEVEN_LABS_API_KEY") or os.getenv("ELEVEN_LABS_API")
        if not self.api_key:
            raise ValueError("ELEVEN_LABS_API_KEY is not set")

        self.voice_id = os.getenv("ELEVEN_LABS_VOICE_ID")
        if not self.voice_id:
            raise ValueError("ELEVEN_LABS_VOICE_ID is not set")

        self.model_id = os.getenv("ELEVEN_LABS_MODEL_ID") or DEFAULT_ELEVEN_LABS_MODEL_ID
        self.output_format = DEFAULT_ELEVEN_LABS_OUTPUT_FORMAT

        self.stability = DEFAULT_ELEVEN_LABS_STABILITY
        self.similarity_boost = DEFAULT_ELEVEN_LABS_SIMILARITY_BOOST
        self.style = DEFAULT_ELEVEN_LABS_STYLE
        self.use_speaker_boost = DEFAULT_ELEVEN_LABS_USE_SPEAKER_BOOST
        self.speed = DEFAULT_ELEVEN_LABS_SPEED

        # One pooled connection for every clip. A fresh request per sentence
        # paid a TCP + TLS handshake to api.elevenlabs.io each time.
        self.session = requests.Session()
        self.session.headers.update({"xi-api-key": self.api_key})

        print(f"ElevenLabs TTS: model {self.model_id}, voice id {self.voice_id}")

    def stream_text_to_speech(
        self,
        text: str,
        chunk_size: int = 4096,
        previous_text: str | None = None,
        timer: "TurnTimer | None" = None,
    ) -> Iterator[bytes]:
        """
        Stream `text` as MP3 chunks.

        `previous_text` is the line spoken just before this one in the same
        reply. Each sentence is its own request, and without it ElevenLabs
        reads every one as the start of a fresh utterance — the pitch resets
        and the reply sounds like a list of separate announcements.
        """
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
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
        if previous_text:
            data["previous_text"] = previous_text[-MAX_PREVIOUS_TEXT_CHARS:]

        _mark_timing(timer, "tts_request_sent", provider="elevenlabs")
        request_started_at = time.monotonic()
        response = self.session.post(
            url,
            headers={"Accept": "audio/mpeg"},
            params={"output_format": self.output_format},
            json=data,
            stream=True,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        with response:
            if not response.ok:
                raise RuntimeError(_describe_failure(response, self.voice_id))
            first_byte_marked = False
            for chunk in response.iter_content(chunk_size=chunk_size):
                if not first_byte_marked:
                    first_byte_marked = True
                    _mark_timing(
                        timer,
                        "first_tts_byte",
                        provider="elevenlabs",
                        wait_ms=round((time.monotonic() - request_started_at) * 1000),
                    )
                yield chunk

    def text_to_speech(self, text: str) -> tuple[bytes, str]:
        audio_bytes = b"".join(self.stream_text_to_speech(text))
        return audio_bytes, self.output_mime_type()

    def output_mime_type(self) -> str:
        # With mp3_* formats, ElevenLabs returns an MP3 stream.
        return "audio/mpeg"


def _describe_failure(response: requests.Response, voice_id: str) -> str:
    """An error message that says what to fix, not just the status code."""
    try:
        body = response.text[:1000]
    except Exception:
        body = "<unreadable body>"

    status = ""
    try:
        status = (response.json().get("detail") or {}).get("status") or ""
    except Exception:
        pass

    if status == "ivc_not_permitted":
        hint = (
            f"Voice {voice_id} is an instant voice clone and the ElevenLabs "
            "plan no longer includes cloned voices. Upgrade the plan or set "
            "ELEVEN_LABS_VOICE_ID to a library voice."
        )
    elif status == "quota_exceeded":
        hint = "The ElevenLabs character quota for this billing period is used up."
    else:
        hint = "Check ELEVEN_LABS_API_KEY / ELEVEN_LABS_VOICE_ID."
    return f"ElevenLabs TTS failed ({response.status_code}). {hint} Response: {body}"
