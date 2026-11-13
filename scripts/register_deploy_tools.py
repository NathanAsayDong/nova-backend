"""
Register the deploy tools so Nova can trigger and check on scripts/deploy_main.py.

Same shape as register_coding_tools.py: idempotent, --replace to update
descriptions in place.

Run with:
    uv run python scripts/register_deploy_tools.py
    uv run python scripts/register_deploy_tools.py --replace
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

from src.model.tool import Tool  # noqa: E402
from src.service.tool_service import ToolService  # noqa: E402

_BASE = "src.service.deploy_service.DeployService"

DEPLOY_TOOLS: list[dict] = [
    {
        "name": "deploy_main",
        "description": (
            "Deploy main to the tower: pull the latest main, run the test "
            "suite, restart the API and worker, verify /health, and "
            "automatically roll back to the previous commit (and restart "
            "again) if health does not come back after the restart. Runs in "
            "the background and returns immediately with a deploy_id — use "
            "check_deploy_status with that id (or no id, for the latest) to "
            "follow progress; it takes well over a minute end to end. "
            "SAFETY: this restarts Nova's own live backend and worker "
            "processes. Only call this after Nate has reviewed and "
            "explicitly approved the specific PR that is about to be merged "
            "and deployed — never call it on your own initiative, never call "
            "it to 'see what happens', and never call it just because a PR "
            "was opened or merged. If you want to sanity-check the script "
            "itself without any real effect (no pull, no restart, no "
            "process touched), pass dry_run=true, which only records the "
            "rollback point and runs the test suite."
        ),
        "config": {
            "type": "service_method",
            "callable_path": f"{_BASE}.deploy_main",
            "input_schema": {
                "type": "object",
                "properties": {
                    "dry_run": {
                        "type": "boolean",
                        "description": (
                            "Run the script without pulling, restarting, or "
                            "touching any running process — just the "
                            "rollback-point record and the test suite. "
                            "Defaults to false."
                        ),
                    },
                    "health_timeout_seconds": {
                        "type": "integer",
                        "description": (
                            "How long to poll /health after restarting before "
                            "giving up and rolling back. Defaults to 60."
                        ),
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "name": "check_deploy_status",
        "description": (
            "Check on a deploy started with deploy_main: whether it is still "
            "running, its exit code if it has finished (0 = succeeded, 1 = "
            "failed and rolled back, 2 = failed and the rollback itself did "
            "not come back healthy), and the tail of its log. With no "
            "deploy_id this checks the most recently triggered deploy. Safe "
            "to call any time, including repeatedly while a deploy is still "
            "running."
        ),
        "config": {
            "type": "service_method",
            "callable_path": f"{_BASE}.check_deploy_status",
            "input_schema": {
                "type": "object",
                "properties": {
                    "deploy_id": {
                        "type": "string",
                        "description": (
                            "The id returned by deploy_main. Omit to check "
                            "the most recent deploy."
                        ),
                    },
                },
                "additionalProperties": False,
            },
        },
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true", help="Update tools that already exist.")
    args = parser.parse_args()

    tool_service = ToolService()
    existing_by_name = {
        (tool.name or "").strip(): tool for tool in tool_service.list_tools()
    }

    for definition in DEPLOY_TOOLS:
        name = definition["name"]
        existing = existing_by_name.get(name)

        if existing is None:
            tool_service.add_tool(
                name=name,
                description=definition["description"],
                config=definition["config"],
            )
            print(f"registered: {name}")
        elif args.replace:
            validated = tool_service._validate_config(definition["config"])
            tool_service.tool_dao.update(
                existing.id,
                Tool(
                    name=name,
                    description=definition["description"],
                    config=validated.model_dump(mode="json"),
                ),
            )
            print(f"replaced:   {name}")
        else:
            print(f"skipped:    {name} (already exists; use --replace to update)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
