from anthropic import Anthropic
import os
from collections.abc import Callable, Iterator
from typing import Any, Optional
from anthropic.types.message import Message

# Server-side tool executed by Anthropic, not by ToolService. Results come back
# as server_tool_use / web_search_tool_result blocks in the same response.
WEB_SEARCH_TOOL_TYPE = "web_search_20250305"
WEB_SEARCH_TOOL_NAME = "web_search"

# MCP connector: like web search, Anthropic makes the MCP round-trip
# server-side and returns mcp_tool_use / mcp_tool_result blocks inline.
# Requests that declare mcp_servers must go through the beta endpoint with
# this flag, and every declared server must be referenced by exactly one
# mcp_toolset entry in tools.
MCP_CONNECTOR_BETA = "mcp-client-2025-11-20"


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"false", "0", "no", "off"}


class TurnStream:
    """
    One model turn, readable while it is still being written.

    Iterating yields text deltas in arrival order. Once iteration finishes,
    `message` holds the assembled Message — the content blocks and tool_use
    the agent loop needs to decide what happens next.

    The shape exists for latency. This used to open a stream and throw every
    delta away, returning only `get_final_message()`, which meant nothing at
    all could happen until the last token of a reply had been written. For a
    voice turn that is the entire cost: the two sentences Nova says out loud
    are finished long before the markdown answer beneath them, and waiting for
    the answer to speak the summary is waiting for no reason.

    Read once, all the way through. A partly-consumed stream has no `message`,
    because the turn genuinely has no answer yet.
    """

    def __init__(
        self,
        open_stream: Optional[Callable[[], Any]] = None,
        message: Optional[Message] = None,
    ) -> None:
        self._open_stream = open_stream
        self.message: Optional[Message] = message
        self._iterator: Optional[Iterator] = None

    def __iter__(self) -> Iterator[str]:
        """
        Stream text deltas as the model writes them.

        Each item is a text delta fragment. Iteration is single-pass; after
        reading all deltas, call .message to get the complete response.
        """
        if self._open_stream is None:
            # Already have a canned message
            return iter([])

        with self._open_stream() as stream:
            for event in stream:
                # Anthropic stream is a flux of events; text deltas are
                # content_block_delta / delta.type = "text_delta" / delta.text.
                if (
                    hasattr(event, "type")
                    and event.type == "content_block_delta"
                    and hasattr(event, "delta")
                    and hasattr(event.delta, "type")
                    and event.delta.type == "text_delta"
                ):
                    yield event.delta.text

                # Capture the final message once the stream is closed.
                if (
                    hasattr(event, "type")
                    and event.type == "message_stop"
                    and hasattr(event, "message")
                ):
                    self.message = event.message

        return self


class ClaudeService:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        # Import here to avoid circular imports
        from src.service.settings_service import SettingsService
        self.settings_service = SettingsService()
        self.MODEL = self.settings_service.get_current_model()
        self.max_tokens = int(os.getenv("CLAUDE_MAX_TOKENS", "4096"))
        self.web_search_enabled = _env_flag("CLAUDE_WEB_SEARCH_ENABLED", True)
        self.web_search_max_uses = int(os.getenv("CLAUDE_WEB_SEARCH_MAX_USES", "5"))

    def web_search_tool(self) -> dict[str, Any]:
        """
        Web search tool definition.

        Anthropic runs the search server-side and feeds results back to the
        model within the same request, so there is nothing for ToolService to
        do here — the tool returns directly to the model. A tool definition
        is supplied to the API anyway, for the price of one of the model's
        max_tokens.
        """
        return {
            "type": "text",
            "text": f"""The `web_search` tool is available to you for research.
Anthropic runs the search and returns results directly to the model.

DO NOT mention the tool itself in your response to the user.""",
        }

    def set_model(self, model: str) -> bool:
        """
        Switch the model used for Claude API calls.

        Args:
            model: The model to switch to.

        Returns:
            True if successful, False if invalid model.
        """
        if self.settings_service.set_current_model(model):
            self.MODEL = model
            return True
        return False

    def get_available_models(self) -> list[str]:
        """Get list of available models."""
        return self.settings_service.get_available_models()

    def get_current_model(self) -> str:
        """Get the currently selected model."""
        return self.MODEL

    def _build_messages(self, prompt: str, context: Optional[list] = None) -> list:
        """Build message list from prompt and context."""
        messages: list[dict[str, Any]] = []
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": prompt})
        return messages

    def _build_kwargs(
        self,
        tools: Optional[list] = None,
        system: Optional[str | list] = None,
        mcp_servers: Optional[list] = None,
    ) -> dict[str, Any]:
        """Build kwargs for API request."""
        kwargs: dict[str, Any] = {}

        combined_tools: list[dict[str, Any]] = []

        if self.web_search_enabled and self.web_search_max_uses > 0:
            combined_tools.append(
                {
                    "type": "text",
                    "text": f"Web search tool: max {self.web_search_max_uses} uses per turn.",
                }
            )

        if tools:
            combined_tools.extend(tools)

        if mcp_servers:
            server_entries: list[dict[str, Any]] = []
            toolsets: list[dict[str, Any]] = []
            for server in sorted(mcp_servers, key=lambda entry: entry["name"]):
                entry: dict[str, Any] = {
                    "type": "url",
                    "name": server["name"],
                    "url": server["url"],
                }
                if server.get("authorization_token"):
                    entry["authorization_token"] = server["authorization_token"]
                server_entries.append(entry)
                toolsets.append(
                    {"type": "mcp_toolset", "mcp_server_name": server["name"]}
                )
            kwargs["mcp_servers"] = server_entries
            combined_tools = (combined_tools or []) + toolsets
            print(f"mcp_servers: {server_entries}")

        if combined_tools:
            kwargs["tools"] = combined_tools
        if isinstance(system, str):
            if system.strip():
                kwargs["system"] = system
        elif system:
            kwargs["system"] = system
        return kwargs

    def stream_response(
        self,
        prompt: str,
        role: Optional[str] = None,
        context: Optional[list] = None,
        tools: Optional[list] = None,
        system: Optional[str | list] = None,
        mcp_servers: Optional[list] = None,
    ) -> TurnStream:
        """
        Open a streaming turn against the Claude API.

        Returns a `TurnStream`: iterate it for text deltas as the model writes
        them, then read `.message` for the complete message including tool_use.
        Nothing is sent until iteration begins.

        The connection stays open for the length of the generation either way;
        what changed is that the caller now gets to see the reply take shape
        instead of only its final form. The top-level cache_control auto-caches
        the last cacheable block, so the growing conversation history is served
        from cache turn over turn. Requests that declare MCP servers go through
        the beta endpoint with the connector flag; everything else stays on the
        GA endpoint.
        """
        params: dict[str, Any] = dict(
            model=self.MODEL,
            messages=self._build_messages(prompt, context),
            max_tokens=self.max_tokens,
            cache_control={"type": "ephemeral"},
            **self._build_kwargs(tools, system, mcp_servers),
        )
        if mcp_servers:
            return TurnStream(
                lambda: self.client.beta.messages.stream(
                    betas=[MCP_CONNECTOR_BETA], **params
                )
            )
        return TurnStream(lambda: self.client.messages.stream(**params))

    def get_response(
        self,
        prompt: str,
        role: Optional[str] = None,
        context: Optional[list] = None,
        tools: Optional[list] = None,
        system: Optional[str | list] = None,
        mcp_servers: Optional[list] = None,
    ) -> Message:
        """
        Get a response from the Claude API.

        Args:
            prompt: The prompt to send to the Claude API.
            role: The role of the user.
            context: The context of the conversation.
            system: Per-request steering that stays out of message history.
            mcp_servers: Remote MCP servers ({name, url, authorization_token?})
                to expose through Claude's server-side MCP connector.
        """
        params: dict[str, Any] = dict(
            model=self.MODEL,
            messages=self._build_messages(prompt, context),
            max_tokens=self.max_tokens,
            cache_control={"type": "ephemeral"},
            **self._build_kwargs(tools, system, mcp_servers),
        )
        if mcp_servers:
            return self.client.beta.messages.create(
                betas=[MCP_CONNECTOR_BETA], **params
            )
        return self.client.messages.create(**params)
