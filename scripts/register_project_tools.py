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

# Responsibilities: recurring background work the worker runs on a schedule.
_SCHEDULE_PROPERTY = {
    "type": "array",
    "items": {
        "type": "string",
        "enum": ["morning", "afternoon", "evening", "night"],
    },
    "description": (
        "Time-of-day windows to run in. Runs at most once per window, so "
        "['morning','evening'] means twice a day. morning=6-12, "
        "afternoon=12-17, evening=17-21, night=21-6. Omit to run every window."
    ),
}
_REPORT_TYPE_PROPERTY = {
    "type": "string",
    "enum": ["email", "sms", "call", "chat"],
    "description": (
        "How to report results. Only 'email' can actually be delivered today — "
        "the others have no tool yet, so the responsibility runs but only "
        "summarizes in its reply. Omit for no report."
    ),
}

RESPONSIBILITY_TOOLS: list[dict] = [
    {
        "name": "list_responsibilities",
        "description": (
            "List all responsibilities — recurring background tasks that run "
            "automatically on a schedule — with their ids, schedules, and when "
            "each last ran. Use this to find a responsibility before updating "
            "or deleting it."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.responsibility_service.ResponsibilityService.get_all_responsibilities",
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "name": "get_responsibility",
        "description": "Get one responsibility by id, including its schedule and last run time.",
        "config": {
            "type": "service_method",
            "callable_path": "src.service.responsibility_service.ResponsibilityService.get_responsibility",
            "input_schema": {
                "type": "object",
                "properties": {
                    "responsibility_id": {
                        "type": "integer",
                        "description": "Id of the responsibility.",
                    },
                },
                "required": ["responsibility_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "name": "create_responsibility",
        "description": (
            "Create a recurring background task that runs on a schedule without "
            "the user present. The description is the ONLY instruction the agent "
            "receives when it runs later, so write it as a complete, standalone "
            "brief — not a reminder note. Attach a project_id when the work "
            "belongs to a project, so it can use that project's files and memory."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.responsibility_service.ResponsibilityService.create_responsibility",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Short name, e.g. 'Morning inbox triage'.",
                    },
                    "description": {
                        "type": "string",
                        "description": (
                            "Full standalone instructions for the agent to carry "
                            "out unattended."
                        ),
                    },
                    "schedule": _SCHEDULE_PROPERTY,
                    "project_id": {
                        "type": "integer",
                        "description": "Optional project this work belongs to.",
                    },
                    "report_type": _REPORT_TYPE_PROPERTY,
                },
                "required": ["name", "description"],
                "additionalProperties": False,
            },
        },
    },
    {
        "name": "update_responsibility",
        "description": (
            "Update a responsibility's name, description, schedule, project, or "
            "report type. Omitted fields are left unchanged. Use "
            "list_responsibilities first to find the id."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.responsibility_service.ResponsibilityService.update_responsibility",
            "input_schema": {
                "type": "object",
                "properties": {
                    "responsibility_id": {
                        "type": "integer",
                        "description": "Id of the responsibility to update.",
                    },
                    "name": {"type": "string", "description": "New name."},
                    "description": {
                        "type": "string",
                        "description": "New standalone instructions.",
                    },
                    "schedule": _SCHEDULE_PROPERTY,
                    "project_id": {
                        "type": "integer",
                        "description": "Project to attach this responsibility to.",
                    },
                    "report_type": _REPORT_TYPE_PROPERTY,
                },
                "required": ["responsibility_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "name": "delete_responsibility",
        "description": (
            "Delete a responsibility so it stops running on its schedule. This "
            "only removes the schedule entry — work it already did (files, "
            "emails, memory) is unaffected. Confirm the correct id with the user "
            "before deleting."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.responsibility_service.ResponsibilityService.delete_responsibility",
            "input_schema": {
                "type": "object",
                "properties": {
                    "responsibility_id": {
                        "type": "integer",
                        "description": "Id of the responsibility to delete.",
                    },
                },
                "required": ["responsibility_id"],
                "additionalProperties": False,
            },
        },
    },
]

# Updates: notifications produced by background work (sub-agents,
# responsibilities) that the user hasn't seen yet.
UPDATE_TOOLS: list[dict] = [
    {
        "name": "get_unviewed_updates",
        "description": (
            "List the updates the user has not seen yet, oldest first. Updates "
            "are written when background work finishes — a sub-agent or "
            "responsibility completes and its outcome is summarized into an "
            "update. Each update may carry the project and/or conversation the "
            "work came from, which explains why it ran. Call this when the "
            "user asks what's new, to report on their updates, or about the "
            "updates indicator. After you have reported the updates to the "
            "user, call mark_all_updates_viewed so the indicator clears."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.update_service.UpdateService.get_unviewed_updates",
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "name": "mark_all_updates_viewed",
        "description": (
            "Mark every unviewed update as viewed, clearing the client's "
            "updates indicator. Call this only after you have actually "
            "reported the unviewed updates to the user."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.update_service.UpdateService.mark_all_updates_viewed",
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
]

# Background agents: one-off sub-agents that run detached from the chat turn
# and report back through the updates system.
BACKGROUND_AGENT_TOOLS: list[dict] = [
    {
        "name": "run_background_agent",
        "description": (
            "Kick off a background sub-agent for work too long or too "
            "self-contained for the current chat turn — multi-step research, "
            "bulk file work, anything the user should not sit through. "
            "Returns immediately; the agent runs on its own and its summary "
            "is posted as an update linked to this conversation and its "
            "project, which the user can read via get_unviewed_updates or "
            "the updates UI. The prompt is the agent's ONLY instruction and "
            "it cannot ask follow-up questions, so write a complete, "
            "standalone brief. After calling this, tell the user the task "
            "has started and that an update will appear when it is done. Do "
            "not use this for quick work you could do inline, and if you are "
            "already a background agent, do the work yourself instead of "
            "spawning another agent."
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.harness.agent_loop.AgentLoop.run_agent",
            "input_schema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": (
                            "Complete, standalone instructions for the "
                            "background agent to carry out unattended."
                        ),
                    },
                },
                "required": ["prompt"],
                "additionalProperties": False,
            },
            "static_kwargs": {"background": True},
            # Injected by the harness when the call comes from a conversation
            # so the resulting update links back to it; absent (and fine) when
            # a background agent itself is the caller.
            "optional_context_kwargs": ["conversation_uuid"],
        },
    },
]

# Direct database access. Reads are free; writes are gated behind an
# explicit flag and user confirmation; DDL is refused by the service.
SQL_TOOLS: list[dict] = [
    {
        "name": "run_sql",
        "description": (
            "Run a raw SQL statement directly against Nova's Postgres "
            "database (Supabase) — the same database behind projects, "
            "conversations, messages, memory, responsibilities, and updates. "
            "Read-only by default: SELECTs and introspection queries are "
            "safe to run on your own initiative to answer questions the "
            "other tools can't. To modify data (INSERT/UPDATE/DELETE) you "
            "must set allow_writes to true, and you may only do that after "
            "showing the user the exact statement and getting their "
            "explicit confirmation — prefer the dedicated tools "
            "(create_project, create_responsibility, ...) over raw writes "
            "whenever one exists. Schema and privilege changes "
            "(CREATE/ALTER/DROP/TRUNCATE/GRANT/...) are refused entirely; "
            "ask the user to run those in the Supabase SQL editor. Results "
            "are capped at 200 rows. Note the updates table is named "
            '"update", a reserved word — quote it in queries.'
        ),
        "config": {
            "type": "service_method",
            "callable_path": "src.service.sql_service.SQLService.run_sql",
            "input_schema": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "The SQL statement to run.",
                    },
                    "allow_writes": {
                        "type": "boolean",
                        "description": (
                            "Set true only for an INSERT/UPDATE/DELETE the "
                            "user has explicitly approved after seeing the "
                            "statement. Defaults to false (read-only)."
                        ),
                    },
                },
                "required": ["sql"],
                "additionalProperties": False,
            },
        },
    },
]

PROJECT_TOOLS = (
    PROJECT_TOOLS + CODE_TOOLS + COMMUNICATION_TOOLS + RESPONSIBILITY_TOOLS
    + UPDATE_TOOLS + BACKGROUND_AGENT_TOOLS + SQL_TOOLS
)

# Superseded tools to remove from the tool table on every run. Registration
# is the single source of truth for what the model can call, so retiring a
# tool means listing it here — not editing the database by hand.
DEPRECATED_TOOLS: list[str] = [
    # Replaced by run_background_agent: it ran AgentLoop.run_agent awaited
    # (blocking the chat turn) instead of detached with an update on finish.
    "run_sub_agent",
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

    for name in DEPRECATED_TOOLS:
        existing = existing_by_name.pop(name, None)
        if existing is not None:
            tool_service.tool_dao.delete(existing.id)
            print(f"removed:    {name} (deprecated)")

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
