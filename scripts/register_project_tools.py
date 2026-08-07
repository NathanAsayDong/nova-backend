"""
Register the project-management tools in the tool table so the agent loop
can call them.

Idempotent: existing tools (matched by name) are skipped unless --replace is
passed, in which case their description/config are updated in place.

Run with:
    uv run python scripts/register_project_tools.py
    uv run python scripts/register_project_tools.py --replace
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

from src.model.tool import Tool  # noqa: E402
from src.service.tool_service import ToolService  # noqa: E402

PROJECT_TOOLS: list[dict] = [
    {
        "name": "create_project",
        "description": (
            "Create a new project. Projects group conversations and memory around "
            "an ongoing body of work. Returns the created project including its id."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.project_service.ProjectService.create_project",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Short, human-readable project name.",
                    },
                    "description": {
                        "type": "string",
                        "description": "What this project is about and what it is trying to achieve.",
                    },
                },
                "required": ["name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "name": "update_project",
        "description": (
            "Update an existing project's name and/or description. Use list_projects "
            "first if you need to find the project id. Returns the updated project."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.project_service.ProjectService.update_project",
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Id of the project to update.",
                    },
                    "name": {
                        "type": "string",
                        "description": "New project name. Omit to leave unchanged.",
                    },
                    "description": {
                        "type": "string",
                        "description": "New project description. Omit to leave unchanged.",
                    },
                },
                "required": ["project_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "name": "list_projects",
        "description": (
            "List all projects with their ids, names, and descriptions. Use this to "
            "find a project before updating it or assigning the conversation to it."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.project_service.ProjectService.list_projects",
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "name": "assign_conversation_to_project",
        "description": (
            "Attach the current conversation to a project so its messages are "
            "attributed to that project. Only works when this conversation has no "
            "project yet — a conversation can belong to at most one project, ever. "
            "To move to a different project use switch_project instead. Use "
            "list_projects to find the project id, or create_project if it "
            "doesn't exist yet."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.conversation_service.ConversationService.assign_project",
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Id of the project to attach this conversation to.",
                    },
                },
                "required": ["project_id"],
                "additionalProperties": False,
            },
            # Injected by the harness from the active conversation — the model
            # never supplies (and cannot spoof) this value.
            "context_kwargs": ["conversation_uuid"],
        },
    },
    {
        "name": "switch_project",
        "description": (
            "Switch the user's session to a different project. Conversations and "
            "messages belong to at most one project, ever, so switching never "
            "re-homes history: if the current conversation has no project it is "
            "attached in place; otherwise the current conversation is closed and "
            "the chat continues automatically in a fresh conversation attached to "
            "the target project (the client is redirected — the user does not "
            "need to do anything). Use list_projects to find the project id, or "
            "create_project if it doesn't exist yet."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.conversation_service.ConversationService.switch_project",
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Id of the project to switch this session to.",
                    },
                },
                "required": ["project_id"],
                "additionalProperties": False,
            },
            # Injected by the harness from the active conversation — the model
            # never supplies (and cannot spoof) this value.
            "context_kwargs": ["conversation_uuid"],
        },
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Update description/config of tools that already exist.",
    )
    args = parser.parse_args()

    tool_service = ToolService()
    existing_by_name = {
        (tool.name or "").strip(): tool for tool in tool_service.list_tools()
    }

    for definition in PROJECT_TOOLS:
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


if __name__ == "__main__":
    main()
