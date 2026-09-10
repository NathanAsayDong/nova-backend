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

Neither of those limits used to work on a command that spawns something
long-lived. `communicate()` waits for the output pipes to close, and a pipe
closes when its LAST writer does — so a dev server inherited the pipe and held
the call for the entire timeout however hard the model tried to detach it with
`&`. Then the timeout killed the shell and orphaned the server, which kept
running and kept the port with no handle left to stop it. So: output goes to
files, every command gets its own session so a kill takes the whole tree, and
anything that is not going to exit on its own is handed to `processes` instead
of being run to a pointless timeout.

The result shape matches CommandLineService exactly. agent_loop's
`_artifact_for_tool` reads stdout / stderr / exit_code to draw the terminal
artifact, and it would quietly stop rendering if this drifted.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from . import processes

DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 120
MAX_OUTPUT_CHARS = 8_000


def _clip(text: str) -> str:
    text = text or ""
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    omitted = len(text) - MAX_OUTPUT_CHARS
    return text[:MAX_OUTPUT_CHARS] + f"\n... [truncated {omitted} characters]"


def _scratch_pair() -> tuple[Path, Path]:
    root = Path(tempfile.gettempdir()) / "nova-shell"
    root.mkdir(parents=True, exist_ok=True)
    stamp = f"{os.getpid()}-{time.time_ns()}"
    return root / f"cmd-{stamp}.out", root / f"cmd-{stamp}.err"


def _resolve_cwd(cwd: str | None, default_cwd: Path | None) -> str | None:
    target = cwd or default_cwd
    if not target:
        return None
    resolved = Path(str(target)).expanduser()
    if not resolved.is_dir():
        raise ValueError(f"Working directory does not exist on the Mac: {target}")
    return str(resolved.resolve())


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

    A command that will never finish on its own is started in the background
    and reported as such, rather than being run to a timeout it was always
    going to hit.
    """
    command = (command or "").strip()
    if not command:
        raise ValueError("A non-empty command is required.")

    directory = _resolve_cwd(cwd, default_cwd)

    mode, reason = processes.classify(command)
    if mode == "background":
        return await processes.start(command, cwd=directory, note=reason)

    timeout = int(timeout_seconds or DEFAULT_TIMEOUT_SECONDS)
    timeout = max(1, min(timeout, MAX_TIMEOUT_SECONDS))

    out_path, err_path = _scratch_pair()
    try:
        with open(out_path, "wb", buffering=0) as out, open(err_path, "wb", buffering=0) as err:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=out,
                stderr=err,
                stdin=asyncio.subprocess.DEVNULL,
                cwd=directory,
                start_new_session=True,
            )

        try:
            await asyncio.wait_for(process.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            # The whole group, not just the shell — orphaning the children is
            # how a leaked dev server used to end up holding a port forever.
            await processes.kill_tree(process)
            return {
                "host": "mac",
                "cwd": directory,
                "timed_out": True,
                "timeout_seconds": timeout,
                "exit_code": None,
                "stdout": _clip(processes.read_log(out_path)),
                "stderr": _clip(processes.read_log(err_path)),
                "note": (
                    f"Command and everything it started were killed after {timeout}s. "
                    "The output above is what it had produced by then. If this is "
                    "meant to keep running (a server, a watcher), start it with "
                    "start_mac_background_command instead of raising the timeout."
                ),
            }

        return {
            "host": "mac",
            "cwd": directory,
            "timed_out": False,
            "exit_code": process.returncode,
            "stdout": _clip(processes.read_log(out_path)),
            "stderr": _clip(processes.read_log(err_path)),
        }
    finally:
        for path in (out_path, err_path):
            try:
                os.unlink(path)
            except OSError:
                pass
