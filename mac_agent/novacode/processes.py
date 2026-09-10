"""
Long-lived commands on this Mac, supervised.

The Mac half of src/service/process_supervisor.py, and the result shapes must
stay identical: agent_loop draws the same terminal artifact whichever host ran
the command, and shell.py's docstring already warns what happens when the two
drift.

The reasoning is the same as on the tower. A dev server never exits, so
waiting for it is waiting forever; `communicate()` waits on pipes, and a pipe
closes when its LAST writer closes it, so a server that inherited the pipe
held the tool for the whole timeout even after "detaching" with `&`. Killing
the shell then orphaned the server, which kept running and kept the port,
invisible to Nova. Here: log files instead of pipes, a session per command so
a kill takes the whole tree, and a registry that outlives the request.

Simpler than the tower's copy in one respect — this only ever runs on macOS,
so there are no Windows branches. Deliberately unrestricted in the same way
shell.py is: the limits protect the turn, not the machine.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import signal
import time
import uuid
from pathlib import Path
from typing import Any

MAX_OUTPUT_CHARS = 8_000
DEFAULT_READY_TIMEOUT = 20
MAX_READY_TIMEOUT = 120
# How long to watch a process with no readiness check before calling it
# started. Not zero, because the most common way a server "starts" is to die
# on an import error and the crash is worth catching; not the full timeout
# either, because with nothing to wait FOR there is nothing to learn by
# waiting — that is 20 wasted seconds in the middle of a turn.
CRASH_GRACE_SECONDS = 1.5

LOG_ROOT = Path.home() / ".nova" / "processes"

# Handles for processes this agent started. Module-level, because link.py
# calls into here as a module and each command arrives on its own task — a
# registry on an instance would not survive the request that created it.
_LIVE: dict[str, dict[str, Any]] = {}


# --------------------------------------------------------------------------
# recognising a command that will never finish
# --------------------------------------------------------------------------

_LONG_LIVED = re.compile(
    r"""(?:^|[;&|]\s*|\s)(?:
          uvicorn\b
        | gunicorn\b
        | hypercorn\b
        | daphne\b
        | fastapi\s+(?:dev|run)\b
        | flask\s+run\b
        | manage\.py\s+runserver\b
        | (?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:dev|start|serve|watch|storybook)\b
        | (?:next|nuxt|vite|astro|remix)\s+dev\b
        | webpack(?:-dev-server)?\s+serve\b
        | ng\s+serve\b
        | rails\s+s(?:erver)?\b
        | php\s+-S\b
        | http-server\b
        | python3?\s+-m\s+http\.server\b
        | ngrok\b
        | expo\s+start\b
        | tail\s+-[a-zA-Z]*f
        | docker\s+compose\s+up(?!\s+(?:-d|--detach))
        | docker-compose\s+up(?!\s+(?:-d|--detach))
        | (?:python3?|uv\s+run|poetry\s+run|pipenv\s+run)\s+(?:\S+\s+)*?main\.py\b
    )""",
    re.VERBOSE | re.IGNORECASE,
)

# Checked before the patterns above: a program name is as likely to be an
# argument as a command. `grep -n uvicorn main.py` names two triggers and
# finishes instantly. `tail` is absent on purpose — `tail -f` is the one
# inspector that really does run forever.
_INSPECTORS = re.compile(
    r"""^\s*(?:cat|bat|grep|rg|ag|less|more|head|wc|ls|find|fd|which|type|echo
        |sed|awk|git|stat|du|diff|file|open|code|vim|nano|printf|test)\b""",
    re.VERBOSE | re.IGNORECASE,
)

_TRAILING_AMPERSAND = re.compile(r"&\s*$")
# `start` at the beginning of any command SEGMENT, not just the string. The
# command that prompted all of this was `cd C:\...\nova-backend && start uv run
# main.py`, where the anchored version matched nothing and left `start` in the
# command — which on the Mac is not even a program, and on Windows opens a
# console whose output nobody ever sees.
_WINDOWS_START = re.compile(
    r"(^|&&|\|\||;|\||&)(\s*)start\s+(?:/\w+\s+)*", re.IGNORECASE
)


def classify(command: str) -> tuple[str, str | None]:
    """
    Whether `command` should run in the foreground, and why if not.

    The note is prose Nova can pass straight into the transcript. The model
    learns the rule from being told once, in the result, far faster than from
    a tool description it half-read.
    """
    text = (command or "").strip()
    if not text:
        return "foreground", None

    if _TRAILING_AMPERSAND.search(text):
        return "background", (
            "The trailing '&' was dropped and this was started as a supervised "
            "background process instead. Backgrounding inside the shell does not "
            "detach anything from this tool: the child inherits the output stream "
            "and the call would have blocked until the timeout anyway."
        )
    if _WINDOWS_START.search(text):
        return "background", (
            "The 'start' prefix was dropped and this was started as a supervised "
            "background process instead — and note that 'start' is a Windows "
            "builtin that does not exist on this Mac."
        )
    if _INSPECTORS.match(text):
        return "foreground", None
    if _LONG_LIVED.search(text):
        return "background", (
            "This looks like a long-lived process (a server, a watcher) rather "
            "than a command that finishes, so it was started in the background. "
            "Read its output with check_mac_background_command; stop it with "
            "stop_mac_background_command when you are done."
        )
    return "foreground", None


def strip_detach_syntax(command: str) -> str:
    text = (command or "").strip()
    text = _WINDOWS_START.sub(r"\1\2", text).strip()
    text = _TRAILING_AMPERSAND.sub("", text).strip()
    return text


# --------------------------------------------------------------------------
# process groups and logs
# --------------------------------------------------------------------------


def _log_paths(process_id: str) -> tuple[Path, Path]:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    return LOG_ROOT / f"{process_id}.log", LOG_ROOT / f"{process_id}.json"


def read_log(path: str | Path, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    """
    The tail of a log file.

    The tail, not the head: for a server the interesting part is the most
    recent traceback or request, while the first 8000 characters are a startup
    banner.
    """
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    return f"... [earlier {omitted} characters omitted]\n" + text[-max_chars:]


def pid_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


async def kill_tree(process: Any | None, pid: int | None = None) -> None:
    """
    Kill a process and everything it started, then reap it.

    SIGTERM to the whole group first so a server gets to shut down cleanly,
    SIGKILL if it will not. Reaping is not optional: an unwaited child keeps
    its pipes open, and a zombie eventually wedges this event loop.
    """
    pid = pid if pid is not None else (process.pid if process else None)
    if pid is None:
        return

    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(os.getpgid(pid), sig)
        except (ProcessLookupError, PermissionError):
            break
        if process is not None:
            try:
                await asyncio.wait_for(process.wait(), timeout=3)
                return
            except asyncio.TimeoutError:
                continue
        else:
            await asyncio.sleep(0.3)
            if not pid_alive(pid):
                return

    if process is not None:
        try:
            await asyncio.wait_for(process.wait(), timeout=3)
        except asyncio.TimeoutError:
            pass


# --------------------------------------------------------------------------
# readiness
# --------------------------------------------------------------------------


async def port_open(port: int, host: str = "127.0.0.1") -> bool:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, int(port)), timeout=0.5
        )
    except (OSError, asyncio.TimeoutError):
        return False
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        pass
    return True


async def await_ready(
    process: Any,
    log_path: Path,
    wait_for_port: int | None,
    wait_for_log: str | None,
    timeout: int,
) -> dict[str, Any]:
    """
    Wait until the process is demonstrably up, has died, or the wait expires.

    An early exit is the most valuable outcome here: a server that dies on
    import should be reported as a crash with its traceback, not as a healthy
    background process that the next request will fail against.
    """
    pattern = re.compile(wait_for_log) if wait_for_log else None
    has_signal = bool(wait_for_port or pattern is not None)
    limit = timeout if has_signal else min(timeout, CRASH_GRACE_SECONDS)
    deadline = time.monotonic() + max(0, limit)

    while time.monotonic() < deadline:
        if process.returncode is not None:
            return {
                "ready": False,
                "ready_reason": f"The process exited early with code {process.returncode}.",
                "exited": True,
            }
        if wait_for_port and await port_open(wait_for_port):
            return {
                "ready": True,
                "ready_reason": f"Port {wait_for_port} is accepting connections.",
                "exited": False,
            }
        if pattern is not None and pattern.search(read_log(log_path)):
            return {
                "ready": True,
                "ready_reason": f"Matched {wait_for_log!r} in the log.",
                "exited": False,
            }
        await asyncio.sleep(0.25)

    if process.returncode is not None:
        return {
            "ready": False,
            "ready_reason": f"The process exited early with code {process.returncode}.",
            "exited": True,
        }
    if not has_signal:
        return {
            "ready": True,
            "ready_reason": (
                f"Started, and still running {limit:g}s later. No readiness check "
                "was requested — pass wait_for_port or wait_for_log to confirm it "
                "is actually serving."
            ),
            "exited": False,
        }
    return {
        "ready": False,
        "ready_reason": f"Still running, but did not signal readiness within {timeout}s.",
        "exited": False,
    }


# --------------------------------------------------------------------------
# the registry
# --------------------------------------------------------------------------


# How long a finished process's log survives. The registry is bounded by the
# lifetime of this process; the directory is not, and a machine that starts a
# dev server every day would otherwise keep every log forever.
_PRUNE_AFTER_SECONDS = 24 * 3600


def _prune() -> None:
    """Delete logs and sidecars for processes that are long gone."""
    if not LOG_ROOT.is_dir():
        return
    cutoff = time.time() - _PRUNE_AFTER_SECONDS
    for meta_path in LOG_ROOT.glob("proc_*.json"):
        try:
            if meta_path.stat().st_mtime > cutoff:
                continue
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if pid_alive(meta.get("pid")):
                continue
            log_path = meta.get("log_path")
            if log_path:
                Path(log_path).unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
        except (OSError, ValueError):
            continue
    # Scratch files from foreground commands that died before their cleanup ran.
    for scratch in LOG_ROOT.glob("cmd-*"):
        try:
            if scratch.stat().st_mtime < cutoff:
                scratch.unlink(missing_ok=True)
        except OSError:
            continue


async def start(
    command: str,
    cwd: str | None = None,
    wait_for_port: int | None = None,
    wait_for_log: str | None = None,
    wait_timeout_seconds: int | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Start a long-lived command on this Mac, detached, and say whether it came up."""
    command = strip_detach_syntax(command)
    if not command:
        raise ValueError("A non-empty command is required.")

    _prune()

    process_id = f"proc_{uuid.uuid4().hex[:10]}"
    log_path, meta_path = _log_paths(process_id)

    timeout = DEFAULT_READY_TIMEOUT if wait_timeout_seconds is None else int(wait_timeout_seconds)
    timeout = max(0, min(timeout, MAX_READY_TIMEOUT))

    log_handle = open(log_path, "ab", buffering=0)
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=log_handle,
            stderr=asyncio.subprocess.STDOUT,
            stdin=asyncio.subprocess.DEVNULL,
            cwd=cwd,
            start_new_session=True,
        )
    finally:
        # Our copy is redundant once the child holds one, and keeping it open
        # is how a log stays unflushed and reads back empty.
        log_handle.close()

    meta = {
        "process_id": process_id,
        "host": "mac",
        "command": command,
        "cwd": cwd,
        "pid": process.pid,
        "log_path": str(log_path),
        "started_at": time.time(),
    }
    _LIVE[process_id] = {"process": process, "meta": meta}
    try:
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
    except OSError:
        pass  # recovery after a restart is a convenience, not a precondition

    readiness = await await_ready(process, log_path, wait_for_port, wait_for_log, timeout)
    result = {
        **meta,
        "background": True,
        "running": process.returncode is None,
        "exit_code": process.returncode,
        "output": read_log(log_path),
        **readiness,
    }
    if note:
        result["note"] = note
    return result


def _recover(process_id: str) -> dict[str, Any] | None:
    """Re-adopt a process started before this agent restarted, from its sidecar."""
    _, meta_path = _log_paths(process_id)
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {"process": None, "meta": meta}


def _entry(process_id: str) -> dict[str, Any] | None:
    return _LIVE.get(process_id) or _recover(process_id)


def _running(entry: dict[str, Any]) -> bool:
    process = entry.get("process")
    if process is not None:
        return process.returncode is None
    return pid_alive(entry["meta"].get("pid"))


def _snapshot(entry: dict[str, Any], with_output: bool) -> dict[str, Any]:
    meta = entry["meta"]
    process = entry.get("process")
    running = _running(entry)
    snapshot = {
        **meta,
        "background": True,
        "running": running,
        "exit_code": None if running else (process.returncode if process is not None else None),
        "uptime_seconds": round(time.time() - float(meta.get("started_at") or 0), 1),
    }
    if with_output:
        snapshot["output"] = read_log(meta.get("log_path", ""))
    return snapshot


def _all() -> list[dict[str, Any]]:
    entries = dict(_LIVE)
    if LOG_ROOT.is_dir():
        for meta_path in LOG_ROOT.glob("proc_*.json"):
            process_id = meta_path.stem
            if process_id in entries:
                continue
            recovered = _recover(process_id)
            if recovered is not None and _running(recovered):
                entries[process_id] = recovered
    return list(entries.values())


def check(process_id: str | None = None) -> dict[str, Any]:
    """
    What a background process is doing, or all of them.

    With no id this lists everything known — the shape of the question
    actually asked out loud ("is the server still up?") — and matches how
    check_coding_task behaves.
    """
    if not process_id:
        return {"processes": [_snapshot(e, with_output=False) for e in _all()]}

    entry = _entry(process_id)
    if entry is None:
        return {
            "found": False,
            "process_id": process_id,
            "note": (
                "No such background process on the Mac. Call "
                "check_mac_background_command with no id to list them."
            ),
        }
    return {"found": True, **_snapshot(entry, with_output=True)}


async def stop(process_id: str) -> dict[str, Any]:
    """Stop a background process and its whole tree."""
    entry = _entry(process_id)
    if entry is None:
        return {
            "stopped": False,
            "process_id": process_id,
            "note": "No such background process on the Mac.",
        }

    meta = entry["meta"]
    was_running = _running(entry)
    if was_running:
        await kill_tree(entry.get("process"), pid=meta.get("pid"))

    _LIVE.pop(process_id, None)
    return {
        "stopped": True,
        "was_running": was_running,
        **meta,
        "output": read_log(meta.get("log_path", "")),
    }
