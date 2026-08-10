from anthropic import Anthropic
import os
from typing import Any, Optional
from anthropic.types.message import Message

# Server-side tool executed by Anthropic, not by ToolService. Results come back
# as server_tool_use / web_search_tool_result blocks in the same response.
WEB_SEARCH_TOOL_TYPE = "web_search_20250305"
WEB_SEARCH_TOOL_NAME = "web_search"


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"false", "0", "no", "off"}


class ClaudeService:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        self.MODEL = 'claude-sonnet-5'
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
        self, tools: Optional[list], system: Optional[str]
    ) -> dict[str, Any]:
        """
        Assemble optional request kwargs.

        `system` steers a single request without entering the message history,
        which matters because chat and speech share one conversation — a
        "be brief" instruction meant for a spoken turn must not linger and
        shorten later typed replies.
        """
        kwargs: dict[str, Any] = {}
        combined_tools = self._build_tools(tools)
        if combined_tools:
            kwargs["tools"] = combined_tools
        if system and system.strip():
            kwargs["system"] = system
        return kwargs

    def stream_response(
        self,
        prompt: str,
        role: Optional[str] = None,
        context: Optional[list] = None,
        tools: Optional[list] = None,
        system: Optional[str] = None,
    ) -> Message:
        """
        Stream a response from the Claude API and return the final Message.

        Uses the streaming endpoint so the connection stays open for longer
        generations, then returns the complete message (including tool_use).
        """
        with self.client.messages.stream(
            model=self.MODEL,
            messages=self._build_messages(prompt, context),
            max_tokens=self.max_tokens,
            **self._build_kwargs(tools, system),
        ) as stream:
            return stream.get_final_message()

    def get_response(
        self,
        prompt: str,
        role: Optional[str] = None,
        context: Optional[list] = None,
        tools: Optional[list] = None,
        system: Optional[str] = None,
    ) -> Message:
        """
        Get a response from the Claude API.

        Args:
            prompt: The prompt to send to the Claude API.
            role: The role of the user.
            context: The context of the conversation.
            system: Per-request steering that stays out of message history.
        """
        return self.client.messages.create(
            model=self.MODEL,
            messages=self._build_messages(prompt, context),
            max_tokens=self.max_tokens,
            cache_control={"type": "ephemeral"},
            **self._build_kwargs(tools, system),
        )
