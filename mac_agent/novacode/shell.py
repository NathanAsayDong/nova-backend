"""
Running a shell command on this Mac, on Nova's behalf.

Nova's `run_terminal_command` used to run on the tower, which is the wrong
machine: the repos, the toolchain, the simulators and the dev servers are all
here, and a command about Nate's code is almost always a command about
something on this laptop.

Deliberately unrestricted. There is no allowlist, no path containment and no
forbidden-command list, because this is the same trust level Nova already had
on the tower and half-measures in a shell are theatre — anything that can run
`python` can do whatever the denylist was pretending to prevent. The two
limits that remain are the ones that protect the *turn* rather than the
machine: a command cannot hang forever, and it cannot flood the model's
context.

The result shape matches CommandLineService exactly. agent_loop's
`_artifact_for_tool` reads stdout / stderr / exit_code to draw the terminal
artifact, and it would quietly stop rendering if this drifted.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 120
MAX_OUTPUT_CHARS = 8_000


def _clip(text: str) -> str:
    text = text or ""
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    omitted = len(text) - MAX_OUTPUT_CHARS
    return text[:MAX_OUTPUT_CHARS] + f"\n... [truncated {omitted} characters]"


async def run(
    command: str,
    cwd: str | None = None,
    timeout_seconds: int | None = None,
    default_cwd: Path | None = None,
) -> dict[str, Any]:
    """
    Run `command` through the shell and return the result as data.

    A non-zero exit is a result, not an exception: the model needs to see a
    failing test suite as output it can read, not as a tool error.

    `default_cwd` is where a command with no explicit directory runs. launchd
    starts this agent in mac_agent/, which would be a baffling place for
    `ls` to answer from, so the caller passes the repos root instead.
    """
    command = (command or "").strip()
    if not command:
        raise ValueError("A non-empty command is required.")

    timeout = int(timeout_seconds or DEFAULT_TIMEOUT_SECONDS)
    timeout = max(1, min(timeout, MAX_TIMEOUT_SECONDS))

    directory: str | None = None
    target = cwd or default_cwd
    if target:
        resolved = Path(str(target)).expanduser()
        if not resolved.is_dir():
            raise ValueError(f"Working directory does not exist on the Mac: {target}")
        directory = str(resolved.resolve())

    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=directory,
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        # kill() then wait() — without the wait the process is a zombie and
        # its pipes stay open, which eventually wedges the event loop.
        process.kill()
        await process.wait()
        return {
            "host": "mac",
            "cwd": directory,
            "timed_out": True,
            "timeout_seconds": timeout,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "note": f"Command was killed after {timeout}s.",
        }

    return {
        "host": "mac",
        "cwd": directory,
        "timed_out": False,
        "exit_code": process.returncode,
        "stdout": _clip(stdout.decode("utf-8", errors="replace")),
        "stderr": _clip(stderr.decode("utf-8", errors="replace")),
    }
