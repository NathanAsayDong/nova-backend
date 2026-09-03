"""
Register the coding-agent tools so Nova can hand work to the Mac.

Same shape as register_project_tools.py: idempotent, --replace to update
descriptions in place.

Run with:
    uv run python scripts/register_coding_tools.py
    uv run python scripts/register_coding_tools.py --replace
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

from src.model.tool import Tool  # noqa: E402
from src.service.tool_service import ToolService  # noqa: E402

_BASE = "src.service.coding_service.CodingService"

CODING_TOOLS: list[dict] = [
    {
        "name": "start_coding_task",
        "description": (
            "Hand a real coding task to Claude Code running on Nate's Mac. Use this "
            "for work that means reading and changing a codebase — building a "
            "feature, fixing a bug, refactoring — not for answering questions about "
            "code, which you should just answer. The task runs in its own git "
            "worktree on a branch named nova/<slug>, so it never disturbs what Nate "
            "has open, and the result is a branch he reviews. It runs for minutes to "
            "an hour: say you have started it and move on, then use check_coding_task "
            "when he asks. Write the instructions as you would brief a capable "
            "engineer who cannot ask you a follow-up: what to build, where, and how "
            "to know it worked."
        ),
        "config": {
            "type": "service_method",
            "callable_path": f"{_BASE}.start_coding_task",
            "input_schema": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name as it appears on Nate's Desktop, e.g. 'nova-backend'.",
                    },
                    "instructions": {
                        "type": "string",
                        "description": "The full brief for the coding agent.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Short label for the task, a few words. Used as the branch name and in the UI.",
                    },
                    "project_id": {
                        "type": "integer",
                        "description": "Project this work belongs to, if any.",
                    },
                },
                "required": ["repo", "instructions"],
                "additionalProperties": False,
            },
        },
    },
    {
        "name": "check_coding_task",
        "description": (
            "What the coding agent is doing. With no session_id it reports every "
            "task still open, which is what 'how's that going?' usually means. This "
            "reads Nova's own record rather than the Mac, so it answers instantly "
            "and works even when the laptop is asleep."
        ),
        "config": {
            "type": "service_method",
            "callable_path": f"{_BASE}.check_coding_task",
            "input_schema": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "A specific task's id. Omit to summarise all open tasks.",
                    }
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "name": "send_feedback_to_coding_task",
        "description": (
            "Send Nate's words into a running coding task — a correction, an extra "
            "requirement, a change of direction. If the agent is mid-step the "
            "feedback is queued and applied when that step finishes; if it is "
            "between steps it starts the next one immediately. Set steer=true only "
            "when the agent is visibly going the wrong way and letting it finish "
            "would waste time, since that cuts its current step short."
        ),
        "config": {
            "type": "service_method",
            "callable_path": f"{_BASE}.send_feedback_to_coding_task",
            "input_schema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "The task to send feedback to."},
                    "text": {"type": "string", "description": "What to tell the coding agent."},
                    "steer": {
                        "type": "boolean",
                        "description": "Interrupt the current step instead of waiting for it.",
                    },
                },
                "required": ["session_id", "text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "name": "stop_coding_task",
        "description": (
            "End a coding task. The branch and its commits survive — only the live "
            "session ends. Use when Nate says he is done with it or wants it "
            "abandoned."
        ),
        "config": {
            "type": "service_method",
            "callable_path": f"{_BASE}.stop_coding_task",
            "input_schema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "The task to stop."}
                },
                "required": ["session_id"],
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

    for definition in CODING_TOOLS:
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
