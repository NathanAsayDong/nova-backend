from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ServiceMethodToolConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["service_method"] = "service_method"
    callable_path: str
    input_schema: dict[str, Any]
    static_kwargs: dict[str, Any] = Field(default_factory=dict)
    argument_map: dict[str, str] = Field(default_factory=dict)

    @field_validator("callable_path")
    @classmethod
    def _validate_callable_path(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized

    @field_validator("input_schema")
    @classmethod
    def _validate_input_schema(cls, value: dict[str, Any]) -> dict[str, Any]:
        if value.get("type") != "object":
            raise ValueError("input_schema.type must be 'object'")
        if not isinstance(value.get("properties"), dict):
            raise ValueError("input_schema.properties must be a dictionary")

        required = value.get("required", [])
        if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
            raise ValueError("input_schema.required must be a list of strings")

        additional_properties = value.get("additionalProperties")
        if additional_properties is not None and not isinstance(additional_properties, bool):
            raise ValueError("input_schema.additionalProperties must be a boolean when provided")

        return value

    @field_validator("argument_map")
    @classmethod
    def _validate_argument_map(cls, value: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for source_name, target_name in value.items():
            source = source_name.strip()
            target = target_name.strip()
            if not source or not target:
                raise ValueError("argument_map keys and values must not be empty")
            normalized[source] = target
        return normalized


ToolConfig = ServiceMethodToolConfig


__all__ = ["ServiceMethodToolConfig", "ToolConfig"]
