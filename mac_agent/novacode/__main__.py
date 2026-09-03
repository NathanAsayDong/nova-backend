"""
Entry point. Two modes, and the second one is why this is testable at all.

    python -m novacode run
        Connect to Nova and serve coding sessions. What launchd runs.

    python -m novacode task --repo nova-backend "add a health endpoint"
        Run one task locally and print the events to stdout. No Nova, no
        websocket, no tower — the same SessionManager driven directly, so the
        interesting half can be exercised before the other half exists.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import uuid

from .config import Config
from .link import Link
from .sessions import SessionManager


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s  %(message)s",
        stream=sys.stderr,
    )


async def _run(config: Config) -> None:
    await Link(config).run_forever()


async def _task(config: Config, repo: str, instructions: str, keep: bool) -> int:
    """Drive one session start-to-finish, printing events as they arrive."""
    done = asyncio.Event()
    failed = False

    async def sink(event: dict) -> None:
        nonlocal failed
        kind = event.get("type")
        if kind == "text":
            print(f"\n\033[1m● {event['text']}\033[0m")
        elif kind == "tool":
            artifact = event.get("artifact")
            detail = f" → {artifact['kind']}: {artifact['title']}" if artifact else ""
            print(f"  \033[2m{event['tool']}{detail}\033[0m")
        elif kind == "result":
            failed = bool(event.get("is_error"))
            print(
                f"\n\033[1mdone\033[0m  turns={event.get('num_turns')} "
                f"cost=${event.get('total_cost_usd') or 0:.4f} "
                f"stop={event.get('stop_reason')}"
            )
            if event.get("result"):
                print(event["result"])
            done.set()
        elif kind == "rate_limit":
            used = event.get("utilization") or {}
            summary = ", ".join(
                f"{k} {float(v):.0%}" for k, v in used.items() if v is not None
            )
            print(f"  \033[2mwindow: {summary or event.get('status')}\033[0m")
        elif kind == "error":
            failed = True
            print(f"\n\033[31merror ({event.get('reason')}): {event.get('detail')}\033[0m")
            done.set()
        elif kind == "started":
            print(f"branch \033[36m{event.get('branch')}\033[0m in {event.get('cwd')}")

    manager = SessionManager(config, sink)
    session_id = str(uuid.uuid4())
    await manager.start(
        session_id=session_id, repo=repo, instructions=instructions, title=instructions
    )
    await done.wait()

    session = manager.sessions.get(session_id)
    if session is not None:
        print(json.dumps(session.snapshot(), indent=2))
        if not keep:
            await manager.stop(session_id)
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="novacode", description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="mode", required=True)

    sub.add_parser("run", help="Connect to Nova and serve coding sessions.")

    task = sub.add_parser("task", help="Run one task locally and print events.")
    task.add_argument("instructions")
    task.add_argument("--repo", required=True, help="Repo name under the repos root, or a path.")
    task.add_argument(
        "--keep",
        action="store_true",
        help="Leave the session and its worktree in place when the task finishes.",
    )

    args = parser.parse_args()
    _configure_logging(args.verbose)
    config = Config.from_env()

    try:
        if args.mode == "run":
            asyncio.run(_run(config))
            return 0
        return asyncio.run(_task(config, args.repo, args.instructions, args.keep))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
