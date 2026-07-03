from __future__ import annotations

import importlib
import inspect
from typing import Any

from src.dao.tool_dao import ToolDao
from src.model.tool import Tool
from src.model.tool_config import ToolConfig


class ToolExecutionError(Exception):
    def __init__(self, message: str, recoverable: bool = True) -> None:
        super().__init__(message)
        self.recoverable = recoverable


class ToolService:
    def __init__(self) -> None:
        self.tool_dao = ToolDao()

    def list_tools(self) -> list[Tool]:
        return self.tool_dao.get_all()

    def add_tool(
        self,
        name: str,
        description: str | None = None,
        config: ToolConfig | dict[str, Any] | None = None,
    ) -> Tool:
        validated_config = self._validate_config(config)
        return self.tool_dao.create(
            Tool(
                name=name,
                description=description,
                config=validated_config.model_dump(mode="json"),
            )
        )

    def call_tool(self, tool: Tool, arguments: dict[str, Any]) -> Any:
        if not isinstance(arguments, dict):
            raise ToolExecutionError("Tool arguments must be a JSON object.", recoverable=True)

        tool_config = self._validate_config(tool.config)
        method = self._resolve_callable(tool_config.callable_path)
        method_kwargs = self._build_call_kwargs(tool_config, arguments)
        tool_name = (tool.name or "").strip() or tool_config.callable_path

        try:
            inspect.signature(method).bind(**method_kwargs)
        except TypeError as exc:
            raise ToolExecutionError(
                f"Tool '{tool_name}' arguments did not match '{tool_config.callable_path}': {str(exc)}",
                recoverable=True,
            ) from exc

        try:
            result = method(**method_kwargs)
        except ToolExecutionError:
            raise
        except Exception as exc:
            raise ToolExecutionError(f"Tool '{tool_name}' failed: {str(exc)}", recoverable=True) from exc

        if inspect.isawaitable(result):
            raise ToolExecutionError(
                f"Tool '{tool_name}' mapped to async callable '{tool_config.callable_path}', which is not supported.",
                recoverable=False,
            )

        return result

    def _validate_config(self, config: ToolConfig | dict[str, Any] | None) -> ToolConfig:
        if config is None:
            raise ToolExecutionError("Tool config is required.", recoverable=False)

        try:
            if isinstance(config, ToolConfig):
                return config
            return ToolConfig.model_validate(config)
        except Exception as exc:
            raise ToolExecutionError(f"Invalid tool config: {str(exc)}", recoverable=False) from exc

    @staticmethod
    def _resolve_callable(callable_path: str) -> Any:
        try:
            module_name, class_name, method_name = callable_path.rsplit(".", 2)
        except ValueError as exc:
            raise ToolExecutionError(
                f"Invalid callable_path '{callable_path}'. Expected 'module.Class.method'.",
                recoverable=False,
            ) from exc

        if class_name.startswith("_") or method_name.startswith("_"):
            raise ToolExecutionError(f"Invalid callable_path '{callable_path}'.", recoverable=False)

        try:
            module = importlib.import_module(module_name)
            service_class = getattr(module, class_name)
        except Exception as exc:
            raise ToolExecutionError(
                f"Failed to import callable '{callable_path}': {str(exc)}",
                recoverable=False,
            ) from exc

        try:
            instance = service_class()
        except Exception as exc:
            raise ToolExecutionError(
                f"Failed to initialize callable class '{module_name}.{class_name}': {str(exc)}",
                recoverable=False,
            ) from exc

        method = getattr(instance, method_name, None)
        if method is None or not callable(method):
            raise ToolExecutionError(
                f"Callable '{callable_path}' does not resolve to a public callable method.",
                recoverable=False,
            )
        return method

    @staticmethod
    def _build_call_kwargs(tool_config: ToolConfig, arguments: dict[str, Any]) -> dict[str, Any]:
        method_kwargs = dict(tool_config.static_kwargs)

        for argument_name, value in arguments.items():
            target_name = tool_config.argument_map.get(argument_name, argument_name)
            if target_name in method_kwargs:
                raise ToolExecutionError(
                    f"Tool argument '{argument_name}' conflicts with static kwarg '{target_name}'.",
                    recoverable=False,
                )
            method_kwargs[target_name] = value

        return method_kwargs
