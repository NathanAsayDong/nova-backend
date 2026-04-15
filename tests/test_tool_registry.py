import json
import tempfile
import unittest
from pathlib import Path

from src.service.cursor_service import CursorServiceError
from src.service.github_service import GithubServiceError
from src.service.tool_registry import ToolExecutionError, ToolRegistry


class _FakeCursorService:
    def __init__(self) -> None:
        self.launch_kwargs = None

    def launch_agent(self, **kwargs):
        self.launch_kwargs = kwargs
        return {"id": "bc_123", "status": "RUNNING"}

    def get_agent_status(self, agent_id: str):
        return {"id": agent_id, "status": "RUNNING"}

    def get_agent_conversation(self, agent_id: str):
        return {"id": agent_id, "messages": [{"type": "assistant_message", "text": "Working..."}]}


class _FakeGithubService:
    def __init__(self) -> None:
        self.pull_request_kwargs = None
        self.list_repo_kwargs = None
        self.read_code_kwargs = None

    @staticmethod
    def normalize_repository_url(repository_url: str) -> str:
        return repository_url.replace(".git", "")

    def list_pull_requests(self, **kwargs):
        self.pull_request_kwargs = kwargs
        return [{"number": 101, "title": "Test PR"}]

    def list_repositories(self, **kwargs):
        self.list_repo_kwargs = kwargs
        return [{"full_name": "acme/api", "url": "https://github.com/acme/api"}]

    def read_repository_code(self, **kwargs):
        self.read_code_kwargs = kwargs
        return {
            "repository_url": kwargs["repository_url"],
            "path": kwargs.get("path") or "",
            "ref": kwargs.get("ref"),
            "kind": "file",
            "name": "main.py",
            "size": 13,
            "url": "https://github.com/acme/api/blob/main/main.py",
            "encoding": "utf-8",
            "content": 'print("ok")\\n',
            "truncated": False,
            "content_bytes_returned": 12,
            "content_bytes_total": 12,
        }


class ToolRegistryTests(unittest.TestCase):
    def _write_tool(self, tools_dir: Path, payload: dict) -> None:
        file_path = tools_dir / f"{payload['name']}.txt"
        file_path.write_text(json.dumps(payload), encoding="utf-8")

    def _tool_payload(self, name: str = "demo_tool", enabled: bool = True, handler_id: str = "get_current_time_handler") -> dict:
        return {
            "name": name,
            "description": "Demo tool",
            "enabled": enabled,
            "handler_id": handler_id,
            "json_schema": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        }

    def test_loads_valid_txt_tool_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tools_dir = Path(temp_dir)
            self._write_tool(tools_dir, self._tool_payload())

            registry = ToolRegistry(tools_dir=tools_dir)
            names = {tool["name"] for tool in registry.list_tools()}
            self.assertIn("demo_tool", names)

    def test_name_must_match_filename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tools_dir = Path(temp_dir)
            payload = self._tool_payload(name="internal_name")
            (tools_dir / "different_name.txt").write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(ValueError):
                ToolRegistry(tools_dir=tools_dir)

    def test_set_enabled_persists_to_disk(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tools_dir = Path(temp_dir)
            payload = self._tool_payload(name="toggle_tool", enabled=True)
            self._write_tool(tools_dir, payload)

            registry = ToolRegistry(tools_dir=tools_dir)
            registry.set_enabled("toggle_tool", False)

            file_payload = json.loads((tools_dir / "toggle_tool.txt").read_text(encoding="utf-8"))
            self.assertFalse(file_payload["enabled"])

    def test_as_openai_tools_only_returns_enabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tools_dir = Path(temp_dir)
            self._write_tool(tools_dir, self._tool_payload(name="on_tool", enabled=True))
            self._write_tool(tools_dir, self._tool_payload(name="off_tool", enabled=False))

            registry = ToolRegistry(tools_dir=tools_dir)
            tool_names = {tool["name"] for tool in registry.as_openai_tools()}
            self.assertIn("on_tool", tool_names)
            self.assertNotIn("off_tool", tool_names)

    def test_disabled_tool_execution_is_recoverable_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tools_dir = Path(temp_dir)
            self._write_tool(tools_dir, self._tool_payload(name="off_tool", enabled=False))
            registry = ToolRegistry(tools_dir=tools_dir)

            with self.assertRaises(ToolExecutionError) as ctx:
                registry.execute("off_tool", {})

            self.assertTrue(ctx.exception.recoverable)

    def test_default_agentic_tools_are_bootstrapped(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = ToolRegistry(tools_dir=Path(temp_dir))
            names = {tool["name"] for tool in registry.list_tools()}
            self.assertTrue(
                {
                    "write_code",
                    "check_prs",
                    "check_coding_agent",
                    "code_planner",
                    "github_list_repos",
                    "github_read_repo_code",
                }.issubset(names)
            )

    def test_openai_strict_schema_requires_all_properties(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = ToolRegistry(tools_dir=Path(temp_dir))
            openai_tools = registry.as_openai_tools()
            by_name = {tool["name"]: tool for tool in openai_tools}

            check_tool = by_name["check_coding_agent"]
            required_fields = set(check_tool["parameters"]["required"])
            self.assertEqual(required_fields, {"agent_id", "include_conversation"})

            include_schema = check_tool["parameters"]["properties"]["include_conversation"]
            self.assertIn("null", include_schema["type"])

    def test_write_code_handler_executes_cursor_service(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = ToolRegistry(tools_dir=Path(temp_dir))
            fake_cursor = _FakeCursorService()
            fake_github = _FakeGithubService()
            registry.cursor_service = fake_cursor
            registry.github_service = fake_github

            result = registry.execute(
                "write_code",
                {
                    "prompt": "Add tests",
                    "repository_url": "https://github.com/acme/api.git",
                    "ref": "main",
                },
            )

            self.assertEqual(result["status"], "submitted")
            self.assertEqual(result["agent_id"], "bc_123")
            self.assertEqual(fake_cursor.launch_kwargs["repository_url"], "https://github.com/acme/api")

    def test_write_code_defaults_auto_create_pr_to_true_when_null(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = ToolRegistry(tools_dir=Path(temp_dir))
            fake_cursor = _FakeCursorService()
            registry.cursor_service = fake_cursor
            registry.github_service = _FakeGithubService()

            registry.execute(
                "write_code",
                {
                    "prompt": "Add tests",
                    "repository_url": "https://github.com/acme/api",
                    "auto_create_pr": None,
                },
            )

            self.assertTrue(fake_cursor.launch_kwargs["auto_create_pr"])

    def test_check_prs_handler_executes_github_service(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = ToolRegistry(tools_dir=Path(temp_dir))
            fake_github = _FakeGithubService()
            registry.github_service = fake_github

            result = registry.execute(
                "check_prs",
                {
                    "repository_url": "https://github.com/acme/api",
                    "state": "open",
                    "limit": 10,
                    "page": 2,
                },
            )

            self.assertEqual(result["count"], 1)
            self.assertEqual(fake_github.pull_request_kwargs["state"], "open")
            self.assertEqual(fake_github.pull_request_kwargs["per_page"], 10)
            self.assertEqual(fake_github.pull_request_kwargs["page"], 2)

    def test_check_coding_agent_can_include_conversation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = ToolRegistry(tools_dir=Path(temp_dir))
            registry.cursor_service = _FakeCursorService()

            result = registry.execute(
                "check_coding_agent",
                {
                    "agent_id": "bc_abc123",
                    "include_conversation": True,
                },
            )

            self.assertEqual(result["agent_id"], "bc_abc123")
            self.assertIn("conversation", result)

    def test_github_read_repo_code_handler_executes_github_service(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = ToolRegistry(tools_dir=Path(temp_dir))
            fake_github = _FakeGithubService()
            registry.github_service = fake_github

            result = registry.execute(
                "github_read_repo_code",
                {
                    "repository_url": "https://github.com/acme/api.git",
                    "path": "main.py",
                    "ref": "main",
                    "max_bytes": 2048,
                },
            )

            self.assertEqual(result["kind"], "file")
            self.assertEqual(result["path"], "main.py")
            self.assertEqual(fake_github.read_code_kwargs["repository_url"], "https://github.com/acme/api")
            self.assertEqual(fake_github.read_code_kwargs["max_bytes"], 2048)

    def test_external_service_errors_are_recoverable(self):
        class _BrokenCursor:
            @staticmethod
            def launch_agent(**kwargs):
                raise CursorServiceError("Cursor upstream unavailable")

        with tempfile.TemporaryDirectory() as temp_dir:
            registry = ToolRegistry(tools_dir=Path(temp_dir))
            registry.cursor_service = _BrokenCursor()
            registry.github_service = _FakeGithubService()

            with self.assertRaises(ToolExecutionError) as ctx:
                registry.execute(
                    "write_code",
                    {
                        "prompt": "Do work",
                        "repository_url": "https://github.com/acme/api",
                    },
                )

            self.assertTrue(ctx.exception.recoverable)

    def test_github_service_errors_are_recoverable(self):
        class _BrokenGithub:
            @staticmethod
            def normalize_repository_url(repository_url: str) -> str:
                return repository_url

            @staticmethod
            def list_repositories(**kwargs):
                raise GithubServiceError("GitHub token invalid")

        with tempfile.TemporaryDirectory() as temp_dir:
            registry = ToolRegistry(tools_dir=Path(temp_dir))
            registry.github_service = _BrokenGithub()

            with self.assertRaises(ToolExecutionError) as ctx:
                registry.execute("github_list_repos", {})

            self.assertTrue(ctx.exception.recoverable)


if __name__ == "__main__":
    unittest.main()
