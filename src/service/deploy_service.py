"""
Triggers scripts/deploy_main.py in the background and tracks the most recent
deploy's process id, so Nova can kick off a deploy and check on it later
without blocking a chat turn.

SAFETY: deploy_main is destructive. It restarts Nova's own backend and
worker processes on the tower, after pulling and testing main. It must only
be called once a human (Nate) has reviewed and approved the PR that is about
to be merged and deployed — see the tool description registered in
scripts/register_deploy_tools.py, which states this explicitly to the model.
This class has no way to verify approval happened (there is nothing in this
process to check it against); the calling agent is the one obligated not to
invoke it on its own initiative.

Reuses process_supervisor (the same module behind
start_background_command/check_background_command) for the actual detached
spawn and status polling, rather than inventing a second mechanism: the
deploy script is launched the same way as any other long-lived background
command, and `check_deploy_status` is a thin wrapper around
process_supervisor.check().
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from src.service import process_supervisor as supervisor

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEPLOY_SCRIPT = REPO_ROOT / "scripts" / "deploy_main.py"
STATE_PATH = REPO_ROOT / "logs" / "last_deploy_trigger.json"


class DeployService:
    def deploy_main(
        self,
        dry_run: bool = False,
        health_timeout_seconds: int | None = None,
    ) -> dict:
        """
        Tool entry point: start a deploy in the background and return its id.

        dry_run=True records the rollback point and runs the test suite but
        never pulls, restarts, or touches a running process — use it to
        sanity-check the script without any real effect.
        """
        command = f'uv run python "{DEPLOY_SCRIPT}"'
        if dry_run:
            command += " --dry-run"
        if health_timeout_seconds:
            command += f" --health-timeout {int(health_timeout_seconds)}"

        result = supervisor.start(
            command,
            cwd=str(REPO_ROOT),
            host="tower",
            note=(
                "Deploy started in the background. It will pull main, run "
                "tests, restart the backend and worker, verify health, and "
                "roll back automatically if health fails. Use "
                "check_deploy_status with this deploy_id to follow progress."
            ),
        )
        deploy_id = result["process_id"]
        self._record_last(deploy_id, dry_run)
        return {
            "deploy_id": deploy_id,
            "dry_run": dry_run,
            "started_at": result.get("started_at"),
            "note": result.get("note"),
        }

    def check_deploy_status(self, deploy_id: str | None = None) -> dict:
        """
        Tool entry point: status of one deploy, or the most recent one if
        deploy_id is omitted.
        """
        deploy_id = deploy_id or self._last_deploy_id()
        if not deploy_id:
            return {
                "found": False,
                "note": "No deploy has been triggered yet (or its record was lost).",
            }
        status = supervisor.check(deploy_id)
        status["deploy_id"] = deploy_id
        return status

    def _record_last(self, deploy_id: str, dry_run: bool) -> None:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            STATE_PATH.write_text(
                json.dumps(
                    {"deploy_id": deploy_id, "dry_run": dry_run, "started_at": time.time()}
                ),
                encoding="utf-8",
            )
        except OSError:
            pass  # best-effort; a deploy_id is still returned to the caller directly

    def _last_deploy_id(self) -> str | None:
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data.get("deploy_id")
