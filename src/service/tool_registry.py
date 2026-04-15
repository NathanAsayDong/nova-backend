import datetime as dt
import copy
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from openai import APIConnectionError, APITimeoutError, OpenAI

from src.service.cursor_service import CursorService, CursorServiceError
from src.service.github_service import GithubService, GithubServiceError


DEFAULT_CODE_PLANNER_MODEL = "gpt-5.4-mini-2026-03-17"


class ToolExecutionError(Exception):
    def __init__(self, message: str, recoverable: bool = True) -> None:
        super().__init__(message)
        self.recoverable = recoverable


@dataclass
class ToolSpec:
    name: str
    description: str
    enabled: bool
    handler_id: str
    json_schema: dict[str, Any]
    file_path: Path


class ToolRegistry:
    def __init__(self, tools_dir: Path | None = None) -> None:
        default_tools_dir = Path(__file__).resolve().parent.parent / "tools"
        self.tools_dir = tools_dir or default_tools_dir
        self._tools: dict[str, ToolSpec] = {}
        self.cursor_service = CursorService()
        self.github_service = GithubService()
        self._handler_map: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "get_current_time_handler": self._get_current_time,
            "write_code_handler": self._write_code,
            "check_prs_handler": self._check_prs,
            "check_coding_agent_handler": self._check_coding_agent,
            "code_planner_handler": self._code_planner,
            "github_list_repos_handler": self._github_list_repos,
            "github_read_repo_code_handler": self._github_read_repo_code,
        }

        self.tools_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_default_tool_files()
        self.load_from_files()

    def _ensure_default_tool_files(self) -> None:
        defaults = [
            {
                "name": "get_current_time",
                "description": "Get the current date.",
                "enabled": True,    
                "handler_id": "get_current_time_handler",
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "The current date."
                        },
                        "time": {
                            "type": "string",
                            "description": "The current time."
                        }
                    },
                    "required": ["date", "time"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "write_code",
                "description": "Launch a Cursor coding agent against a GitHub repository.",
                "enabled": True,
                "handler_id": "write_code_handler",
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Instruction prompt for the Cursor coding agent.",
                        },
                        "repository_url": {
                            "type": "string",
                            "description": "GitHub repository URL, e.g. https://github.com/org/repo.",
                        },
                        "ref": {
                            "type": "string",
                            "description": "Base branch/ref for the Cursor agent.",
                        },
                        "branch_name": {
                            "type": "string",
                            "description": "Optional branch name for the Cursor target.",
                        },
                        "model": {
                            "type": "string",
                            "description": "Optional Cursor model override.",
                        },
                        "auto_create_pr": {
                            "type": "boolean",
                            "description": "Whether Cursor should auto-create a pull request.",
                        },
                    },
                    "required": ["prompt", "repository_url"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "check_prs",
                "description": "List pull requests for a GitHub repository.",
                "enabled": True,
                "handler_id": "check_prs_handler",
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "repository_url": {
                            "type": "string",
                            "description": "GitHub repository URL, e.g. https://github.com/org/repo.",
                        },
                        "state": {
                            "type": "string",
                            "description": "PR state filter: open, closed, or all.",
                            "enum": ["open", "closed", "all"],
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of pull requests to return (1-100).",
                            "minimum": 1,
                            "maximum": 100,
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number for pagination.",
                            "minimum": 1,
                        },
                    },
                    "required": ["repository_url"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "check_coding_agent",
                "description": "Get Cursor coding agent status and optional conversation history.",
                "enabled": True,
                "handler_id": "check_coding_agent_handler",
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "Cursor agent id, e.g. bc_abc123.",
                        },
                        "include_conversation": {
                            "type": "boolean",
                            "description": "Include conversation history when true.",
                        },
                    },
                    "required": ["agent_id"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "code_planner",
                "description": "Generate an implementation plan and a Cursor-ready execution prompt.",
                "enabled": True,
                "handler_id": "code_planner_handler",
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "objective": {
                            "type": "string",
                            "description": "What should be built or changed.",
                        },
                        "repository_url": {
                            "type": "string",
                            "description": "Optional GitHub repository URL for implementation context.",
                        },
                        "context": {
                            "type": "string",
                            "description": "Optional extra context, constraints, or acceptance criteria.",
                        },
                    },
                    "required": ["objective"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "github_list_repos",
                "description": "List GitHub repositories available to this Nova backend.",
                "enabled": True,
                "handler_id": "github_list_repos_handler",
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "visibility": {
                            "type": "string",
                            "description": "Repository visibility filter.",
                            "enum": ["all", "public", "private"],
                        },
                        "affiliation": {
                            "type": "string",
                            "description": "GitHub affiliation filter (comma-separated values).",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of repositories to return (1-100).",
                            "minimum": 1,
                            "maximum": 100,
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number for pagination.",
                            "minimum": 1,
                        },
                        "sort": {
                            "type": "string",
                            "description": "Sort key for repository listing.",
                            "enum": ["created", "updated", "pushed", "full_name"],
                        },
                        "direction": {
                            "type": "string",
                            "description": "Sort direction.",
                            "enum": ["asc", "desc"],
                        },
                    },
                    "required": [],
                    "additionalProperties": False,
                },
            },
            {
                "name": "github_read_repo_code",
                "description": "Read code from a GitHub repository file or list a repository directory.",
                "enabled": True,
                "handler_id": "github_read_repo_code_handler",
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "repository_url": {
                            "type": "string",
                            "description": "GitHub repository URL, e.g. https://github.com/org/repo.",
                        },
                        "path": {
                            "type": "string",
                            "description": "Repository-relative path to a file or directory. Empty means repository root.",
                        },
                        "ref": {
                            "type": "string",
                            "description": "Optional branch, tag, or commit SHA.",
                        },
                        "max_bytes": {
                            "type": "integer",
                            "description": "Maximum file bytes to return for file reads (512-500000).",
                            "minimum": 512,
                            "maximum": 500000,
                        },
                    },
                    "required": ["repository_url"],
                    "additionalProperties": False,
                },
            },
        ]

        for payload in defaults:
            file_path = self.tools_dir / f"{payload['name']}.txt"
            if file_path.exists():
                continue
            self._atomic_write_json(file_path, payload)

    @staticmethod
    def _atomic_write_json(file_path: Path, payload: dict[str, Any]) -> None:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, dir=file_path.parent) as tmp:
            json.dump(payload, tmp, indent=2)
            tmp.write("\n")
            tmp_path = Path(tmp.name)

        tmp_path.replace(file_path)

    def _validate_tool_payload(self, payload: dict[str, Any], file_path: Path) -> ToolSpec:
        required_fields = {"name", "description", "enabled", "handler_id", "json_schema"}
        missing = required_fields - payload.keys()
        if missing:
            raise ValueError(f"Missing fields {sorted(missing)} in {file_path.name}")

        name = payload["name"]
        description = payload["description"]
        enabled = payload["enabled"]
        handler_id = payload["handler_id"]
        json_schema = payload["json_schema"]

        if not isinstance(name, str) or not name:
            raise ValueError(f"Invalid 'name' in {file_path.name}")

        expected_name = file_path.stem
        if name != expected_name:
            raise ValueError(f"Tool name '{name}' must match filename '{expected_name}'")

        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"Invalid 'description' in {file_path.name}")

        if not isinstance(enabled, bool):
            raise ValueError(f"Invalid 'enabled' in {file_path.name}")

        if not isinstance(handler_id, str) or handler_id not in self._handler_map:
            raise ValueError(f"Invalid 'handler_id' in {file_path.name}")

        if not isinstance(json_schema, dict):
            raise ValueError(f"Invalid 'json_schema' in {file_path.name}")

        return ToolSpec(
            name=name,
            description=description,
            enabled=enabled,
            handler_id=handler_id,
            json_schema=json_schema,
            file_path=file_path,
        )

    def load_from_files(self) -> None:
        loaded: dict[str, ToolSpec] = {}

        for file_path in sorted(self.tools_dir.glob("*.txt")):
            with open(file_path, "r", encoding="utf-8") as tool_file:
                payload = json.load(tool_file)

            if not isinstance(payload, dict):
                raise ValueError(f"Tool definition in {file_path.name} must be a JSON object")

            spec = self._validate_tool_payload(payload, file_path)
            loaded[spec.name] = spec

        self._tools = loaded

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "enabled": spec.enabled,
                "handler_id": spec.handler_id,
                "json_schema": spec.json_schema,
            }
            for spec in sorted(self._tools.values(), key=lambda item: item.name)
        ]

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def set_enabled(self, name: str, enabled: bool) -> dict[str, Any]:
        spec = self.get(name)
        if spec is None:
            raise ToolExecutionError(f"Unknown tool: {name}", recoverable=False)

        updated_payload = {
            "name": spec.name,
            "description": spec.description,
            "enabled": enabled,
            "handler_id": spec.handler_id,
            "json_schema": spec.json_schema,
        }
        self._atomic_write_json(spec.file_path, updated_payload)

        updated_spec = ToolSpec(
            name=spec.name,
            description=spec.description,
            enabled=enabled,
            handler_id=spec.handler_id,
            json_schema=spec.json_schema,
            file_path=spec.file_path,
        )
        self._tools[name] = updated_spec

        return {
            "name": updated_spec.name,
            "description": updated_spec.description,
            "enabled": updated_spec.enabled,
            "handler_id": updated_spec.handler_id,
            "json_schema": updated_spec.json_schema,
        }

    def as_openai_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": spec.name,
                "description": spec.description,
                "parameters": self._to_openai_strict_schema(spec.json_schema),
                "strict": True,
            }
            for spec in self._tools.values()
            if spec.enabled
        ]

    @staticmethod
    def _to_openai_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize schemas for OpenAI strict function validation:
        - `required` must include every property key.
        - Fields that were previously optional become nullable so the model can still
          omit semantic values by sending null.
        """
        normalized = copy.deepcopy(schema)
        properties = normalized.get("properties")
        if not isinstance(properties, dict):
            return normalized

        required_raw = normalized.get("required")
        existing_required = (
            set(required_raw)
            if isinstance(required_raw, list) and all(isinstance(item, str) for item in required_raw)
            else set()
        )

        for field_name, field_schema in properties.items():
            if field_name in existing_required:
                continue
            if not isinstance(field_schema, dict):
                continue
            ToolRegistry._make_nullable(field_schema)

        normalized["required"] = list(properties.keys())
        if "additionalProperties" not in normalized:
            normalized["additionalProperties"] = False
        return normalized

    @staticmethod
    def _make_nullable(field_schema: dict[str, Any]) -> None:
        field_type = field_schema.get("type")
        if isinstance(field_type, str):
            field_schema["type"] = [field_type, "null"]
        elif isinstance(field_type, list):
            if "null" not in field_type:
                field_schema["type"] = [*field_type, "null"]
        else:
            any_of = field_schema.get("anyOf")
            if isinstance(any_of, list):
                has_null = any(
                    isinstance(item, dict) and item.get("type") == "null"
                    for item in any_of
                )
                if not has_null:
                    any_of.append({"type": "null"})

        enum_values = field_schema.get("enum")
        if isinstance(enum_values, list) and None not in enum_values:
            field_schema["enum"] = [*enum_values, None]

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        spec = self.get(name)
        if spec is None:
            raise ToolExecutionError(f"Unknown tool: {name}", recoverable=False)

        if not spec.enabled:
            raise ToolExecutionError(f"Tool '{name}' is disabled.", recoverable=True)

        handler = self._handler_map[spec.handler_id]
        return handler(arguments)

    @staticmethod
    def _get_current_time(_: dict[str, Any]) -> dict[str, Any]:
        now = dt.datetime.now(dt.timezone(dt.timedelta(hours=-6)))
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M")
        return {"date": date, "time": time}

    def _write_code(self, arguments: dict[str, Any]) -> dict[str, Any]:
        prompt = (arguments.get("prompt") or "").strip()
        repository_url = (arguments.get("repository_url") or "").strip()
        if not prompt:
            raise ToolExecutionError("'prompt' is required.", recoverable=True)
        if not repository_url:
            raise ToolExecutionError("'repository_url' is required.", recoverable=True)

        ref = (arguments.get("ref") or "main").strip() or "main"
        branch_name_raw = arguments.get("branch_name")
        branch_name = branch_name_raw.strip() if isinstance(branch_name_raw, str) and branch_name_raw.strip() else None
        model_raw = arguments.get("model")
        model = model_raw.strip() if isinstance(model_raw, str) and model_raw.strip() else None
        auto_create_pr_value = arguments.get("auto_create_pr")
        auto_create_pr = True if auto_create_pr_value is None else bool(auto_create_pr_value)

        try:
            normalized_repo = self.github_service.normalize_repository_url(repository_url)
            launched = self.cursor_service.launch_agent(
                prompt_text=prompt,
                repository_url=normalized_repo,
                ref=ref,
                branch_name=branch_name,
                model=model,
                auto_create_pr=auto_create_pr,
            )
        except (GithubServiceError, CursorServiceError) as exc:
            raise ToolExecutionError(str(exc), recoverable=True) from exc
        except Exception as exc:
            raise ToolExecutionError(f"write_code failed: {str(exc)}", recoverable=True) from exc

        return {
            "status": "submitted",
            "agent_id": launched.get("id"),
            "repository_url": normalized_repo,
            "ref": ref,
            "auto_create_pr": auto_create_pr,
            "agent": launched,
        }

    def _check_prs(self, arguments: dict[str, Any]) -> dict[str, Any]:
        repository_url = (arguments.get("repository_url") or "").strip()
        if not repository_url:
            raise ToolExecutionError("'repository_url' is required.", recoverable=True)

        state = (arguments.get("state") or "open").strip().lower()
        if state not in {"open", "closed", "all"}:
            raise ToolExecutionError("'state' must be one of: open, closed, all.", recoverable=True)

        limit = self._coerce_int(arguments.get("limit"), "limit", default=20, minimum=1, maximum=100)
        page = self._coerce_int(arguments.get("page"), "page", default=1, minimum=1, maximum=None)

        try:
            normalized_repo = self.github_service.normalize_repository_url(repository_url)
            pull_requests = self.github_service.list_pull_requests(
                repository_url=normalized_repo,
                state=state,
                per_page=limit,
                page=page,
            )
        except GithubServiceError as exc:
            raise ToolExecutionError(str(exc), recoverable=True) from exc
        except Exception as exc:
            raise ToolExecutionError(f"check_prs failed: {str(exc)}", recoverable=True) from exc

        return {
            "repository_url": normalized_repo,
            "state": state,
            "page": page,
            "limit": limit,
            "count": len(pull_requests),
            "pull_requests": pull_requests,
        }

    def _check_coding_agent(self, arguments: dict[str, Any]) -> dict[str, Any]:
        agent_id = (arguments.get("agent_id") or "").strip()
        if not agent_id:
            raise ToolExecutionError("'agent_id' is required.", recoverable=True)

        include_conversation = bool(arguments.get("include_conversation", False))

        try:
            agent_payload = self.cursor_service.get_agent_status(agent_id)
            status_value = str(agent_payload.get("status") or "").upper()
            result: dict[str, Any] = {
                "agent_id": agent_id,
                "status": status_value,
                "terminal": status_value in {"COMPLETED", "FAILED", "STOPPED", "CANCELED", "CANCELLED"},
                "agent": agent_payload,
            }

            if include_conversation:
                conversation = self.cursor_service.get_agent_conversation(agent_id)
                result["conversation"] = conversation

            return result
        except CursorServiceError as exc:
            raise ToolExecutionError(str(exc), recoverable=True) from exc
        except Exception as exc:
            raise ToolExecutionError(f"check_coding_agent failed: {str(exc)}", recoverable=True) from exc

    def _code_planner(self, arguments: dict[str, Any]) -> dict[str, Any]:
        objective = (arguments.get("objective") or "").strip()
        if not objective:
            raise ToolExecutionError("'objective' is required.", recoverable=True)

        repository_url_raw = (arguments.get("repository_url") or "").strip()
        context = (arguments.get("context") or "").strip()

        normalized_repo: str | None = None
        if repository_url_raw:
            try:
                normalized_repo = self.github_service.normalize_repository_url(repository_url_raw)
            except GithubServiceError as exc:
                raise ToolExecutionError(f"Invalid repository_url: {str(exc)}", recoverable=True) from exc

        api_key = (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_APIKEY") or "").strip()
        if not api_key:
            raise ToolExecutionError("OPENAI_API_KEY is not set for code_planner.", recoverable=True)

        model = (os.getenv("CODE_PLANNER_MODEL") or DEFAULT_CODE_PLANNER_MODEL).strip()
        client = OpenAI(api_key=api_key)

        system_prompt = (
            "You are a senior software planner. Produce a concise, implementation-ready plan for coding work. "
            "Focus on concrete, testable steps, edge cases, and verification."
        )

        user_prompt_parts = [
            f"Objective:\n{objective}",
            (
                f"Repository:\n{normalized_repo}"
                if normalized_repo
                else "Repository:\nNot provided"
            ),
            (
                f"Additional context:\n{context}"
                if context
                else "Additional context:\nNone"
            ),
            (
                "Return markdown with these exact sections:\n"
                "## Summary\n"
                "## Implementation Steps\n"
                "## Risks and Edge Cases\n"
                "## Verification"
            ),
        ]

        try:
            response = client.responses.create(
                model=model,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": system_prompt}],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": "\n\n".join(user_prompt_parts)}],
                    },
                ],
                timeout=45,
            )
        except (APITimeoutError, APIConnectionError, TimeoutError) as exc:
            raise ToolExecutionError(f"code_planner timed out: {str(exc)}", recoverable=True) from exc
        except Exception as exc:
            raise ToolExecutionError(f"code_planner failed: {str(exc)}", recoverable=True) from exc

        plan_markdown = (response.output_text or "").strip()
        if not plan_markdown:
            raise ToolExecutionError("code_planner returned an empty response.", recoverable=True)

        cursor_prompt_parts = [
            "Implement the following coding objective in the target repository.",
            f"Objective: {objective}",
        ]
        if normalized_repo:
            cursor_prompt_parts.append(f"Repository URL: {normalized_repo}")
        if context:
            cursor_prompt_parts.append(f"Context: {context}")

        cursor_prompt_parts.extend(
            [
                "Follow this implementation plan:",
                plan_markdown,
                "Return a concise completion summary with any relevant PR link.",
            ]
        )

        return {
            "objective": objective,
            "repository_url": normalized_repo,
            "model": model,
            "plan_markdown": plan_markdown,
            "cursor_prompt": "\n\n".join(cursor_prompt_parts),
        }

    def _github_list_repos(self, arguments: dict[str, Any]) -> dict[str, Any]:
        visibility = (arguments.get("visibility") or "all").strip().lower()
        if visibility not in {"all", "public", "private"}:
            raise ToolExecutionError("'visibility' must be one of: all, public, private.", recoverable=True)

        affiliation = (arguments.get("affiliation") or "owner,collaborator,organization_member").strip()
        sort = (arguments.get("sort") or "updated").strip().lower()
        if sort not in {"created", "updated", "pushed", "full_name"}:
            raise ToolExecutionError(
                "'sort' must be one of: created, updated, pushed, full_name.",
                recoverable=True,
            )

        direction = (arguments.get("direction") or "desc").strip().lower()
        if direction not in {"asc", "desc"}:
            raise ToolExecutionError("'direction' must be one of: asc, desc.", recoverable=True)

        limit = self._coerce_int(arguments.get("limit"), "limit", default=30, minimum=1, maximum=100)
        page = self._coerce_int(arguments.get("page"), "page", default=1, minimum=1, maximum=None)

        try:
            repositories = self.github_service.list_repositories(
                visibility=visibility,
                affiliation=affiliation,
                per_page=limit,
                page=page,
                sort=sort,
                direction=direction,
            )
        except GithubServiceError as exc:
            raise ToolExecutionError(str(exc), recoverable=True) from exc
        except Exception as exc:
            raise ToolExecutionError(f"github_list_repos failed: {str(exc)}", recoverable=True) from exc

        return {
            "count": len(repositories),
            "page": page,
            "limit": limit,
            "visibility": visibility,
            "affiliation": affiliation,
            "repositories": repositories,
        }

    def _github_read_repo_code(self, arguments: dict[str, Any]) -> dict[str, Any]:
        repository_url = (arguments.get("repository_url") or "").strip()
        if not repository_url:
            raise ToolExecutionError("'repository_url' is required.", recoverable=True)

        path = (arguments.get("path") or "").strip()
        ref_value = arguments.get("ref")
        ref = ref_value.strip() if isinstance(ref_value, str) and ref_value.strip() else None

        max_bytes = self._coerce_int(
            arguments.get("max_bytes"),
            "max_bytes",
            default=120000,
            minimum=512,
            maximum=500000,
        )

        try:
            normalized_repo = self.github_service.normalize_repository_url(repository_url)
            result = self.github_service.read_repository_code(
                repository_url=normalized_repo,
                path=path,
                ref=ref,
                max_bytes=max_bytes,
            )
        except GithubServiceError as exc:
            raise ToolExecutionError(str(exc), recoverable=True) from exc
        except Exception as exc:
            raise ToolExecutionError(f"github_read_repo_code failed: {str(exc)}", recoverable=True) from exc

        return {
            **result,
            "max_bytes": max_bytes,
        }

    @staticmethod
    def _coerce_int(
        value: Any,
        field_name: str,
        *,
        default: int,
        minimum: int,
        maximum: int | None,
    ) -> int:
        if value is None:
            parsed = default
        else:
            try:
                parsed = int(value)
            except (TypeError, ValueError) as exc:
                raise ToolExecutionError(f"'{field_name}' must be an integer.", recoverable=True) from exc

        if parsed < minimum:
            raise ToolExecutionError(f"'{field_name}' must be at least {minimum}.", recoverable=True)
        if maximum is not None and parsed > maximum:
            raise ToolExecutionError(f"'{field_name}' must be at most {maximum}.", recoverable=True)

        return parsed
