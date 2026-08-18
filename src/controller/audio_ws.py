"""
Shared audio plumbing for the two WebSocket controllers.

Both the assistant socket and the meeting socket transcribe on the same single
GPU, so they must serialize against the *same* lock object — two controllers
each holding their own would be no lock at all.

The lock is priority-aware because the two callers do not deserve equal
treatment. A meeting window is background work that can wait a cycle; a person
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


def suffix_for_mime(mime_type: str) -> str:
    mime = (mime_type or "").lower()
    if "wav" in mime:
        return ".wav"
    if "ogg" in mime:
        return ".ogg"
    if "mp4" in mime or "mpeg" in mime:
        return ".mp4"
    return ".webm"


def transcribe_serialized(file_path: Path, language: str | None) -> str:
    """Flat transcription for an assistant turn. Takes priority on the GPU."""
    with asr_lock.priority():
        return asr_service.transcribe_file_path(file_path, language)


def transcribe_segments_serialized(
    audio, language: str | None, priority: bool = False
) -> list[TranscriptSegment]:
    """Timed transcription, used by meeting capture. Yields to spoken turns."""
    guard = asr_lock.priority() if priority else asr_lock.background()
    with guard:
        return asr_service.transcribe_segments(audio, language)
