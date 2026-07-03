import unittest

from src.model.tool import Tool
from src.service.tool_service import ToolExecutionError, ToolService


class FakeToolDao:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self.tools = tools or []
        self.created: Tool | None = None

    def get_all(self) -> list[Tool]:
        return list(self.tools)

    def create(self, entity: Tool) -> Tool:
        self.created = entity
        return Tool(id=1, name=entity.name, description=entity.description, config=entity.config)


class DemoService:
    def combine(self, message: str, prefix: str = "", suffix: str = "") -> dict[str, str]:
        return {"text": f"{prefix}{message}{suffix}"}

    def ping(self) -> dict[str, bool]:
        return {"ok": True}

    def _hidden(self) -> dict[str, bool]:
        return {"hidden": True}


class ToolServiceTests(unittest.TestCase):
    def _build_service(self, tools: list[Tool] | None = None) -> ToolService:
        service = ToolService.__new__(ToolService)
        service.tool_dao = FakeToolDao(tools)
        return service

    def _config(self, **overrides) -> dict:
        config = {
            "type": "service_method",
            "callable_path": "tests.test_tool_service.DemoService.combine",
            "input_schema": {
                "type": "object",
                "properties": {
                    "body": {"type": "string"},
                    "lead": {"type": "string"},
                },
                "required": ["body"],
                "additionalProperties": False,
            },
            "static_kwargs": {"suffix": "!"},
            "argument_map": {"body": "message", "lead": "prefix"},
        }
        config.update(overrides)
        return config

    def test_add_tool_validates_and_persists_config(self):
        service = self._build_service()

        created = service.add_tool(
            name="demo_tool",
            description="Demo tool",
            config=self._config(),
        )

        self.assertEqual(created.id, 1)
        self.assertIsNotNone(service.tool_dao.created)
        self.assertEqual(service.tool_dao.created.config["type"], "service_method")
        self.assertEqual(service.tool_dao.created.config["callable_path"], "tests.test_tool_service.DemoService.combine")

    def test_add_tool_rejects_invalid_config(self):
        service = self._build_service()

        with self.assertRaises(ToolExecutionError) as ctx:
            service.add_tool(
                name="bad_tool",
                description="Broken tool",
                config={"type": "service_method", "callable_path": "tests.test_tool_service.DemoService.combine"},
            )

        self.assertIn("Invalid tool config", str(ctx.exception))

    def test_call_tool_dispatches_to_service_method(self):
        tool = Tool(name="demo_tool", description="Demo", config=self._config())
        service = self._build_service([tool])

        result = service.call_tool(tool, {"body": "world", "lead": "hello "})

        self.assertEqual(result, {"text": "hello world!"})

    def test_call_tool_errors_on_invalid_callable_path(self):
        tool = Tool(name="demo_tool", description="Demo", config=self._config(callable_path="bad_path"))
        service = self._build_service([tool])

        with self.assertRaises(ToolExecutionError) as ctx:
            service.call_tool(tool, {"body": "world"})

        self.assertIn("Invalid callable_path", str(ctx.exception))

    def test_call_tool_errors_on_missing_method(self):
        tool = Tool(
            name="demo_tool",
            description="Demo",
            config=self._config(callable_path="tests.test_tool_service.DemoService.missing_method"),
        )
        service = self._build_service([tool])

        with self.assertRaises(ToolExecutionError) as ctx:
            service.call_tool(tool, {"body": "world"})

        self.assertIn("does not resolve", str(ctx.exception))

    def test_call_tool_rejects_private_method(self):
        tool = Tool(
            name="demo_tool",
            description="Demo",
            config=self._config(callable_path="tests.test_tool_service.DemoService._hidden"),
        )
        service = self._build_service([tool])

        with self.assertRaises(ToolExecutionError) as ctx:
            service.call_tool(tool, {"body": "world"})

        self.assertIn("Invalid callable_path", str(ctx.exception))

    def test_call_tool_errors_on_bad_argument_mapping(self):
        tool = Tool(
            name="demo_tool",
            description="Demo",
            config=self._config(argument_map={"body": "unknown_kwarg"}),
        )
        service = self._build_service([tool])

        with self.assertRaises(ToolExecutionError) as ctx:
            service.call_tool(tool, {"body": "world"})

        self.assertIn("arguments did not match", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
