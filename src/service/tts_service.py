import os
import time
from collections.abc import Iterator

from src.harness.turn_timer import TurnTimer, mark as _mark_timing

DEFAULT_OPENAI_TTS_MODEL = "gpt-4o-mini-tts"
DEFAULT_OPENAI_TTS_VOICE = "cedar"
DEFAULT_OPENAI_TTS_FORMAT = "mp3"
OPENAI_TTS_INSTRUCTIONS = (
    "You are a refined, highly capable AI assistant. "
    "Use a British accent and a calm, confident, slightly witty delivery. "
    "Prioritize clarity and natural prosody."
)

# Longest wait for the next bytes of an OpenAI TTS response (including the
# first ones) before the request is abandoned and retried. See OpenAITTS.
OPENAI_TTS_READ_TIMEOUT_SECONDS = 4
OPENAI_TTS_MAX_RETRIES = 3

# After a provider refuses a clip, how long to skip straight past it to the
# next one in the chain. A refusal is usually a plan or quota problem that
# will not fix itself between sentences, and retrying it first would add a
# failed round trip to every line Nova says. Each provider in the chain keeps
# its own cooldown clock (see TTSService), so one dead provider's cooldown
# never affects another's.
TTS_FALLBACK_COOLDOWN_SECONDS = 600

ELEVEN_LABS_ALIASES = {"elevenlabs", "eleven-labs", "eleven_labs", "11labs", "eleven"}


def _requested_provider() -> str:
    """
    "elevenlabs" (the default) or "openai", from TTS_PROVIDER.

    TTS_MODEL=elevenlabs is still honoured, because that is how ElevenLabs used
    to be switched on; any other TTS_MODEL value names an OpenAI model and so
    implies the OpenAI provider when TTS_PROVIDER is unset.

    "openai" is a full opt-out: every other provider (ElevenLabs, Cartesia) is
    skipped even if configured, and nothing is tried if OpenAI itself fails —
    the explicit choice of a single provider is not overridden by the chain.
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

        import httpx
        from openai import OpenAI

        # OpenAI's TTS normally starts streaming within ~1.5s, but about one
        # request in six hangs for 30s+ before sending anything (measured
        # 2026-10-20). Lines are spoken one after another, so one hung request
        # stalls every sentence behind it. Give up on a silent request after a
        # few seconds and send a fresh one, which almost always starts at once.
        self.client = OpenAI(
            api_key=api_key,
            timeout=httpx.Timeout(OPENAI_TTS_READ_TIMEOUT_SECONDS, connect=5),
            max_retries=OPENAI_TTS_MAX_RETRIES,
        )
        model = (os.getenv("TTS_MODEL") or "").strip()
        self.model = (
            model
            if model and model.lower() not in ELEVEN_LABS_ALIASES
            else DEFAULT_OPENAI_TTS_MODEL
        )
        self.voice = DEFAULT_OPENAI_TTS_VOICE
        self.response_format = DEFAULT_OPENAI_TTS_FORMAT

    def stream_text_to_speech(
        self,
        text: str,
        chunk_size: int = 4096,
        previous_text: str | None = None,
        timer: "TurnTimer | None" = None,
    ) -> Iterator[bytes]:
        _mark_timing(
            timer,
            "tts_request_sent",
            provider="openai",
            model=self.model,
            chars=len(text),
        )
        request_started_at = time.monotonic()
        first_byte_marked = False
        total_bytes = 0
        n_chunks = 0
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
                    total_bytes += len(audio_chunk)
                    n_chunks += 1
                    if not first_byte_marked:
                        first_byte_marked = True
                        _mark_timing(
                            timer,
                            "first_tts_byte",
                            provider="openai",
                            wait_ms=round((time.monotonic() - request_started_at) * 1000),
                        )
                    yield audio_chunk
        _mark_timing(
            timer,
            "tts_done",
            provider="openai",
            chars=len(text),
            bytes=total_bytes,
            chunks=n_chunks,
            total_ms=round((time.monotonic() - request_started_at) * 1000),
        )

    def output_mime_type(self) -> str:
        return "audio/mpeg"


class _ChainedProvider:
    """One link in TTSService's fallback chain: a provider plus its own,
    independent cooldown clock."""

    __slots__ = ("name", "service", "cooldown_seconds", "down_until")

    def __init__(self, name: str, service, cooldown_seconds: float) -> None:
        self.name = name
        self.service = service
        self.cooldown_seconds = cooldown_seconds
        self.down_until = 0.0


def _build_provider(name: str, factory) -> "object | None":
    """Construct a provider, or return None (with a console note) if it is
    not configured. A provider missing its API key is not an error — it is
    just absent from the chain, same as before Cartesia existed."""
    try:
        return factory()
    except (ValueError, RuntimeError) as exc:
        print(f"{name} TTS unavailable ({exc}); skipping.")
        return None


class TTSService:
    """
    Nova's voice: ElevenLabs, then Cartesia, then OpenAI.

    The fallback chain matters because the voice is the whole interface on a
    voice turn: if a provider refuses a clip (plan lapsed, quota spent,
    network blip) before any audio has gone out, the same line is spoken
    through the next provider in the chain rather than Nova going silent. All
    three produce MP3, so the client never knows. Once a provider has started
    streaming a clip, a failure is raised as before — splicing a second voice
    into half a sentence is worse than stopping.

    Each provider in the chain keeps its own cooldown: after ElevenLabs
    refuses a clip, lines go straight to Cartesia (skipping a doomed retry)
    for TTS_FALLBACK_COOLDOWN_SECONDS, but Cartesia is tried fresh on every
    line unless Cartesia has *also* failed recently. A dead Cartesia account
    therefore never adds a failed-request's worth of latency to a turn that
    only needed to fall through to it once.
    """

    def __init__(self) -> None:
        requested = _requested_provider()

        if requested == "openai":
            # Explicit opt-out: skip ElevenLabs and Cartesia entirely, and if
            # OpenAI itself is not configured, let that error propagate — the
            # user asked for exactly one provider.
            self.chain = [
                _ChainedProvider("openai", OpenAITTS(), TTS_FALLBACK_COOLDOWN_SECONDS)
            ]
        else:
            built: list[tuple[str, object]] = []

            def _eleven_labs():
                from src.service.eleven_labs_service import ElevenLabsService

                return ElevenLabsService()

            def _cartesia():
                from src.service.cartesia_service import CartesiaService

                return CartesiaService()

            for name, display_name, factory in (
                ("elevenlabs", "ElevenLabs", _eleven_labs),
                ("cartesia", "Cartesia", _cartesia),
                ("openai", "OpenAI", OpenAITTS),
            ):
                service = _build_provider(display_name, factory)
                if service is not None:
                    built.append((name, service))

            if not built:
                raise RuntimeError(
                    "No TTS provider is configured (checked ElevenLabs, Cartesia, OpenAI)."
                )

            self.chain = [
                _ChainedProvider(name, service, TTS_FALLBACK_COOLDOWN_SECONDS)
                for name, service in built
            ]

        # Back-compat surface for existing callers/tests: the active
        # (first-choice) provider, and the first thing after it to try.
        self.primary = self.chain[0].service
        self.fallback = self.chain[1].service if len(self.chain) > 1 else None
        self.provider = self.chain[0].name

        chain_names = " -> ".join(p.name for p in self.chain)
        print(f"TTS provider chain: {chain_names}")

    def stream_text_to_speech(
        self,
        text: str,
        chunk_size: int = 4096,
        previous_text: str | None = None,
        timer: "TurnTimer | None" = None,
    ) -> Iterator[bytes]:
        last_exc: Exception | None = None

        for index, link in enumerate(self.chain):
            now = time.monotonic()
            if link.down_until > now:
                _mark_timing(
                    timer,
                    "tts_provider_skipped",
                    provider=link.name,
                    cooldown=True,
                    chars=len(text),
                )
                continue

            _mark_timing(
                timer,
                "tts_provider",
                provider=link.name,
                cooldown=False,
                chars=len(text),
                attempt=index,
            )
            chunks = link.service.stream_text_to_speech(
                text, chunk_size=chunk_size, previous_text=previous_text, timer=timer
            )
            try:
                first = next(chunks, None)
            except Exception as exc:
                link.down_until = time.monotonic() + link.cooldown_seconds
                print(
                    f"{link.name} TTS failed; using the next provider for the "
                    f"next {link.cooldown_seconds // 60:.0f} minutes: {exc}"
                )
                _mark_timing(
                    timer,
                    "tts_fallback_switch",
                    from_provider=link.name,
                    reason=str(exc)[:80],
                )
                last_exc = exc
                continue

            # Reached a provider that answered: stream it. A failure from
            # here on (mid-clip) is raised, not caught — splicing a second
            # voice into a half-spoken sentence is worse than stopping.
            if first is not None:
                yield first
            yield from chunks
            return

        # Every provider in the chain is either in cooldown or just failed.
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("No TTS provider in the chain is currently available.")

    def text_to_speech(self, text: str) -> tuple[bytes, str]:
        audio_bytes = b"".join(self.stream_text_to_speech(text))
        return audio_bytes, self.output_mime_type()

    def output_mime_type(self) -> str:
        return self.chain[0].service.output_mime_type()
