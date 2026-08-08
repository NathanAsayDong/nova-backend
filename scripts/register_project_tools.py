"""
Register the project-management and memory tools in the tool table so the
agent loop can call them.

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
        "name": "delete_project",
        "description": (
            "Permanently delete a project. This CASCADES: it also deletes the "
            "project's conversations, all of their messages, and all of its "
            "memory chunks. There is no undo. Call it first without force — if "
            "the project still has anything attached, the call fails with the "
            "exact counts of what would be destroyed. Report those counts to "
            "the user verbatim and get their explicit confirmation before "
            "retrying with force set to true. Never set force on the first "
            "attempt, and never set it based on your own judgment that the data "
            "looks unimportant."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.project_service.ProjectService.delete_project",
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Id of the project to delete.",
                    },
                    "force": {
                        "type": "boolean",
                        "description": (
                            "Set to true ONLY after the user has explicitly "
                            "confirmed deletion of the attached conversations, "
                            "messages, and memory. Defaults to false."
                        ),
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
    {
        "name": "fetch_memory",
        "description": (
            "Search Nova's long-term memory for information relevant to a query. "
            "Memory holds distilled facts, decisions, preferences, and outcomes "
            "from past conversations. The search is automatically scoped to the "
            "current conversation's project (plus general memory); conversations "
            "without a project search all memory. Use this when the user refers "
            "to something from the past, asks what you know or remember, or when "
            "prior context would clearly improve your answer."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.memory_chunk_service.MemoryChunkService.fetch_memory_for_conversation",
            "input_schema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": (
                            "What to look for, phrased as a standalone query "
                            "(e.g. 'user's preferences for deployment tooling')."
                        ),
                    },
                },
                "required": ["prompt"],
                "additionalProperties": False,
            },
            # Injected by the harness from the active conversation — the model
            # never supplies (and cannot spoof) this value.
            "context_kwargs": ["conversation_uuid"],
        },
    },
    {
        "name": "run_terminal_command",
        "description": (
            "Run a shell command on the local machine and return its exit code, "
            "stdout, and stderr. Use this for running and inspecting things — "
            "tests, builds, git, checking versions. "
            "NEVER use this to create, edit, or delete code files: all code must "
            "belong to a project, so use write_project_file, edit_project_file, "
            "and delete_project_file instead, which keep files inside the "
            "project's workspace. Do not use shell redirection, heredocs, tee, "
            "or editors to author files. "
            "Commands run with the backend's own privileges, so prefer "
            "read-only commands, and do not run destructive commands (deleting "
            "files, rewriting git history, installing or removing software, "
            "changing system settings) unless the user has explicitly asked for "
            "that specific action. A non-zero exit code is returned as data, not "
            "an error. Output is truncated at 8000 characters and the command is "
            "killed if it exceeds its timeout."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.command_line_service.CommandLineService.run_terminal_command",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to run.",
                    },
                    "working_directory": {
                        "type": "string",
                        "description": (
                            "Absolute path to run the command in. Defaults to the "
                            "backend process's working directory."
                        ),
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": (
                            "Seconds before the command is killed. Defaults to 30, "
                            "maximum 120."
                        ),
                    },
                },
                "required": ["command"],
                "additionalProperties": False,
            },
            # Lets the command default to the active project's workspace.
            "optional_context_kwargs": ["conversation_uuid"],
        },
    },
]

# Code tools. All of them resolve a project first — from an explicit
# project_id, otherwise from the active conversation — so code is always
# attributed to a project and confined to that project's workspace folder.
_PROJECT_ID_PROPERTY = {
    "type": "integer",
    "description": (
        "Project whose workspace to operate in. Defaults to the current "
        "conversation's project; only pass this to work on a different project."
    ),
}

CODE_TOOLS: list[dict] = [
    {
        "name": "list_project_files",
        "description": (
            "List the code files in a project's workspace folder. Use this when "
            "returning to a project to see what code already exists before "
            "reading or writing anything."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.code_service.CodeService.list_project_files",
            "input_schema": {
                "type": "object",
                "properties": {
                    "subdirectory": {
                        "type": "string",
                        "description": (
                            "Optional subdirectory to list, relative to the "
                            "project workspace. Omit to list everything."
                        ),
                    },
                    "project_id": _PROJECT_ID_PROPERTY,
                },
                "additionalProperties": False,
            },
            "optional_context_kwargs": ["conversation_uuid"],
        },
    },
    {
        "name": "read_project_file",
        "description": (
            "Read a file from a project's workspace folder. Paths are relative "
            "to the workspace (e.g. 'src/main.py'). Read a file before editing "
            "it so you know its current contents."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.code_service.CodeService.read_project_file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to the project workspace.",
                    },
                    "project_id": _PROJECT_ID_PROPERTY,
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            "optional_context_kwargs": ["conversation_uuid"],
        },
    },
    {
        "name": "write_project_file",
        "description": (
            "Write a file into a project's workspace folder, creating parent "
            "directories as needed. Use this to create new files or to replace "
            "a file's entire contents; for small changes to an existing file "
            "prefer edit_project_file, which avoids rewriting the whole file."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.code_service.CodeService.write_project_file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to the project workspace.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full contents to write to the file.",
                    },
                    "project_id": _PROJECT_ID_PROPERTY,
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
            "optional_context_kwargs": ["conversation_uuid"],
        },
    },
    {
        "name": "edit_project_file",
        "description": (
            "Edit an existing file in a project's workspace by running a shell "
            "command against it, instead of rewriting the file. The command runs "
            "with the project workspace as its working directory, so refer to "
            "the file by its relative path — for example "
            "\"sed -i '' 's/old/new/g' src/main.py\". Returns the command's exit "
            "code and a diff of what actually changed, so verify the diff "
            "matches your intent. Note that sed on macOS requires the empty "
            "string argument after -i."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.code_service.CodeService.edit_project_file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "File the command edits, relative to the project "
                            "workspace. Used to produce the diff."
                        ),
                    },
                    "command": {
                        "type": "string",
                        "description": "Shell command that modifies the file in place.",
                    },
                    "project_id": _PROJECT_ID_PROPERTY,
                },
                "required": ["path", "command"],
                "additionalProperties": False,
            },
            "optional_context_kwargs": ["conversation_uuid"],
        },
    },
    {
        "name": "delete_project_file",
        "description": (
            "Delete a file from a project's workspace folder. This is "
            "permanent. Deleting a directory requires recursive set to true — "
            "confirm with the user before doing that, since it removes every "
            "file inside it."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.code_service.CodeService.delete_project_file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to the project workspace.",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": (
                            "Required to delete a directory and everything in "
                            "it. Defaults to false."
                        ),
                    },
                    "project_id": _PROJECT_ID_PROPERTY,
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            "optional_context_kwargs": ["conversation_uuid"],
        },
    },
]

COMMUNICATION_TOOLS: list[dict] = [
    {
        "name": "send_email",
        "description": (
            "Send an email from the user's configured Gmail account. This goes "
            "out immediately and cannot be recalled, and it is sent as the user, "
            "not as you. Before calling this, show the user the exact "
            "recipients, subject, and body, and get their explicit approval to "
            "send — never send on your own initiative, and never send to "
            "recipients the user did not name. Returns true if the send "
            "succeeded and false if it failed."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.email_service.EmailService.send_email",
            "input_schema": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Recipient email addresses.",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Subject line.",
                    },
                    "body": {
                        "type": "string",
                        "description": "Body content of the email.",
                    },
                    "is_html": {
                        "type": "boolean",
                        "description": (
                            "Set true if the body is HTML. Defaults to false "
                            "(plain text)."
                        ),
                    },
                },
                "required": ["to", "subject", "body"],
                "additionalProperties": False,
            },
        },
    },
]

PROJECT_TOOLS = PROJECT_TOOLS + CODE_TOOLS + COMMUNICATION_TOOLS


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
