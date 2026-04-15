from pathlib import Path
from typing import Any

from src.service.tool_registry import ToolExecutionError, ToolRegistry


class ToolService:
    def __init__(self, tools_dir: Path | None = None, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or ToolRegistry(tools_dir=tools_dir)

    def list_tools(self) -> list[dict[str, Any]]:
        return self.registry.list_tools()

    def set_enabled(self, name: str, enabled: bool) -> dict[str, Any]:
        return self.registry.set_enabled(name, enabled)

    def as_openai_tools(self) -> list[dict[str, Any]]:
        tools = self.registry.as_openai_tools()
        tools.append({ "type": "web_search" })
        return tools

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.registry.execute(name, arguments)


tool_service = ToolService()

__all__ = ["ToolService", "ToolExecutionError", "tool_service"]
