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
        self._message = message
        self._drained = message is not None
        self._started = False

    def __iter__(self) -> Iterator[str]:
        if self._open_stream is None:
            # An already-complete turn. Replay its text so anything watching
            # the stream sees the same content — all at once, which is what a
            # non-streaming turn is.
            replay = "".join(
                block.text
                for block in (self._message.content if self._message else [])
                if getattr(block, "text", None)
            )
            if replay:
                yield replay
            return

        if self._started:
            raise RuntimeError("A TurnStream can only be read once.")
        self._started = True

        with self._open_stream() as stream:
            for delta in stream.text_stream:
                if delta:
                    yield delta
            self._message = stream.get_final_message()
        self._drained = True

    @property
    def message(self) -> Message:
        """The assembled turn. Available only after the stream is drained."""
        if not self._drained or self._message is None:
            raise RuntimeError(
                "TurnStream.message is not available until the stream has been "
                "read to completion."
            )
        return self._message

    @classmethod
    def completed(cls, message: Message) -> "TurnStream":
        """A turn that is already whole, for callers with no live connection."""
        return cls(message=message)


class ClaudeService:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        self.MODEL = 'claude-haiku-4-5'
        self.max_tokens = int(os.getenv("CLAUDE_MAX_TOKENS", "4096"))
        self.web_search_enabled = _env_flag("CLAUDE_WEB_SEARCH_ENABLED", True)
        self.web_search_max_uses = int(os.getenv("CLAUDE_WEB_SEARCH_MAX_USES", "5"))

    def web_search_tool(self) -> dict[str, Any]:
        """
        Web search tool definition.

        Anthropic runs the search server-side and feeds results back to the
        model within the same request, so there is nothing for ToolService to
        execute. Optional domain filtering (allowed_domains / blocked_domains,
        never both) and user_location can be added here.
        """
        return {
            "type": WEB_SEARCH_TOOL_TYPE,
            "name": WEB_SEARCH_TOOL_NAME,
            "max_uses": self.web_search_max_uses,
        }

    def _build_tools(self, tools: Optional[list]) -> Optional[list]:
        """Combine caller-supplied client tools with Anthropic's server tools."""
        combined = list(tools or [])
        if self.web_search_enabled:
            combined.append(self.web_search_tool())
        return combined or None

    def _build_messages(self, prompt: str, context: Optional[list]) -> list:
        messages = []
        if context:
            messages.extend(context)
        # Empty prompt is used by the ReAct sub-agent loop once history already
        # contains the full turn (assistant tool_use + user tool_result blocks).
        if prompt:
            messages.append({"role": "user", "content": prompt})
        return messages

    def _build_kwargs(
        self,
        tools: Optional[list],
        system: Optional[str | list],
        mcp_servers: Optional[list] = None,
    ) -> dict[str, Any]:
        """
        Assemble optional request kwargs.

        `system` steers a single request without entering the message history,
        which matters because chat and speech share one conversation — a
        "be brief" instruction meant for a spoken turn must not linger and
        shorten later typed replies. It accepts either a plain string or a
        list of system content blocks (the Messages API supports both); the
        block form lets callers put a cache_control breakpoint on the stable
        part of the prompt.

        `mcp_servers` is a list of {name, url, authorization_token?} dicts.
        The API requires the two halves together: the mcp_servers request
        parameter AND one mcp_toolset tools entry per server — a server
        without its toolset is rejected as a validation error, so this
        method derives the toolsets rather than trusting callers to pair
        them. Entries are sorted by name to keep the tool list byte-stable
        for prompt caching.
        """
        kwargs: dict[str, Any] = {}
        combined_tools = self._build_tools(tools)

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
