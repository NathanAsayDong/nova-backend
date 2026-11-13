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
about to stop. See the comment on `stop_pid` below for why that makes
`taskkill /F /T` (tree-kill) actively dangerous here, and what this script
does instead.
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


def find_pid_on_port(port: int) -> int | None:
    """The pid listening on `port`, if any. Mirrors scripts/tower-status.ps1."""
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
        lines = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
        return int(lines[0]) if lines and lines[0].isdigit() else None

    result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True, check=False)
    lines = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
    return int(lines[0]) if lines and lines[0].isdigit() else None


def find_worker_pid() -> int | None:
    """The pid running `worker.py`, if any."""
    if supervisor.IS_WINDOWS:
        script = (
            "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='uv.exe'\" "
            "| Where-Object { $_.CommandLine -match 'worker\\.py' } "
            "| Select-Object -First 1 -ExpandProperty ProcessId"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
        )
        lines = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
        return int(lines[0]) if lines and lines[0].isdigit() else None

    result = subprocess.run(["pgrep", "-f", "worker.py"], capture_output=True, text=True, check=False)
    lines = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
    return int(lines[0]) if lines and lines[0].isdigit() else None


def stop_pid(pid: int | None) -> None:
    """
    Stop exactly one process by pid. Deliberately NOT a tree-kill.

    This script can itself be a *descendant* of the API process it has just
    been told to stop: the Nova tool that triggers a deploy
    (src/service/deploy_service.py) spawns this script from inside the very
    uvicorn process serving that tool call. `process_supervisor.kill_tree`
    uses `taskkill /F /T /PID` on Windows, which walks down from the target
    pid to every process Windows still considers its descendant — including
    this script, mid-deploy, if the target pid is an ancestor of ours. A
    plain, non-tree kill of only the pid we looked up (the one actually
    listening on the port / running worker.py) cannot reach upward or
    sideways to anything else, so it cannot kill the deploy script itself.

    If uvicorn's --reload spawns a child that re-binds the port after the
    parent dies, the caller re-checks find_pid_on_port and calls this again
    on the new pid — still never a tree-kill.
    """
    if pid is None:
        return
    if supervisor.IS_WINDOWS:
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, check=False)
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass


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

        self.logger.info("Starting API (uv run main.py)...")
        api_result = start_api(cfg.repo_root, cfg.port)
        self.logger.info(f"  api: {api_result.get('ready_reason')}")

        self.logger.info("Starting worker (uv run worker.py)...")
        worker_result = start_worker(cfg.repo_root)
        self.logger.info(f"  worker: {worker_result.get('ready_reason')}")

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
    args = parser.parse_args(argv)

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
