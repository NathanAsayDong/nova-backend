"""
Shared audio plumbing for the two WebSocket controllers.

Both the assistant socket and the meeting socket transcribe on the same single
GPU, so they must serialize against the *same* lock object — two controllers
each holding their own would be no lock at all.

The lock is priority-aware because the two callers do not deserve equal
treatment. A meeting window (or a sidekick utterance) is background work that can wait a cycle; a person
who just finished speaking is waiting for an answer. Background callers check
`priority_pending` and stand aside rather than making a spoken turn queue
behind thirty seconds of meeting audio.
"""

import threading
from contextlib import contextmanager
from pathlib import Path

from src.service.asr_service import ASRService, TranscriptSegment

# One model, one process. Both sockets share this instance.
asr_service = ASRService()


class AsrLock:
    """A mutex that lets background work notice it is in someone's way."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._waiters_lock = threading.Lock()
        self._priority_waiters = 0

    @property
    def priority_pending(self) -> bool:
        """True while a latency-sensitive caller is waiting or about to wait."""
        with self._waiters_lock:
            return self._priority_waiters > 0

    @contextmanager
    def priority(self):
        """For work a person is waiting on: assistant turns, wake checks."""
        with self._waiters_lock:
            self._priority_waiters += 1
        try:
            with self._lock:
                yield
        finally:
            with self._waiters_lock:
                self._priority_waiters -= 1

    @contextmanager
    def background(self):
        """For work that can wait: meeting windows."""
        with self._lock:
            yield


asr_lock = AsrLock()


PCM_DEFAULT_RATE = 16000


def is_raw_pcm(mime_type: str) -> bool:
    """Headerless 16-bit little-endian PCM, as a native client captures it."""
    return (mime_type or "").lower().split(";", 1)[0].strip() in (
        "audio/pcm",
        "audio/l16",
    )


def _pcm_params(mime_type: str) -> tuple[int, int]:
    """(sample rate, channels) from e.g. `audio/pcm;rate=16000;channels=1`."""
    rate, channels = PCM_DEFAULT_RATE, 1
    for part in (mime_type or "").lower().split(";")[1:]:
        key, _, value = part.partition("=")
        try:
            if key.strip() == "rate":
                rate = int(value)
            elif key.strip() == "channels":
                channels = int(value)
        except ValueError:
            continue
    return max(rate, 1), max(channels, 1)


def audio_file_bytes(mime_type: str, audio: bytes) -> bytes:
    """
    The bytes to write to disk for the decoder.

    Container formats (webm, mp4, ogg, wav) are already decodable. Raw PCM has
    no header, so it gets a WAV one sized to the buffer. Chunks can split a
    sample across frames, so a trailing odd byte is dropped.
    """
    if not is_raw_pcm(mime_type):
        return audio
    rate, channels = _pcm_params(mime_type)
    frame = 2 * channels
    audio = audio[: len(audio) - (len(audio) % frame)]
    header = (
        b"RIFF"
        + (36 + len(audio)).to_bytes(4, "little")
        + b"WAVEfmt "
        + (16).to_bytes(4, "little")
        + (1).to_bytes(2, "little")  # PCM
        + channels.to_bytes(2, "little")
        + rate.to_bytes(4, "little")
        + (rate * frame).to_bytes(4, "little")
        + frame.to_bytes(2, "little")
        + (16).to_bytes(2, "little")
        + b"data"
        + len(audio).to_bytes(4, "little")
    )
    return header + audio


def suffix_for_mime(mime_type: str) -> str:
    mime = (mime_type or "").lower()
    if is_raw_pcm(mime) or "wav" in mime:
        return ".wav"
    if "ogg" in mime:
        return ".ogg"
    if "mp4" in mime or "mpeg" in mime:
        return ".mp4"
    return ".webm"


def transcribe_serialized(
    file_path: Path,
    language: str | None,
    fast: bool = False,
    background: bool = False,
) -> str:
    """Flat transcription for an assistant turn. Takes priority on the GPU.

    `fast` is for live captions: greedy decoding, since the caption is redrawn
    a second later and the final pass decodes properly.

    `background` is for audio nobody is waiting on — sidekick's overheard
    utterances — which queues behind spoken turns instead of ahead of them.
    """
    guard = asr_lock.background() if background else asr_lock.priority()
    with guard:
        return asr_service.transcribe_file_path(file_path, language, fast=fast)


def transcribe_segments_serialized(
    audio, language: str | None, priority: bool = False
) -> list[TranscriptSegment]:
    """Timed transcription, used by meeting capture. Yields to spoken turns."""
    guard = asr_lock.priority() if priority else asr_lock.background()
    with guard:
        return asr_service.transcribe_segments(audio, language)
