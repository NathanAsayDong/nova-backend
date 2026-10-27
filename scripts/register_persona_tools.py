"""
Register the persona-management tools in the tool table so the agent loop
can call them.

Same shape as register_project_tools.py: idempotent, --replace to update
descriptions/config in place.

Requires migration 009 (persona_prompt table + functions) to already be
applied — see scripts/migrations/009_persona_prompt.sql.

Run with:
    uv run python scripts/register_persona_tools.py
    uv run python scripts/register_persona_tools.py --replace
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

from src.model.tool import Tool  # noqa: E402
from src.service.tool_service import ToolService  # noqa: E402

_BASE = "src.service.persona_service.PersonaService"

PERSONA_TOOLS: list[dict] = [
    {
        "name": "get_persona",
        "description": (
            "Read Nova's current active persona prompt: its version number "
            "and full content. Use this before update_persona so the edit is "
            "based on the real current text rather than a guess, and any time "
            "Nate asks what the persona currently says."
        ),
        "config": {
            "type": "service_method",
            "callable_path": f"{_BASE}.get_persona",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "name": "update_persona",
        "description": (
            "Replace Nova's persona prompt with new content, effective "
            "immediately on the next turn everywhere. This is a PERSISTED "
            "ACTION — it changes who Nova is for every future conversation, "
            "not just this one — so confirm the change with Nate before "
            "calling it: read back what will change (or the full new text if "
            "it's short) and get an explicit yes first, the same as any other "
            "persisted action. Call get_persona first if you need the current "
            "text to edit rather than replace outright. Pass the FULL new "
            "persona text, not a diff — this replaces the entire prompt. "
            "Content under 50 characters or over 20,000 is rejected. Every "
            "past version is kept, so a bad edit is a rollback_persona call "
            "away, not a crisis."
        ),
        "config": {
            "type": "service_method",
            "callable_path": f"{_BASE}.tool_update_persona",
            "input_schema": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": (
                            "The complete new persona prompt text, replacing "
                            "the current one in full."
                        ),
                    },
                    "change_note": {
                        "type": "string",
                        "description": (
                            "A short note on what changed and why, e.g. "
                            "'Nate asked for less sarcasm in voice mode'. "
                            "Required — this is what list_persona_versions "
                            "shows later."
                        ),
                    },
                },
                "required": ["content", "change_note"],
                "additionalProperties": False,
            },
        },
    },
    {
        "name": "list_persona_versions",
        "description": (
            "List every stored persona version, newest first, with its "
            "version number, change note, author, timestamp, and whether it "
            "is currently active. Does not include the full text of each "
            "version — call get_persona for the active one's content, or "
            "rollback_persona to inspect/activate an older one."
        ),
        "config": {
            "type": "service_method",
            "callable_path": f"{_BASE}.tool_list_persona_versions",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "name": "rollback_persona",
        "description": (
            "Activate a previous persona version by its version number, "
            "undoing whatever changed after it. This is a PERSISTED ACTION — "
            "confirm with Nate which version to roll back to before calling "
            "it, the same as update_persona. Use list_persona_versions first "
            "to find the right version number."
        ),
        "config": {
            "type": "service_method",
            "callable_path": f"{_BASE}.tool_rollback_persona",
            "input_schema": {
                "type": "object",
                "properties": {
                    "version": {
                        "type": "integer",
                        "description": "The version number to reactivate.",
                    },
                },
                "required": ["version"],
                "additionalProperties": False,
            },
        },
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Update description/config in place for tools that already exist.",
    )
    args = parser.parse_args()

    tool_service = ToolService()
    existing_by_name = {
        (tool.name or "").strip(): tool for tool in tool_service.list_tools()
    }

    for definition in PERSONA_TOOLS:
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
