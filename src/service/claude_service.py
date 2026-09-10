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


class ToolUseStarted:
    """
    Marker yielded by a TurnStream the moment the model opens a tool_use block.

    It arrives after the round's text and before the (often very long) tool
    arguments. That position is the whole point: it is the earliest moment a
    reader can know that the text it has seen so far was a pre-tool
    acknowledgment and not the answer, which is what lets the agent loop speak
    the acknowledgment now instead of after the arguments finish.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "TOOL_USE_STARTED"


TOOL_USE_STARTED = ToolUseStarted()

# Model families that take `output_config.effort`. Everything older (Haiku 4.5,
# the 4.5 line and before) rejects the parameter outright.
_EFFORT_MODEL_PREFIXES = (
    "claude-opus-5",
    "claude-sonnet-5",
    "claude-fable-5",
    "claude-mythos-5",
    "claude-opus-4-6",
    "claude-opus-4-7",
    "claude-opus-4-8",
    "claude-sonnet-4-6",
)
_EFFORT_LEVELS = {"low", "medium", "high", "xhigh", "max"}


class TurnStream:
    """
    One model turn, readable while it is still being written.

    Iterating yields text deltas in arrival order, plus a `TOOL_USE_STARTED`
    marker at the point the model begins a tool call. Once iteration finishes,
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

    def __iter__(self) -> Iterator[str | ToolUseStarted]:
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

        # The SDK stream is iterated event by event rather than through
        # `text_stream`, because the latter hides the one non-text event this
        # needs: the start of a tool_use block. Text deltas are surfaced as
        # the SDK's synthetic `text` events; thinking, citations and tool
        # argument JSON all pass by unyielded.
        with self._open_stream() as stream:
            for event in stream:
                event_type = getattr(event, "type", None)
                if event_type == "text":
                    delta = getattr(event, "text", "")
                    if delta:
                        yield delta
                elif event_type == "content_block_start":
                    block = getattr(event, "content_block", None)
                    if getattr(block, "type", None) == "tool_use":
                        yield TOOL_USE_STARTED
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
        # Imported here rather than at module scope: SettingsService is
        # reached from controllers that already import this module.
        from src.service.settings_service import SettingsService

        self.settings_service = SettingsService()
        self.MODEL = self.settings_service.get_current_model()
        # Thinking tokens count against this on the models that think, and a
        # tool call cut off mid-JSON is a failed turn, so the ceiling leaves
        # room for both. Every request streams, so the size costs nothing.
        self.max_tokens = int(os.getenv("CLAUDE_MAX_TOKENS", "8192"))
        # How hard the model thinks before it writes. Nova's replies are
        # spoken, and the first word cannot go out until thinking ends, so the
        # default is the low end — a conversational turn does not need the
        # deliberation a coding task does. Only sent to models that take it.
        # Namespaced because a bare CLAUDE_EFFORT is set by other tooling.
        self.effort = (os.getenv("NOVA_CLAUDE_EFFORT") or "low").strip().lower()
        if self.effort not in _EFFORT_LEVELS:
            print(f"Unknown NOVA_CLAUDE_EFFORT {self.effort!r}; using 'low'.")
            self.effort = "low"
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

    def set_model(self, model: str) -> bool:
        """
        Switch the model used for Claude API calls.

        Returns False for a model that is not in the allowed list, so a bad
        value from a controller cannot leave the service pointing at a model
        the API will reject on the next turn.
        """
        if self.settings_service.set_current_model(model):
            self.MODEL = model
            return True
        return False

    def get_available_models(self) -> list[str]:
        """The model ids a caller is allowed to switch to."""
        return self.settings_service.get_available_models()

    def get_model_options(self) -> list[dict[str, str]]:
        """The same models as {id, display_name}, for a picker to render."""
        return self.settings_service.get_model_options()

    def get_current_model_name(self) -> str:
        """The display name of the current model, for showing rather than storing."""
        return self.settings_service.display_name_for(self.MODEL)

    def get_current_model_id(self) -> str:
        """
        The listed id the current model resolves to.

        A picker matches its options against this, not against the stored
        value: an alias matches no option, and a <select> whose value matches
        nothing silently displays its first entry — claiming Fable 5.1 while
        Haiku is what is actually selected.
        """
        return self.settings_service.resolve_model(self.MODEL) or self.MODEL

    def get_current_model(self) -> str:
        """The model this service is currently pointing at."""
        return self.MODEL

    def _generation_kwargs(self) -> dict[str, Any]:
        """
        Per-model generation settings.

        Opus 5 and Sonnet 5 think by default, at `high` effort, with the
        thinking hidden — which from a voice turn's point of view is a long
        silence before the first word, since the `<speak>` line cannot start
        until the thinking is done. `effort` is the lever that shortens it;
        thinking itself is left adaptive, because switching it off entirely
        on these models can push tool calls into visible text. Haiku 4.5 and
        older models reject the parameter, so they get nothing here.

        Matched on the configured id as-is. Both forms it takes — the alias
        (`claude-haiku-4-5`) and the dated snapshot it resolves to — share
        the family prefix, and resolving it properly means the Models API,
        which has no place on the path of every request.
        """
        if self.MODEL.startswith(_EFFORT_MODEL_PREFIXES):
            return {"output_config": {"effort": self.effort}}
        return {}

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
            **self._generation_kwargs(),
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
            **self._generation_kwargs(),
            **self._build_kwargs(tools, system, mcp_servers),
        )
        if mcp_servers:
            return self.client.beta.messages.create(
                betas=[MCP_CONNECTOR_BETA], **params
            )
        return self.client.messages.create(**params)
