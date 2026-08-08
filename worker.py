"""
Nova background worker.

Entry point for scheduled jobs that run outside the request path:

  * process_conversations - distills closed conversations into memory chunks
  * check_for_responsibilities - runs responsibilities that are due

Register further jobs by appending a ScheduledJob to build_jobs().

Run with:
    uv run python worker.py
"""

import time
from dataclasses import dataclass, field
from typing import Callable

from dotenv import load_dotenv

load_dotenv()

_TICK_SECONDS = 30.0


@dataclass
class ScheduledJob:
    name: str
    interval_seconds: float
    run: Callable[[], None]
    # 0.0 means "due immediately" — every job runs once at worker startup.
    next_run_at: float = field(default=0.0)

    def due(self, now: float) -> bool:
        return now >= self.next_run_at

    def mark_ran(self, now: float) -> None:
        self.next_run_at = now + self.interval_seconds


def _run_process_conversations() -> None:
    # Imported lazily so a bad deploy of one job's dependencies doesn't stop
    # the worker from starting, and each run gets fresh service instances.
    from src.service.memory_chunk_service import MemoryChunkService

    MemoryChunkService().process_conversations()


def _run_check_for_responsibilities() -> None:
    from src.service.responsibility_service import ResponsibilityService

    ResponsibilityService().check_for_responsibilities()


def build_jobs() -> list[ScheduledJob]:
    return [
        ScheduledJob(
            name="process_conversations",
            interval_seconds=30 * 60,
            run=_run_process_conversations,
        ),
        # Checked more often than responsibilities actually run: the service
        # decides what's due, so a short interval only means a due
        # responsibility starts soon after its window opens.
        ScheduledJob(
            name="check_for_responsibilities",
            interval_seconds=5 * 60,
            run=_run_check_for_responsibilities,
        ),
    ]


def run_worker() -> None:
    jobs = build_jobs()
    # flush so logs appear promptly when stdout is redirected to a file.
    print(f"Nova worker online. Jobs: {[job.name for job in jobs]}", flush=True)

    while True:
        now = time.monotonic()
        for job in jobs:
            if not job.due(now):
                continue
            print(f"Running job: {job.name}", flush=True)
            try:
                job.run()
            except Exception as exc:
                # A failing job must not kill the worker; it retries on its
                # next interval.
                print(f"Job '{job.name}' failed: {exc}", flush=True)
            job.mark_ran(time.monotonic())
        time.sleep(_TICK_SECONDS)


if __name__ == "__main__":
    run_worker()
