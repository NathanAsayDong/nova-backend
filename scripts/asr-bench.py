"""
Compare speech-to-text engines on the same audio, side by side.

Runs each configuration in turn over a handful of clips cut from one
recording (by default the newest file in meeting_audio/), and prints every
engine's transcript of every clip, then a speed table.

The point is to judge on this machine's microphone and room rather than a
leaderboard: read the clips where the engines disagree, and the better one
is usually obvious.

Run with (hyphenated name so it can be typed anywhere):
    uv run python scripts/asr-bench.py [audio-file] [--clips N] [--seconds S]
    uv run python scripts/asr-bench.py --configs parakeet,turbo
"""

import argparse
import gc
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

# Each configuration is the env an ASRService would be started with.
CONFIGS: dict[str, dict[str, str]] = {
    # What the tower ran before this change, for the before/after comparison.
    "distil": {
        "ASR_PROVIDER": "faster_whisper",
        "WHISPER_MODEL_SIZE": "distil-large-v3",
        "WHISPER_COMPUTE_TYPE": "int8",
        "ASR_HOTWORDS": "",
    },
    "turbo": {"ASR_PROVIDER": "faster_whisper", "WHISPER_MODEL_SIZE": "large-v3-turbo"},
    "parakeet": {"ASR_PROVIDER": "parakeet"},
}


def default_audio() -> Path:
    candidates = sorted(
        (p for p in (ROOT / "meeting_audio").glob("*") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        raise SystemExit("No audio given and meeting_audio/ is empty.")
    return candidates[-1]


def cut_clips(audio_path: Path, count: int, seconds: float):
    """`count` clips of `seconds`, spread evenly over the parts that contain speech."""
    from faster_whisper.vad import VadOptions, get_speech_timestamps

    from src.service.asr_service import SAMPLE_RATE, ASRService

    print(f"decoding {audio_path.name} ...", flush=True)
    samples = ASRService.decode_audio(str(audio_path))
    total = len(samples) / SAMPLE_RATE
    print(f"  {total / 60:.1f} min of audio", flush=True)

    clip_len = int(seconds * SAMPLE_RATE)
    starts = []
    for k in range(count):
        start = int((k + 0.5) * len(samples) / count) - clip_len // 2
        start = max(0, min(start, len(samples) - clip_len))
        starts.append(start)

    clips = []
    for start in starts:
        clip = samples[start : start + clip_len]
        # Skip clips that are mostly silence; they say nothing about accuracy.
        speech = get_speech_timestamps(clip, VadOptions())
        voiced = sum(c["end"] - c["start"] for c in speech) / SAMPLE_RATE
        if voiced < seconds * 0.3:
            continue
        clips.append((start / SAMPLE_RATE, clip))
    return clips


def load(name: str):
    from src.service.asr_service import ASRService

    saved = {key: os.environ.get(key) for key in CONFIGS[name]}
    os.environ.update(CONFIGS[name])
    try:
        started = time.perf_counter()
        service = ASRService()
        return service, time.perf_counter() - started
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("audio", nargs="?", type=Path, help="recording to cut clips from")
    parser.add_argument("--clips", type=int, default=6)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--configs", default=",".join(CONFIGS))
    parser.add_argument("--width", type=int, default=160, help="truncate transcripts to this many chars")
    args = parser.parse_args()

    names = [n.strip() for n in args.configs.split(",") if n.strip()]
    unknown = [n for n in names if n not in CONFIGS]
    if unknown:
        raise SystemExit(f"unknown config(s) {unknown}; choose from {list(CONFIGS)}")

    audio_path = args.audio or default_audio()
    clips = cut_clips(audio_path, args.clips, args.seconds)
    if not clips:
        raise SystemExit("No clips with enough speech in them.")

    results: dict[str, list[str]] = {}
    timing: dict[str, tuple[float, float]] = {}
    for name in names:
        print(f"\nloading {name} ...", flush=True)
        try:
            service, load_seconds = load(name)
        except Exception as exc:  # noqa: BLE001 - report and move on to the next engine
            print(f"  {name} failed to load: {exc}")
            continue
        # One throwaway pass so CUDA kernel compilation is not billed to clip 1.
        service.transcribe_segments(clips[0][1][: 16000 * 2])
        texts, spent = [], 0.0
        for _, clip in clips:
            started = time.perf_counter()
            segments = service.transcribe_segments(clip, "en")
            spent += time.perf_counter() - started
            texts.append(" ".join(s.text for s in segments))
        results[name], timing[name] = texts, (load_seconds, spent)
        del service
        gc.collect()

    audio_seconds = len(clips) * args.seconds
    print("\n" + "=" * 80)
    for index, (offset, _) in enumerate(clips):
        print(f"\nclip {index + 1} @ {int(offset // 60)}:{int(offset % 60):02d}")
        for name, texts in results.items():
            text = texts[index]
            if len(text) > args.width:
                text = text[: args.width - 3] + "..."
            print(f"  {name:>9}: {text}")

    print("\n" + "=" * 80)
    print(f"{'engine':>9} {'load s':>7} {'asr s':>7} {'x realtime':>11}")
    for name, (load_seconds, spent) in timing.items():
        speed = audio_seconds / spent if spent else float("inf")
        print(f"{name:>9} {load_seconds:7.1f} {spent:7.2f} {speed:10.0f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
