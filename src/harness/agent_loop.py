import json
import re
import time
from collections.abc import Iterable, Iterator
from typing import Any
from uuid import UUID
import uuid

from anthropic.types.message import Message

from src.model.conversation import Conversation
from src.model.message import MessageRole
from src.model.responsibility import Responsibility
from src.service.claude_service import ClaudeService
from src.service.conversation_service import ConversationService
from src.service.tool_service import ToolExecutionError, ToolService

_SENTENCE_END = re.compile(r"[.!?][\"')\]]*\s")
_MIN_SENTENCE_CHARS = 30
_AGENT_MAX_ITERATIONS = 10
_AGENT_LOOP_TIMEOUT_SECONDS = 120.0


class AgentLoop:
    """
    Handles the logic for orchestrating the LLM's lifecycle and memory context.
    """

    def __init__(self):
        self.claude_service = ClaudeService()
        self.conversations: dict[UUID, list] = {}
        self.tool_service: ToolService | None = None
        self.conversation_service: ConversationService | None = None

    def new_conversation_id(self) -> UUID:
        return uuid.uuid4()

    def _persist_message(
        self,
        conversation: Conversation,
        role: MessageRole,
        content: str,
    ) -> None:
        """Best-effort write-behind: a persistence hiccup must not kill the turn."""
        try:
            self.conversation_service.record_message(conversation, role, content)
        except Exception as exc:
            print(f"Failed to persist {role} message for conversation {conversation.uuid}: {exc}")

    def conversation_loop_stream(self, prompt: str, conversation_uuid: UUID) -> Iterator[str]:
        """
        Run a single voice conversation turn as a bounded ReAct loop.

        Yields sentence-sized chunks of the final assistant text for TTS.
        Tool calls (including run_sub_agent) are executed inline between Claude
        rounds; only text from the terminal no-tool reply is spoken.

        Turns are persisted to the conversation/message tables. Raises
        ConversationClosedError before yielding anything if the conversation
        has been closed — closed conversations can never be continued.
        """
        if self.tool_service is None:
            self.tool_service = ToolService()
        if self.conversation_service is None:
            self.conversation_service = ConversationService()

        # Gate the turn on the persisted conversation state (may raise
        # ConversationClosedError), creating the row on first use.
        conversation = self.conversation_service.ensure_open_conversation(conversation_uuid)

        # Rehydrate LLM history from persisted messages when this process
        # hasn't seen the conversation yet (e.g. after a restart).
        if conversation_uuid not in self.conversations:
            self.conversations[conversation_uuid] = self.conversation_service.load_history(
                conversation
            )
        history = self.conversations[conversation_uuid]
        history.append({"role": "user", "content": prompt})
        self._persist_message(conversation, MessageRole.USER, prompt)

        tool_context = {"conversation_uuid": str(conversation_uuid)}

        started_at = time.monotonic()

        try:
            tools = self.tool_service.list_tools()
        except Exception:
            tools = []

        tools_by_name: dict[str, Any] = {}
        claude_tools: list[dict[str, Any]] = []
        for tool in tools:
            name = (tool.name or "").strip()
            config = tool.config if isinstance(tool.config, dict) else {}
            input_schema = config.get("input_schema")
            if not name or not isinstance(input_schema, dict):
                continue
            tools_by_name[name] = tool
            claude_tools.append(
                {
                    "name": name,
                    "description": tool.description or "",
                    "input_schema": input_schema,
                }
            )
        tools_arg = claude_tools or None

        for _ in range(_AGENT_MAX_ITERATIONS):
            if time.monotonic() - started_at > _AGENT_LOOP_TIMEOUT_SECONDS:
                fallback = "I hit a time limit while working on that and had to stop."
                history.append({"role": "assistant", "content": fallback})
                self._persist_message(conversation, MessageRole.NOVA, fallback)
                yield fallback
                return

            try:
                response = self.claude_service.stream_response(
                    "",
                    context=history,
                    tools=tools_arg,
                )
            except TimeoutError:
                fallback = "I hit a backend timeout while working on that and had to stop."
                history.append({"role": "assistant", "content": fallback})
                self._persist_message(conversation, MessageRole.NOVA, fallback)
                yield fallback
                return
            except Exception as exc:
                fallback = f"Agent loop failed: {str(exc)}"
                history.append({"role": "assistant", "content": fallback})
                self._persist_message(conversation, MessageRole.NOVA, fallback)
                yield fallback
                return

            tool_uses: list[Any] = []
            assistant_blocks: list[dict[str, Any]] = []
            for block in response.content:
                block_type = getattr(block, "type", None)
                if block_type == "tool_use":
                    tool_uses.append(block)
                    assistant_blocks.append(
                        {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )
                elif hasattr(block, "text") and block.text:
                    assistant_blocks.append({"type": "text", "text": block.text})

            if not tool_uses:
                text = self._extract_text(response)
                # Persist before yielding so a client disconnect mid-stream
                # can't lose the reply.
                self._persist_message(conversation, MessageRole.NOVA, text)
                try:
                    if text:
                        yield from self.iter_sentence_chunks([text])
                finally:
                    history.append({"role": "assistant", "content": text})
                return

            history.append({"role": "assistant", "content": assistant_blocks})

            tool_results: list[dict[str, Any]] = []
            for block in tool_uses:
                tool = tools_by_name.get(block.name)
                if tool is None:
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Unknown tool: {block.name}",
                            "is_error": True,
                        }
                    )
                    self._persist_message(
                        conversation,
                        MessageRole.TOOL,
                        json.dumps({"tool": block.name, "error": "Unknown tool."}),
                    )
                    continue

                arguments = block.input if isinstance(block.input, dict) else {}
                try:
                    print(f"Calling tool: {tool.name} with arguments: {arguments}")
                    result = self.tool_service.call_tool(tool, arguments, context=tool_context)
                    if isinstance(result, str):
                        content = result
                    else:
                        try:
                            content = json.dumps(result)
                        except TypeError:
                            content = str(result)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": content,
                        }
                    )
                    self._persist_message(
                        conversation,
                        MessageRole.TOOL,
                        json.dumps(
                            {"tool": block.name, "input": arguments, "result": content}
                        ),
                    )
                except ToolExecutionError as exc:
                    self._persist_message(
                        conversation,
                        MessageRole.TOOL,
                        json.dumps(
                            {"tool": block.name, "input": arguments, "error": str(exc)}
                        ),
                    )
                    if not exc.recoverable:
                        fallback = "I ran into a tool execution issue and had to stop."
                        history.append({"role": "assistant", "content": fallback})
                        self._persist_message(conversation, MessageRole.NOVA, fallback)
                        yield fallback
                        return
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(exc),
                            "is_error": True,
                        }
                    )

            history.append({"role": "user", "content": tool_results})

        fallback = "I hit a loop limit while working on that and had to stop."
        history.append({"role": "assistant", "content": fallback})
        self._persist_message(conversation, MessageRole.NOVA, fallback)
        yield fallback

    def run_agent(
        self,
        prompt: str,
        responsibility: Responsibility | None = None,
    ) -> str:
        """
        Run a sub-agent as a bounded Claude + ToolService ReAct loop.

        Context is isolated from the voice conversation history. Call from
        FastAPI via asyncio.to_thread so the event loop stays free.
        """
        if self.tool_service is None:
            self.tool_service = ToolService()

        task_prompt = (prompt or "").strip()
        if responsibility is not None:
            task_prompt = task_prompt + "\n" + responsibility.to_prompt()
        if not task_prompt:
            raise ValueError("A prompt or responsibility with name/description is required.")

        started_at = time.monotonic()

        try:
            tools = self.tool_service.list_tools()
        except Exception:
            tools = []

        tools_by_name: dict[str, Any] = {}
        claude_tools: list[dict[str, Any]] = []
        for tool in tools:
            name = (tool.name or "").strip()
            config = tool.config if isinstance(tool.config, dict) else {}
            input_schema = config.get("input_schema")
            if not name or not isinstance(input_schema, dict):
                continue
            tools_by_name[name] = tool
            claude_tools.append(
                {
                    "name": name,
                    "description": tool.description or "",
                    "input_schema": input_schema,
                }
            )
        tools_arg = claude_tools or None

        history: list[dict[str, Any]] = [{"role": "user", "content": task_prompt}]

        for _ in range(_AGENT_MAX_ITERATIONS):
            if time.monotonic() - started_at > _AGENT_LOOP_TIMEOUT_SECONDS:
                return "I hit a time limit while working on that and had to stop."

            try:
                response = self.claude_service.get_response(
                    "",
                    context=history,
                    tools=tools_arg,
                )
            except TimeoutError:
                return "I hit a backend timeout while working on that and had to stop."
            except Exception as exc:
                return f"Agent loop failed: {str(exc)}"

            tool_uses: list[Any] = []
            assistant_blocks: list[dict[str, Any]] = []
            for block in response.content:
                block_type = getattr(block, "type", None)
                if block_type == "tool_use":
                    tool_uses.append(block)
                    assistant_blocks.append(
                        {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )
                elif hasattr(block, "text") and block.text:
                    assistant_blocks.append({"type": "text", "text": block.text})

            if not tool_uses:
                return self._extract_text(response)

            history.append({"role": "assistant", "content": assistant_blocks})

            tool_results: list[dict[str, Any]] = []
            for block in tool_uses:
                tool = tools_by_name.get(block.name)
                if tool is None:
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Unknown tool: {block.name}",
                            "is_error": True,
                        }
                    )
                    continue

                arguments = block.input if isinstance(block.input, dict) else {}
                try:
                    result = self.tool_service.call_tool(tool, arguments)
                    if isinstance(result, str):
                        content = result
                    else:
                        try:
                            content = json.dumps(result)
                        except TypeError:
                            content = str(result)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": content,
                        }
                    )
                except ToolExecutionError as exc:
                    if not exc.recoverable:
                        return "I ran into a tool execution issue and had to stop."
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(exc),
                            "is_error": True,
                        }
                    )

            history.append({"role": "user", "content": tool_results})

        return "I hit a loop limit while working on that and had to stop."

    def preform_responsibility(self, responsibility: Responsibility):
        """
        Agent performs a responsibility.
        """
        pass

    @staticmethod
    def iter_sentence_chunks(
        text_stream: Iterable[str],
        min_chars: int = _MIN_SENTENCE_CHARS,
    ) -> Iterator[str]:
        """
        Group a stream of text deltas into sentence-sized chunks suitable for TTS.

        Chunks are only emitted at sentence boundaries past `min_chars`, so short
        fragments like abbreviations don't produce choppy audio.
        """
        buffer = ""
        for piece in text_stream:
            buffer += piece
            while True:
                match = _SENTENCE_END.search(buffer, min_chars)
                if not match:
                    break
                chunk = buffer[: match.end()].strip()
                buffer = buffer[match.end():]
                if chunk:
                    yield chunk
        remainder = buffer.strip()
        if remainder:
            yield remainder

    @staticmethod
    def _extract_text(message: Message) -> str:
        parts: list[str] = []
        for block in message.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "".join(parts)
