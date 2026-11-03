from collections.abc import Iterator
import os
import time
import requests

from src.harness.turn_timer import TurnTimer, mark as _mark_timing

# Sonic is Cartesia's low-latency TTS model family, the Cartesia equivalent of
# ElevenLabs' Flash model: built for sentence-by-sentence speech rather than
# one long narration. "sonic-3" is the current generation (also the first to
# support generation_config.emotion, see CARTESIA_EMOTION below); override
# with CARTESIA_MODEL_ID for an older/newer one (e.g. "sonic-3.6").
DEFAULT_CARTESIA_MODEL_ID = "sonic-3"

# A public library voice from Cartesia's own docs/playground ("Brooke"),
# present on every account, so the service still starts without a voice
# picked out yet. Set CARTESIA_VOICE_ID to Nova's own voice once one exists.
DEFAULT_CARTESIA_VOICE_ID = "694f9389-aac1-45b6-b726-9d9369183238"

# Cartesia versions its API by request date, not a semver header; this is the
# current version per Cartesia's docs as of 2026-11-03. Override with
# CARTESIA_API_VERSION if Cartesia ships a breaking change and an even newer
# snapshot is needed.
DEFAULT_CARTESIA_API_VERSION = "2026-08-14"
DEFAULT_CARTESIA_LANGUAGE = "en"

# generation_config.emotion, sonic-3 and newer only. Cartesia's predefined
# list includes at least neutral/calm/angry/content/sad/scared; Nova only
# exposes the two that make sense for an assistant's voice. "content" is a
# steady, unremarkable delivery — the right default for most replies —
# "excited" is for lines that call for it. CARTESIA_EMOTION is validated
# against exactly these two; anything else (typo, unset, a value from a
# model generation that doesn't support it) falls back to "content" rather
# than sending something Cartesia might reject.
CARTESIA_EMOTION_CHOICES = {"content", "excited"}
DEFAULT_CARTESIA_EMOTION = "content"

# mp3, so the rest of the pipeline (chunked over the voice websocket, decoded
# client-side) sees the same container as ElevenLabs and OpenAI and neither
# the server nor the iOS/web clients need to know which provider spoke.
DEFAULT_CARTESIA_SAMPLE_RATE = 44100
DEFAULT_CARTESIA_BIT_RATE = 128000

# Connect fast or fail fast (so the caller can fall through to the next
# provider); once connected, a long clip may take a while to finish streaming.
REQUEST_TIMEOUT_SECONDS = (5, 30)


class CartesiaService:
    """
    Cartesia Sonic TTS, streamed over HTTP the same way ElevenLabsService
    streams — one request per line, chunked response body — so it can slot
    into TTSService's fallback chain without any special-casing.

    Uses Cartesia's `/tts/bytes` endpoint rather than its websocket API:
    the websocket protocol exists mainly to support `context_id`-chained
    turns within one connection, which only pays off when many lines are
    sent back-to-back over a single open socket. Nova already opens and
    closes one HTTP request per spoken line (matching the ElevenLabs path),
    so the simpler request/response endpoint gets the same latency without
    a second connection-lifecycle to manage.
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("CARTESIA_API_KEY")
        if not self.api_key:
            raise ValueError("CARTESIA_API_KEY is not set")

        self.voice_id = os.getenv("CARTESIA_VOICE_ID") or DEFAULT_CARTESIA_VOICE_ID
        self.model_id = os.getenv("CARTESIA_MODEL_ID") or DEFAULT_CARTESIA_MODEL_ID
        self.api_version = os.getenv("CARTESIA_API_VERSION") or DEFAULT_CARTESIA_API_VERSION
        self.language = os.getenv("CARTESIA_LANGUAGE") or DEFAULT_CARTESIA_LANGUAGE
        self.sample_rate = DEFAULT_CARTESIA_SAMPLE_RATE
        self.bit_rate = DEFAULT_CARTESIA_BIT_RATE

        requested_emotion = (os.getenv("CARTESIA_EMOTION") or "").strip().lower()
        self.emotion = (
            requested_emotion if requested_emotion in CARTESIA_EMOTION_CHOICES
            else DEFAULT_CARTESIA_EMOTION
        )

        # One pooled connection for every clip, same reasoning as
        # ElevenLabsService: a fresh request per sentence would pay a TCP +
        # TLS handshake to api.cartesia.ai each time.
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-API-Key": self.api_key,
                "Cartesia-Version": self.api_version,
                "Content-Type": "application/json",
            }
        )

        print(
            f"Cartesia TTS: model {self.model_id}, voice id {self.voice_id}, "
            f"emotion {self.emotion}"
        )

    def stream_text_to_speech(
        self,
        text: str,
        chunk_size: int = 4096,
        previous_text: str | None = None,
        timer: "TurnTimer | None" = None,
    ) -> Iterator[bytes]:
        """
        Stream `text` as MP3 chunks.

        `previous_text` is accepted for interface parity with
        ElevenLabsService but unused: carrying intonation across sentences
        needs Cartesia's websocket API and a shared `context_id`, which the
        one-request-per-line `/tts/bytes` endpoint has no equivalent for.
        Each line is synthesized on its own, the same as the OpenAI fallback.
        """
        url = "https://api.cartesia.ai/tts/bytes"
        body = {
            "model_id": self.model_id,
            "transcript": text,
            "voice": {"mode": "id", "id": self.voice_id},
            "language": self.language,
            "output_format": {
                "container": "mp3",
                "sample_rate": self.sample_rate,
                "bit_rate": self.bit_rate,
            },
            "generation_config": {
                "emotion": self.emotion,
            },
        }

        _mark_timing(
            timer,
            "tts_request_sent",
            provider="cartesia",
            model=self.model_id,
            chars=len(text),
        )
        request_started_at = time.monotonic()
        total_bytes = 0
        n_chunks = 0
        response = self.session.post(
            url,
            json=body,
            stream=True,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        with response:
            if not response.ok:
                raise RuntimeError(_describe_failure(response, self.voice_id))
            first_byte_marked = False
            for chunk in response.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                total_bytes += len(chunk)
                n_chunks += 1
                if not first_byte_marked:
                    first_byte_marked = True
                    _mark_timing(
                        timer,
                        "first_tts_byte",
                        provider="cartesia",
                        wait_ms=round((time.monotonic() - request_started_at) * 1000),
                    )
                yield chunk
            _mark_timing(
                timer,
                "tts_done",
                provider="cartesia",
                chars=len(text),
                bytes=total_bytes,
                chunks=n_chunks,
                total_ms=round((time.monotonic() - request_started_at) * 1000),
            )

    def text_to_speech(self, text: str) -> tuple[bytes, str]:
        audio_bytes = b"".join(self.stream_text_to_speech(text))
        return audio_bytes, self.output_mime_type()

    def output_mime_type(self) -> str:
        # mp3 container requested above, same as ElevenLabsService.
        return "audio/mpeg"


def _describe_failure(response: requests.Response, voice_id: str) -> str:
    """An error message that says what to fix, not just the status code."""
    try:
        body = response.text[:1000]
    except Exception:
        body = "<unreadable body>"

    hint = "Check CARTESIA_API_KEY / CARTESIA_VOICE_ID."
    if response.status_code in (401, 403):
        hint = "CARTESIA_API_KEY looks invalid or lacks TTS access."
    elif response.status_code == 429:
        hint = "Cartesia rate limit or credit balance exceeded for this account."
    elif response.status_code == 404:
        hint = f"Voice {voice_id} was not found on this Cartesia account."

    return f"Cartesia TTS failed ({response.status_code}). {hint} Response: {body}"
