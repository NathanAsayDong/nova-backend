"""
Nova's self-deploy script.

Run with:
    uv run python scripts/deploy_main.py
    uv run python scripts/deploy_main.py --dry-run
    uv run python scripts/deploy_main.py --health-timeout 90

What it does, in order:
  1. Records the current commit as the rollback point.
  2. `git pull --ff-only origin main`.
  3. Runs the test suite; aborts (without touching any running process) if
     it fails.
  4. Restarts the API (`uv run main.py`) and worker (`uv run worker.py`).
  5. Polls /health for up to --health-timeout seconds.
  6. If health never comes back healthy, reverts to the rollback commit,
     restarts again, verifies health again, and exits non-zero either way.

Every run is logged to logs/deploy_<timestamp>.log with timestamps, and the
outcome of the most recent run is written to logs/last_deploy.json.

Windows-compatible: this is plain Python (run via `uv run`, same as main.py
and worker.py), with the two OS-specific lookups (which pid owns port 8000,
which pid is running worker.py) branching on process_supervisor.IS_WINDOWS
and falling back to lsof/pgrep off Windows for local dev and tests.

Self-restart safety: this script is meant to be started by the Nova tool
`deploy_main` (see src/service/deploy_service.py) while Nova's own backend
process is still running the tool call that triggered it. That means this
script's OS process can be a *descendant* of the very API process it is
about to stop. A tree-kill (`taskkill /F /T`) walks down from the target pid
to every process Windows still considers its descendant — including this
script, mid-deploy, if the target pid is an ancestor of ours. See
`_protected_pids` and the comment on `stop_pid` below for how this script
refuses to kill itself or anything upstream of itself while still being
free to tree-kill everything else (API/worker parents and the
multiprocessing.spawn children they leave behind).

Stale protected ancestors: refusing to kill an ancestor is the right call
mid-deploy, but it must not mean the ancestor is simply abandoned on the
port forever — production hit exactly that on 2026-11-16: a deploy run as a
descendant of the live API process left that old API (protected, as an
ancestor) still listening on port 8000 right alongside the freshly started
one, so some requests kept hitting old code. When `_sweep_leftovers` finds
port/worker pids it cannot touch because they are ancestors, it hands them
off to a *second*, independently-spawned, detached helper process (see
`spawn_stale_ancestor_helper` / `run_stale_ancestor_helper`). That helper is
launched with no inherited handles and its own session/process group (POSIX
`start_new_session`; Windows `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`)
specifically so it is *not* a descendant of the ancestor it is about to
kill, and so it keeps running even if this script — or the ancestor tree
itself — exits or is killed out from under it. It waits for this script's
own pid to exit (so it never races this deploy's own health check or
rollback), then tree-kills the stale ancestor pid(s), then makes sure
exactly one healthy API ends up listening on the port, restarting it if the
kill also took down the freshly started one. This script's own deploy
outcome (and exit code) never depends on that helper — a stale protected
ancestor is logged and handed off, never a deploy failure.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.service import process_supervisor as supervisor  # noqa: E402

LOG_DIR = REPO_ROOT / "logs"
STATE_FILE = LOG_DIR / "last_deploy.json"

DEFAULT_HEALTH_URL = "http://127.0.0.1:8000/health"
DEFAULT_HEALTH_TIMEOUT = 60
DEFAULT_PORT = 8000

# Floor for how long the stale-ancestor helper waits for this deploy script to
# exit before it will touch the ancestor tree. Scaled off --health-timeout
# (which the caller may raise well past the default) but never below this,
# since a rollback doubles the number of restart+health-check cycles this
# script can still be mid-way through.
STALE_ANCESTOR_HELPER_MIN_WAIT_SECONDS = 300
STALE_ANCESTOR_HELPER_WAIT_MULTIPLIER = 4

# Known-offline test modules (see the nova-backend-testing runbook): the rest
# of the suite imports things that hang or fail without the DB/network this
# deploy runs with (a websocket controller test that connects to Supabase at
# import time, etc). This is the same curated set that's been the documented
# way to run tests in a sandboxed/headless context; a maintainer who adds a
# new fully-offline test module should add it here too.
DEFAULT_TEST_MODULES = [
    "tests.test_conversation_loop",
    "tests.test_spoken_reply",
    "tests.test_claude_service",
    "tests.test_memory_injection",
    "tests.test_end_session",
    "tests.test_mcp_integration",
]


class DeployError(Exception):
    """Raised for a step that should abort the deploy outright."""


def _timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def build_logger(log_path: Path) -> logging.Logger:
    """A fresh logger per run, writing to its own timestamped file in logs/."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"deploy.{log_path.stem}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)
    return logger


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=False
    )


def current_commit(cwd: Path) -> str:
    result = run_git(["rev-parse", "HEAD"], cwd)
    if result.returncode != 0:
        raise DeployError(f"git rev-parse HEAD failed: {result.stderr.strip()}")
    return result.stdout.strip()


def git_pull(cwd: Path) -> str:
    result = run_git(["pull", "--ff-only", "origin", "main"], cwd)
    if result.returncode != 0:
        raise DeployError(f"git pull failed: {result.stderr.strip()}")
    return result.stdout.strip()


def git_reset_hard(cwd: Path, commit: str) -> None:
    result = run_git(["reset", "--hard", commit], cwd)
    if result.returncode != 0:
        raise DeployError(f"git reset --hard {commit} failed: {result.stderr.strip()}")


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


def run_test_suite(cwd: Path, modules: list[str] | None = None) -> tuple[bool, str]:
    """Run the curated offline unittest set. Returns (passed, combined output)."""
    modules = modules or DEFAULT_TEST_MODULES
    env = dict(os.environ)
    env.setdefault("OPENAI_API_KEY", "test-key")
    result = subprocess.run(
        ["uv", "run", "python", "-m", "unittest", *modules],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output


# ---------------------------------------------------------------------------
# process discovery / control
#
# Windows tower primarily; POSIX fallbacks exist only so this module can be
# imported and exercised (dry runs, unit tests) off Windows.
# ---------------------------------------------------------------------------


def find_all_pids_on_port(port: int) -> list[int]:
    """Every pid listening on `port`. Mirrors scripts/tower-status.ps1."""
    if supervisor.IS_WINDOWS:
        script = (
            f"(Get-NetTCPConnection -LocalPort {port} -State Listen "
            "-ErrorAction SilentlyContinue).OwningProcess"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
        )
    else:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"], capture_output=True, text=True, check=False
        )

    lines = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
    return sorted({int(line) for line in lines if line.isdigit()})


def find_pid_on_port(port: int) -> int | None:
    """The first pid listening on `port`, if any. Kept for single-pid callers."""
    pids = find_all_pids_on_port(port)
    return pids[0] if pids else None


def find_all_worker_pids() -> list[int]:
    """Every pid running `worker.py`."""
    if supervisor.IS_WINDOWS:
        script = (
            "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='uv.exe'\" "
            "| Where-Object { $_.CommandLine -match 'worker\\.py' } "
            "| Select-Object -ExpandProperty ProcessId"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
        )
    else:
        result = subprocess.run(
            ["pgrep", "-f", "worker.py"], capture_output=True, text=True, check=False
        )

    lines = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
    return sorted({int(line) for line in lines if line.isdigit()})


def find_worker_pid() -> int | None:
    """The first pid running `worker.py`, if any. Kept for single-pid callers."""
    pids = find_all_worker_pids()
    return pids[0] if pids else None


def _parent_pid_map() -> dict[int, int]:
    """pid -> parent pid, for every process currently visible on the box."""
    parents: dict[int, int] = {}
    try:
        if supervisor.IS_WINDOWS:
            script = (
                "Get-CimInstance Win32_Process | "
                "Select-Object ProcessId,ParentProcessId | ConvertTo-Csv -NoTypeInformation"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
                check=False,
            )
            rows = (result.stdout or "").splitlines()[1:]  # skip CSV header
            for row in rows:
                parts = [p.strip().strip('"') for p in row.split(",")]
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    parents[int(parts[0])] = int(parts[1])
        else:
            result = subprocess.run(
                ["ps", "-axo", "pid=,ppid="], capture_output=True, text=True, check=False
            )
            for line in (result.stdout or "").splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    parents[int(parts[0])] = int(parts[1])
    except OSError:
        pass
    return parents


def _protected_pids() -> set[int]:
    """
    This process's own pid, plus every ancestor of it.

    This script can be a *descendant* of the very API process it has just
    been told to stop (the Nova tool that triggers a deploy spawns this
    script from inside the uvicorn process serving that tool call). A
    tree-kill of an ancestor pid would walk back down and take out this
    script mid-deploy, so every pid in this set is off-limits no matter what
    find_pid_on_port / find_worker_pid / a leftover sweep turns up.
    """
    protected = {os.getpid()}
    parent_of = _parent_pid_map()
    current = os.getpid()
    for _ in range(64):  # bounded: a parent-pid cycle or bad data must not hang this
        parent = parent_of.get(current)
        if parent is None or parent in protected:
            break
        protected.add(parent)
        current = parent
    return protected


def stop_pid(pid: int | None, *, tree: bool = True) -> None:
    """
    Stop one process by pid, killing its whole tree by default.

    The API and worker are launched with `uv run`, and the API spawns
    multiprocessing.spawn children (some of which inherit the listening
    socket). Killing just the parent leaves those children running old code,
    which is how stale code kept answering requests after a deploy. On
    Windows that means `taskkill /F /T /PID`; off Windows it reuses
    `process_supervisor.kill_tree`, which kills the process group.

    The one thing this must never do is reach this script itself: see
    `_protected_pids`. Any pid that is this process or one of its ancestors
    is silently skipped instead of killed, tree or no tree. A pid that is
    already gone is also a no-op — never raise for that either.
    """
    if pid is None:
        return
    if pid in _protected_pids():
        return

    if supervisor.IS_WINDOWS:
        if tree:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, check=False
            )
        else:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, check=False)
        return

    if tree:
        try:
            supervisor.kill_tree(None, pid=pid)
            return
        except Exception:  # noqa: BLE001 - fall back to a plain signal below
            pass
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass


def spawn_stale_ancestor_helper(
    ancestor_pids: list[int],
    deploy_pid: int,
    port: int,
    health_url: str,
    repo_root: Path,
    max_wait_seconds: int,
) -> None:
    """
    Launch a detached helper that finishes cleaning up `ancestor_pids`.

    `stop_pid` refuses to touch these because they are ancestors of
    `deploy_pid` (see `_protected_pids`) — tree-killing one mid-deploy would
    take the deploy script down with it. This spawns a second process,
    re-invoking this same script in `--helper-mode`, specifically detached
    (own session/process group, no inherited stdio) so it is *not* itself a
    descendant of the ancestor tree and keeps running no matter what happens
    to `deploy_pid` or that tree. See `run_stale_ancestor_helper` for what it
    does once it wakes up.
    """
    args = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--helper-mode",
        "--deploy-pid",
        str(deploy_pid),
        "--ancestor-pids",
        ",".join(str(pid) for pid in ancestor_pids),
        "--port",
        str(port),
        "--health-url",
        health_url,
        "--repo-root",
        str(repo_root),
        "--max-wait-seconds",
        str(max_wait_seconds),
    ]
    popen_kwargs: dict = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if supervisor.IS_WINDOWS:
        # DETACHED_PROCESS: no console, not tied to this process's job/console.
        # CREATE_NEW_PROCESS_GROUP: so it is not in this process's group either.
        # getattr-guarded because these attributes don't exist in the
        # subprocess module on non-Windows interpreters (e.g. tests run on
        # the Mac/Linux dev box with supervisor.IS_WINDOWS patched to True).
        popen_kwargs["creationflags"] = getattr(
            subprocess, "DETACHED_PROCESS", 0x00000008
        ) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    else:
        popen_kwargs["start_new_session"] = True

    subprocess.Popen(args, **popen_kwargs)  # noqa: S603 - fixed argv, no shell


def _wait_for_pid_exit(pid: int, timeout_seconds: float, poll_interval: float = 1.0) -> bool:
    """Block until `pid` is no longer alive, or `timeout_seconds` elapses."""
    deadline = time.monotonic() + max(0, timeout_seconds)
    while supervisor.pid_alive(pid):
        if time.monotonic() >= deadline:
            return False
        time.sleep(poll_interval)
    return True


def _ensure_single_healthy_api(
    port: int,
    health_url: str,
    repo_root: Path,
    logger: logging.Logger,
    attempts: int = 5,
    delay_seconds: float = 2.0,
) -> bool:
    """
    Make sure exactly one process is listening on `port` and /health is up.

    Called after the stale ancestor tree has been killed. Killing that tree
    can (rarely) also take down the freshly started API — e.g. if it shared
    a process group with something underneath the old ancestor — so this
    restarts it when needed rather than just checking and giving up. It only
    ever stops pids it finds listening on `port` right now (never the
    ancestor pids already handled, never this helper's own pid, since this
    helper never binds the port itself).
    """
    for attempt in range(1, attempts + 1):
        remaining = find_all_pids_on_port(port)
        if len(remaining) == 1 and check_health_once(health_url):
            logger.info(
                f"Confirmed exactly one healthy API (pid={remaining[0]}) on port {port}."
            )
            return True

        if remaining:
            logger.warning(
                f"Attempt {attempt}/{attempts}: {len(remaining)} pid(s) on port {port} "
                f"({remaining}) are not a single healthy API; stopping and restarting."
            )
            for pid in remaining:
                stop_pid(pid)
        else:
            logger.warning(
                f"Attempt {attempt}/{attempts}: nothing is listening on port {port}; "
                "starting a fresh API."
            )

        try:
            start_api(repo_root, port)
        except Exception as exc:  # noqa: BLE001 - keep retrying the loop
            logger.error(f"Attempt {attempt}/{attempts}: failed to start API: {exc}")

        time.sleep(delay_seconds)

    remaining = find_all_pids_on_port(port)
    healthy = len(remaining) == 1 and check_health_once(health_url)
    if not healthy:
        logger.error(f"Gave up after {attempts} attempts; port {port} pid(s)={remaining}.")
    return healthy


def run_stale_ancestor_helper(
    deploy_pid: int,
    ancestor_pids: list[int],
    port: int,
    health_url: str,
    repo_root: Path,
    max_wait_seconds: int,
    logger: logging.Logger,
) -> int:
    """
    The detached helper's whole job, start to finish.

    Waits for the deploy script (`deploy_pid`) to exit — so this never races
    its health check or rollback — then tree-kills `ancestor_pids` and makes
    sure exactly one healthy API is left on `port` afterward. Deliberately
    never raises past this function's own try/except in `main()`: a bug here
    should end up logged in this helper's own log file, not crash silently
    with nothing to show for it.
    """
    logger.info(
        f"Stale-ancestor helper started for ancestor pid(s) {ancestor_pids}; "
        f"waiting up to {max_wait_seconds}s for deploy pid={deploy_pid} to exit."
    )
    if not _wait_for_pid_exit(deploy_pid, max_wait_seconds):
        logger.error(
            f"Deploy pid={deploy_pid} did not exit within {max_wait_seconds}s; "
            f"refusing to touch ancestor pid(s) {ancestor_pids} while it may still be "
            "one of their descendants."
        )
        return 1

    logger.info(f"Deploy pid={deploy_pid} has exited. Cleaning up ancestor pid(s) {ancestor_pids}.")

    # `stop_pid` re-derives this *helper's own* protected set (its pid plus
    # its own ancestors) every time it's called — not the exited deploy
    # script's. Because this helper was spawned detached, that set should
    # never contain the stale ancestor pids by the time we get here; this is
    # still what keeps the helper from ever killing itself.
    for pid in ancestor_pids:
        logger.info(f"Tree-killing stale ancestor pid={pid}")
        stop_pid(pid)

    time.sleep(1.0)

    healthy = _ensure_single_healthy_api(port, health_url, repo_root, logger)
    if healthy:
        logger.info("Stale-ancestor cleanup finished: exactly one healthy API is serving the port.")
        return 0
    logger.error("Stale-ancestor cleanup finished but could not confirm a single healthy API.")
    return 1


def start_api(cwd: Path, port: int) -> dict:
    """Start the API detached, and wait for it to accept connections on `port`."""
    return supervisor.start(
        "uv run main.py",
        cwd=str(cwd),
        wait_for_port=port,
        wait_timeout_seconds=30,
        host="tower",
    )


def start_worker(cwd: Path) -> dict:
    """Start the worker detached, and wait for its startup line in the log."""
    return supervisor.start(
        "uv run worker.py",
        cwd=str(cwd),
        wait_for_log="Nova worker online",
        wait_timeout_seconds=30,
        host="tower",
    )


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------


def check_health_once(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, OSError, ValueError):
        return False


def wait_for_health(url: str, timeout_seconds: int, interval_seconds: float = 2.0) -> bool:
    deadline = time.monotonic() + max(0, timeout_seconds)
    while True:
        if check_health_once(url):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(interval_seconds)


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------


@dataclass
class DeployConfig:
    repo_root: Path = field(default_factory=lambda: REPO_ROOT)
    port: int = DEFAULT_PORT
    health_url: str = DEFAULT_HEALTH_URL
    health_timeout: int = DEFAULT_HEALTH_TIMEOUT
    dry_run: bool = False
    test_modules: list[str] = field(default_factory=lambda: list(DEFAULT_TEST_MODULES))


class DeployRunner:
    """
    Orchestrates one deploy.

    Every externally-effectful step is its own method so a test can replace
    one (e.g. `wait_for_health`) without faking the whole OS; see
    tests/test_deploy_main.py for the rollback / abort-on-failing-tests /
    health-timeout cases built that way.
    """

    def __init__(self, config: DeployConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger

    def get_current_commit(self) -> str:
        return current_commit(self.config.repo_root)

    def pull_latest(self) -> str:
        return git_pull(self.config.repo_root)

    def run_tests(self) -> tuple[bool, str]:
        return run_test_suite(self.config.repo_root, self.config.test_modules)

    def restart_services(self) -> None:
        cfg = self.config

        self.logger.info(f"Stopping whatever is listening on port {cfg.port}...")
        for _ in range(5):
            pid = find_pid_on_port(cfg.port)
            if pid is None:
                break
            self.logger.info(f"  stopping api pid={pid}")
            stop_pid(pid)
            time.sleep(1)

        worker_pid = find_worker_pid()
        if worker_pid is not None:
            self.logger.info(f"Stopping worker pid={worker_pid}...")
            stop_pid(worker_pid)
            time.sleep(1)
        else:
            self.logger.info("No worker process found running; nothing to stop.")

        self._sweep_leftovers(cfg.port)

        self.logger.info("Starting API (uv run main.py)...")
        api_result = start_api(cfg.repo_root, cfg.port)
        self.logger.info(f"  api: {api_result.get('ready_reason')}")

        self.logger.info("Starting worker (uv run worker.py)...")
        worker_result = start_worker(cfg.repo_root)
        self.logger.info(f"  worker: {worker_result.get('ready_reason')}")

    def _sweep_leftovers(
        self, port: int, attempts: int = 5, delay_seconds: float = 1.0
    ) -> None:
        """
        Catch everything the single known-pid stops above could miss.

        `uv run` and the API's own multiprocessing.spawn children can leave
        behind extra processes still listening on `port` or still running
        worker.py — sometimes more than one of each. This finds *every* such
        pid (not just the first) and tree-kills each one, retrying with a
        short bounded backoff until the port is actually free, since a
        just-killed parent's socket can take a beat to release. `stop_pid`
        itself refuses to touch this script or any of its ancestors, so this
        loop can never kill its own process no matter what the lookups
        return.

        A leftover that IS this script's own ancestor is a different problem:
        `stop_pid` will keep silently skipping it forever, which is exactly
        how a stale ancestor API was left answering requests in production
        on 2026-11-16 (see the module docstring). Those pids are collected
        separately and handed off to a detached helper at the end instead of
        just being logged and abandoned.
        """
        protected = _protected_pids()
        stale_ancestors: set[int] = set()

        for attempt in range(1, attempts + 1):
            port_pids = find_all_pids_on_port(port)
            worker_pids = find_all_worker_pids()
            leftovers = sorted(set(port_pids) | set(worker_pids))
            if not leftovers:
                if stale_ancestors:
                    self._spawn_stale_ancestor_helper(sorted(stale_ancestors))
                return

            # "protected" is this script's own pid *plus* its ancestors.
            # Only the latter are a stale-ancestor problem to hand off — this
            # script's own pid showing up here would be a lookup bug, not
            # something to spawn a cleanup helper for.
            own_pid = os.getpid()
            ancestor_hits = sorted(pid for pid in leftovers if pid in protected and pid != own_pid)
            killable = [pid for pid in leftovers if pid not in protected]
            stale_ancestors.update(ancestor_hits)

            if ancestor_hits:
                self.logger.warning(
                    f"Sweep pass {attempt}/{attempts}: pid(s) {ancestor_hits} are ancestors "
                    "of this deploy script and cannot be tree-killed from here; will hand "
                    "off to a detached helper once this deploy finishes."
                )
            if not killable:
                # Nothing left this script itself can do here — every
                # remaining leftover is protected (an ancestor, or this
                # script's own pid, which should never actually appear). If
                # any of them are genuine ancestors, hand off and stop
                # immediately rather than silently abandoning them (the
                # 2026-11-16 prod bug) instead of looping pointlessly on
                # pids that will never become killable.
                if stale_ancestors:
                    self._spawn_stale_ancestor_helper(sorted(stale_ancestors))
                return

            self.logger.info(
                f"Sweep pass {attempt}/{attempts}: killing leftover pid(s) {killable} "
                f"(port listeners={port_pids or 'none'}, worker processes={worker_pids or 'none'})"
            )
            for leftover_pid in killable:
                stop_pid(leftover_pid)
            time.sleep(delay_seconds)

        # Exhausted every pass without the port/worker list ever coming up
        # empty — some killable leftover kept reappearing (e.g. a respawning
        # child) and/or a stale ancestor was seen on the last pass.
        if stale_ancestors:
            self._spawn_stale_ancestor_helper(sorted(stale_ancestors))
        self.logger.warning(
            f"Leftover sweep exhausted after {attempts} passes without the port/worker "
            "list ever coming up clear; see the sweep pass logs above for the pid(s) involved."
        )

    def _spawn_stale_ancestor_helper(self, ancestor_pids: list[int]) -> None:
        """
        Hand off pids `_sweep_leftovers` found but could not kill (ancestors
        of this script) to a detached helper process. See
        `spawn_stale_ancestor_helper` / `run_stale_ancestor_helper` for what
        that helper actually does. This never raises the deploy failure path
        — a stale protected ancestor is logged and delegated, not a reason
        to fail the deploy.
        """
        cfg = self.config
        max_wait = max(
            STALE_ANCESTOR_HELPER_MIN_WAIT_SECONDS,
            cfg.health_timeout * STALE_ANCESTOR_HELPER_WAIT_MULTIPLIER,
        )
        self.logger.warning(
            f"Spawning detached helper to clean up stale ancestor pid(s) {ancestor_pids} "
            f"after this deploy's own health check finishes (will wait up to {max_wait}s "
            "for this script to exit)."
        )
        try:
            spawn_stale_ancestor_helper(
                ancestor_pids=ancestor_pids,
                deploy_pid=os.getpid(),
                port=cfg.port,
                health_url=cfg.health_url,
                repo_root=cfg.repo_root,
                max_wait_seconds=max_wait,
            )
        except Exception as exc:  # noqa: BLE001 - never let this fail the deploy
            self.logger.error(f"Failed to spawn stale-ancestor helper: {exc}")

    def wait_for_health(self) -> bool:
        return wait_for_health(self.config.health_url, self.config.health_timeout)

    def rollback(self, commit: str) -> bool:
        self.logger.warning(f"Rolling back to {commit}")
        git_reset_hard(self.config.repo_root, commit)
        self.restart_services()
        healthy = self.wait_for_health()
        if healthy:
            self.logger.info("Rollback succeeded: service is healthy at the previous commit.")
        else:
            self.logger.error("Rollback restart did NOT pass the health check either.")
        return healthy

    def run(self) -> int:
        cfg = self.config
        self.logger.info(f"=== Deploy starting (dry_run={cfg.dry_run}) ===")

        rollback_commit = self.get_current_commit()
        self.logger.info(f"Rollback point recorded: {rollback_commit}")

        if cfg.dry_run:
            self.logger.info("DRY RUN: would `git pull --ff-only origin main` here.")
            passed, output = self.run_tests()
            self.logger.info("Test output:\n" + output)
            if not passed:
                self.logger.error(
                    "DRY RUN: test suite failed. A real deploy would abort here "
                    "without touching any running process."
                )
                return 1
            self.logger.info(
                f"DRY RUN: tests passed. A real deploy would now restart the API "
                f"(port {cfg.port}) and worker, then poll {cfg.health_url} for up "
                f"to {cfg.health_timeout}s. No process was touched."
            )
            return 0

        try:
            pulled = self.pull_latest()
            self.logger.info(f"git pull: {pulled or '(already up to date)'}")
        except DeployError as exc:
            self.logger.error(str(exc))
            return 1

        passed, output = self.run_tests()
        self.logger.info("Test output:\n" + output)
        if not passed:
            self.logger.error("Test suite failed; aborting deploy without restarting services.")
            return 1

        try:
            self.restart_services()
        except Exception as exc:  # noqa: BLE001 - any restart failure triggers rollback
            self.logger.error(f"Restart raised an exception: {exc}")
            if self.rollback(rollback_commit):
                return 1
            self.logger.error("Rollback also failed. Manual intervention required.")
            return 2

        if self.wait_for_health():
            self.logger.info("=== Deploy succeeded: service is healthy. ===")
            return 0

        self.logger.error(f"Health check did not pass within {cfg.health_timeout}s; rolling back.")
        if self.rollback(rollback_commit):
            self.logger.error("=== Deploy FAILED and was rolled back successfully. ===")
            return 1

        self.logger.error("=== Deploy FAILED and rollback ALSO failed its health check. ===")
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deploy Nova: pull main, test, restart, verify health, auto-rollback."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Record the rollback point and run the test suite, but never pull, "
        "restart, or touch a running process.",
    )
    parser.add_argument("--health-url", default=DEFAULT_HEALTH_URL)
    parser.add_argument("--health-timeout", type=int, default=DEFAULT_HEALTH_TIMEOUT)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    # Internal: how this script re-invokes itself as the detached
    # stale-ancestor helper (see spawn_stale_ancestor_helper). Not meant to
    # be passed by hand, hence SUPPRESS.
    parser.add_argument("--helper-mode", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--deploy-pid", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--ancestor-pids", default="", help=argparse.SUPPRESS)
    parser.add_argument(
        "--max-wait-seconds",
        type=int,
        default=STALE_ANCESTOR_HELPER_MIN_WAIT_SECONDS,
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    if args.helper_mode:
        ancestor_pids = [int(p) for p in args.ancestor_pids.split(",") if p.strip()]
        helper_log_path = LOG_DIR / f"stale_ancestor_helper_{time.strftime('%Y%m%d_%H%M%S')}.log"
        helper_logger = build_logger(helper_log_path)
        try:
            return run_stale_ancestor_helper(
                deploy_pid=args.deploy_pid,
                ancestor_pids=ancestor_pids,
                port=args.port,
                health_url=args.health_url,
                repo_root=Path(args.repo_root),
                max_wait_seconds=args.max_wait_seconds,
                logger=helper_logger,
            )
        except Exception as exc:  # noqa: BLE001 - always log, never crash silently
            helper_logger.error(f"Stale-ancestor helper crashed: {exc}")
            return 2

    log_path = LOG_DIR / f"deploy_{time.strftime('%Y%m%d_%H%M%S')}.log"
    logger = build_logger(log_path)

    config = DeployConfig(
        repo_root=Path(args.repo_root),
        port=args.port,
        health_url=args.health_url,
        health_timeout=args.health_timeout,
        dry_run=args.dry_run,
    )
    runner = DeployRunner(config, logger)

    try:
        exit_code = runner.run()
    except Exception as exc:  # noqa: BLE001 - never let an unhandled error skip logging
        logger.error(f"Deploy crashed: {exc}")
        exit_code = 2

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(
            {
                "finished_at": _timestamp(),
                "exit_code": exit_code,
                "log_path": str(log_path),
                "dry_run": args.dry_run,
            }
        ),
        encoding="utf-8",
    )
    logger.info(f"Exit code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
