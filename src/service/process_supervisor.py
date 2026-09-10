"""
Long-lived commands, supervised.

A dev server is not a command that is slow; it is a command that never
finishes. Both shell tools used to wait on pipes, and a pipe closes when its
LAST writer closes it — so backgrounding with `start` or a trailing `&` bought
nothing: the spawned server inherited the pipe write end and held the tool
hostage for the whole timeout anyway. Then the timeout killed the shell rather
than the process group, so the server survived — alive, invisible to Nova, and
holding the port the next attempt needed.

So there are no pipes and no bare kills anywhere in here. Every command gets
its own process group and writes to a log file on disk, which separates the two
questions that pipes conflate: "has it exited?" (wait on the pid) and "what has
it said?" (read the file). A detached grandchild can no longer keep a tool call
open, and killing means killing the whole group.

The registry is module-level deliberately. ToolService builds a fresh service
instance for every tool call, so a handle kept on `self` would be gone by the
time Nova asked what it was doing — the same trap CodingService hit with its
link. A JSON sidecar next to each log lets a restarted backend re-discover
processes it started before, because a stray uvicorn nobody can see or stop is
the exact failure this module exists to end.

Mirrored by mac_agent/novacode/processes.py. The result shapes must stay
identical: agent_loop draws the same terminal artifact whichever host ran the
command.
"""

from __future__ import annotations

import json
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

IS_WINDOWS = os.name == "nt"

MAX_OUTPUT_CHARS = 8_000
DEFAULT_READY_TIMEOUT = 20
MAX_READY_TIMEOUT = 120
# How long to watch a process with no readiness check before calling it
# started. Not zero, because the most common way a server "starts" is to die
# on an import error and the crash is worth catching; not the full timeout
# either, because with nothing to wait FOR there is nothing to learn by
# waiting — that is 20 wasted seconds in the middle of a turn.
CRASH_GRACE_SECONDS = 1.5

LOG_ROOT = Path(tempfile.gettempdir()) / "nova-processes"

# Handles for processes this process started, keyed by our own id. Values are
# {"popen": Popen, "meta": dict}. Module-level; see the note above.
_LIVE: dict[str, dict[str, Any]] = {}


# --------------------------------------------------------------------------
# recognising a command that will never finish
# --------------------------------------------------------------------------

# Commands whose whole job is to keep running. Routing these to the background
# automatically is the difference between "Nova started the server" and "Nova
# hung for 30s and then killed it". A false positive here is cheap — the model
# gets a handle plus a note instead of final output, and can read the log — so
# the list is allowed to be a little generous, but every entry is anchored so
# it cannot fire on an unrelated word inside a path or a message.
_LONG_LIVED = re.compile(
    r"""(?:^|[;&|]\s*|\s)(?:
          uvicorn\b
        | gunicorn\b
        | hypercorn\b
        | daphne\b
        | waitress-serve\b
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
        # This repo's own entry point: main.py *is* the FastAPI app, so
        # `uv run main.py` never returns. It is the command that prompted all
        # of this. Anchored to a runner on purpose — bare `main\.py` would
        # also fire on `cat main.py`, and answering a file read with a process
        # handle is its own kind of broken.
        | (?:python3?|uv\s+run|poetry\s+run|pipenv\s+run)\s+(?:\S+\s+)*?main\.py\b
    )""",
    re.VERBOSE | re.IGNORECASE,
)

# Commands whose job is to look at something and stop. These are checked
# before the long-lived patterns, because a name can appear as an argument as
# easily as a program: `grep -n uvicorn main.py` mentions two triggers and is
# over in milliseconds. `tail` is deliberately absent — `tail -f` is the one
# inspector that really does run forever.
_INSPECTORS = re.compile(
    r"""^\s*(?:cat|bat|grep|rg|ag|less|more|head|wc|ls|find|fd|which|type|echo
        |sed|awk|git|stat|du|diff|file|open|code|vim|nano|printf|test)\b""",
    re.VERBOSE | re.IGNORECASE,
)

# A command the model tried to detach by hand. Neither form ever worked through
# a pipe-capturing tool, so both are rewritten into a real background start
# rather than left to hang.
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

    Returns (mode, reason) where mode is 'foreground' or 'background'. The
    reason is prose Nova can pass straight through to the transcript — the
    model learns the rule from the note far faster than from a tool
    description it half-read.
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
            "background process instead. 'start' does not detach a process from "
            "this tool, and its output would have been lost."
        )
    if _INSPECTORS.match(text):
        return "foreground", None
    if _LONG_LIVED.search(text):
        return "background", (
            "This looks like a long-lived process (a server, a watcher) rather "
            "than a command that finishes, so it was started in the background. "
            "Read its output with check_background_command; stop it with "
            "stop_background_command when you are done."
        )
    return "foreground", None


def strip_detach_syntax(command: str) -> str:
    """Remove hand-rolled detach syntax that the supervisor now handles properly."""
    text = (command or "").strip()
    text = _WINDOWS_START.sub(r"\1\2", text).strip()
    text = _TRAILING_AMPERSAND.sub("", text).strip()
    return text


# --------------------------------------------------------------------------
# process groups, portably
# --------------------------------------------------------------------------


def spawn_kwargs() -> dict[str, Any]:
    """
    Popen keyword arguments that put the child in its own process group.

    This is what makes a kill mean the whole tree. Without it, killing a
    `shell=True` command kills the shell and orphans everything it started,
    which is how a leaked uvicorn ends up holding port 8000 with nobody
    holding a handle to it.
    """
    if IS_WINDOWS:
        return {
            "creationflags": (
                subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
                | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
        }
    return {"start_new_session": True}


def kill_tree(process: subprocess.Popen | None, pid: int | None = None) -> None:
    """
    Kill a process and everything it started, and reap it.

    Reaping matters as much as killing: an unwaited child keeps its file
    handles open, and on the async side a zombie's pipes eventually wedge the
    event loop.
    """
    pid = pid if pid is not None else (process.pid if process else None)
    if pid is None:
        return

    if IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            check=False,
        )
    else:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(os.getpgid(pid), sig)
            except (ProcessLookupError, PermissionError):
                break
            if process is not None:
                try:
                    process.wait(timeout=3)
                    break
                except subprocess.TimeoutExpired:
                    continue
            else:
                time.sleep(0.3)
                if not pid_alive(pid):
                    break

    if process is not None:
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass


def pid_alive(pid: int | None) -> bool:
    """
    Whether `pid` is still running, for a process we do not hold a handle to.

    Never os.kill(pid, 0) on Windows: unlike POSIX, signal 0 is not a
    no-op probe there — Python maps it onto TerminateProcess, so the
    "check" would kill the thing it was asking about.
    """
    if pid is None:
        return False
    if IS_WINDOWS:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in (result.stdout or "")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


# --------------------------------------------------------------------------
# logs
# --------------------------------------------------------------------------


def _log_paths(process_id: str) -> tuple[Path, Path]:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    return LOG_ROOT / f"{process_id}.log", LOG_ROOT / f"{process_id}.json"


def read_log(path: str | Path, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    """
    The tail of a log file.

    The tail, not the head: for anything long-lived the interesting part is
    what it said most recently — the traceback, the request it just served —
    while the first 8000 characters are a banner and a dependency list.
    """
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    return f"... [earlier {omitted} characters omitted]\n" + text[-max_chars:]


def clip(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    text = text or ""
    if len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    return text[:max_chars] + f"\n... [truncated {omitted} characters]"


# --------------------------------------------------------------------------
# readiness
# --------------------------------------------------------------------------


def port_open(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=0.5):
            return True
    except OSError:
        return False


def await_ready(
    process: subprocess.Popen,
    log_path: Path,
    wait_for_port: int | None,
    wait_for_log: str | None,
    timeout: int,
) -> dict[str, Any]:
    """
    Block until the process is demonstrably up, has died, or the wait expires.

    "Up" has to mean something better than "we called Popen and it did not
    immediately explode", or Nova reports a running server and the next curl
    gets connection refused. A listening port or a matching log line is a real
    answer; so is an early exit, which is the most useful outcome of all — a
    server that dies on import should be reported as a crash with its
    traceback, not as a healthy background process.
    """
    pattern = re.compile(wait_for_log) if wait_for_log else None
    has_signal = bool(wait_for_port or pattern is not None)
    limit = timeout if has_signal else min(timeout, CRASH_GRACE_SECONDS)
    deadline = time.monotonic() + max(0, limit)

    while time.monotonic() < deadline:
        if process.poll() is not None:
            return {
                "ready": False,
                "ready_reason": f"The process exited early with code {process.returncode}.",
                "exited": True,
            }
        if wait_for_port and port_open(wait_for_port):
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
        time.sleep(0.25)

    if process.poll() is not None:
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


def start(
    command: str,
    cwd: str | None = None,
    wait_for_port: int | None = None,
    wait_for_log: str | None = None,
    wait_timeout_seconds: int | None = None,
    note: str | None = None,
    host: str = "tower",
) -> dict[str, Any]:
    """Start a long-lived command, detached, and report whether it came up."""
    command = strip_detach_syntax(command)
    if not command:
        raise ValueError("A non-empty command is required.")

    _prune()

    process_id = f"proc_{uuid.uuid4().hex[:10]}"
    log_path, meta_path = _log_paths(process_id)

    timeout = DEFAULT_READY_TIMEOUT if wait_timeout_seconds is None else int(wait_timeout_seconds)
    timeout = max(0, min(timeout, MAX_READY_TIMEOUT))

    # Append, and hand the same handle to stderr: one interleaved log reads the
    # way the developer's own terminal would, and ordering between the two
    # streams is usually the thing you need.
    log_handle = open(log_path, "ab", buffering=0)
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            cwd=cwd,
            **spawn_kwargs(),
        )
    finally:
        # Our copy is redundant once the child holds one, and leaving it open
        # is how a "closed" log file stays unflushed and unreadable.
        log_handle.close()

    meta = {
        "process_id": process_id,
        "host": host,
        "command": command,
        "cwd": cwd,
        "pid": process.pid,
        "log_path": str(log_path),
        "started_at": time.time(),
    }
    _LIVE[process_id] = {"popen": process, "meta": meta}
    try:
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
    except OSError:
        pass  # recovery after a restart is a convenience, not a precondition

    readiness = await_ready(process, log_path, wait_for_port, wait_for_log, timeout)
    result = {
        **meta,
        "background": True,
        "running": process.poll() is None,
        "exit_code": process.returncode,
        "output": read_log(log_path),
        **readiness,
    }
    if note:
        result["note"] = note
    return result


def _recover(process_id: str) -> dict[str, Any] | None:
    """Re-adopt a process started before this backend restarted, from its sidecar."""
    _, meta_path = _log_paths(process_id)
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {"popen": None, "meta": meta}


def _entry(process_id: str) -> dict[str, Any] | None:
    return _LIVE.get(process_id) or _recover(process_id)


def _running(entry: dict[str, Any]) -> bool:
    process = entry.get("popen")
    if process is not None:
        return process.poll() is None
    return pid_alive(entry["meta"].get("pid"))


def check(process_id: str | None = None) -> dict[str, Any]:
    """
    What a background process is doing, or all of them.

    With no id this lists everything known, which is the shape of the question
    actually asked — "is the server still up?" — and matches how
    check_coding_task behaves.
    """
    if not process_id:
        return {"processes": [_snapshot(e, with_output=False) for e in _all()]}

    entry = _entry(process_id)
    if entry is None:
        return {
            "found": False,
            "process_id": process_id,
            "note": "No such background process. Call check_background_command with no id to list them.",
        }
    return {"found": True, **_snapshot(entry, with_output=True)}


def _snapshot(entry: dict[str, Any], with_output: bool) -> dict[str, Any]:
    meta = entry["meta"]
    process = entry.get("popen")
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
    """Everything in this process's registry, plus anything recoverable on disk."""
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


def stop(process_id: str) -> dict[str, Any]:
    """Stop a background process and its whole tree."""
    entry = _entry(process_id)
    if entry is None:
        return {
            "stopped": False,
            "process_id": process_id,
            "note": "No such background process.",
        }

    meta = entry["meta"]
    was_running = _running(entry)
    if was_running:
        kill_tree(entry.get("popen"), pid=meta.get("pid"))

    _LIVE.pop(process_id, None)
    return {
        "stopped": True,
        "was_running": was_running,
        **meta,
        "output": read_log(meta.get("log_path", "")),
    }
