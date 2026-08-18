import json
import re
import threading
import time
from collections.abc import Iterable, Iterator
from typing import Any
from uuid import UUID
import uuid

from anthropic.types.message import Message

from src.dao.responsibility_dao import ResponsibilityDao
from prompting.prompt_enums import PromptEnums
from prompting.prompt_source_prompt import PromptSourceEnum
from src.model.conversation import Conversation
from src.model.message import MessageRole
from src.model.report_type import ReportType
from src.service.claude_service import ClaudeService
from src.service.conversation_service import ConversationService
from src.service.mcp_server_service import McpServerService
from src.service.tool_service import ToolExecutionError, ToolService
from src.service.update_service import UpdateService

_SENTENCE_END = re.compile(r"[.!?][\"')\]]*\s")
_MIN_SENTENCE_CHARS = 30
_AGENT_MAX_ITERATIONS = 50
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
        self.update_service: UpdateService | None = None
        self.mcp_server_service: McpServerService | None = None
        # Nova's identity — WHO the assistant is and HOW it behaves. Loaded
        # once per process; fails fast at startup if the file is missing.
        self.persona_prompt = PromptEnums.NOVA_PERSONA_PROMPT.load()
        # Live handles to background=True runs, mostly for tests and
        # observability; finished threads are pruned on the next spawn.
        self.background_threads: list[threading.Thread] = []

    def _system_blocks(self, steer: str = "") -> list[dict[str, Any]]:
        """
        Assemble the system prompt for one conversation request.

        The persona is the stable prefix and carries the cache breakpoint —
        tools render before system in the prompt, so this one marker caches
        the tool list and persona together. The per-medium steer (e.g. the
        spoken-reply brevity instruction) changes between chat and voice
        turns, so it must come AFTER the breakpoint or every switch of
        medium would invalidate the cache.
        """
        blocks: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": self.persona_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        if steer and steer.strip():
            blocks.append({"type": "text", "text": steer})
        return blocks

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

    def conversation_loop_stream(
        self,
        prompt: str,
        conversation_uuid: UUID,
        prompt_source: PromptSourceEnum = PromptSourceEnum.SPEECH_PROMPT,
    ) -> Iterator[str]:
        """
        Text-only view of a turn, for the voice path.

        The websocket speaks whatever this yields, so tool calls and artifacts
        are filtered out — they are UI concerns, not things to read aloud.
        The pre-tool acknowledgment (status_text) IS spoken: it exists so the
        user hears something before a long tool run goes quiet.
        Defaults to the spoken steer since this view exists to feed TTS.
        """
        for event in self.conversation_loop_events(
            prompt, conversation_uuid, prompt_source=prompt_source
        ):
            if event.get("type") in ("text", "status_text") and event.get("text"):
                yield event["text"]

    @staticmethod
    def _language_for(path: str) -> str:
        suffix = ("." + path.rsplit(".", 1)[-1].lower()) if "." in path else ""
        return {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "jsx",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".json": "json",
            ".md": "markdown",
            ".sh": "bash",
            ".css": "css",
            ".scss": "scss",
            ".html": "html",
            ".sql": "sql",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".toml": "toml",
        }.get(suffix, "")

    @classmethod
    def _artifact_for_tool(
        cls, tool_name: str, arguments: dict[str, Any], result: Any
    ) -> dict[str, Any] | None:
        """
        Turn a tool result into something the UI can render.

        Diffs, file contents, and terminal output are worth showing as their
        own blocks rather than leaving the model to paraphrase them into prose.
        Tools with nothing visual to show return None.
        """
        payload = result if isinstance(result, dict) else {}

        if tool_name == "edit_project_file":
            diff = payload.get("diff")
            if not diff:
                return None
            return {
                "type": "artifact",
                "kind": "diff",
                "title": payload.get("path") or arguments.get("path", ""),
                "content": diff,
                "language": "diff",
                "tool": tool_name,
            }

        if tool_name in {"write_project_file", "read_project_file"}:
            path = payload.get("path") or arguments.get("path", "")
            content = (
                arguments.get("content")
                if tool_name == "write_project_file"
                else payload.get("content")
            )
            if not content:
                return None
            return {
                "type": "artifact",
                "kind": "file",
                "title": path,
                "content": content,
                "language": cls._language_for(path),
                "tool": tool_name,
            }

        if tool_name == "run_terminal_command":
            streams = [payload.get("stdout") or "", payload.get("stderr") or ""]
            content = "\n".join(part for part in streams if part.strip())
            if not content:
                return None
            return {
                "type": "artifact",
                "kind": "terminal",
                "title": arguments.get("command", ""),
                "content": content,
                "language": "bash",
                "tool": tool_name,
                "exitCode": payload.get("exit_code"),
            }

        return None

    @staticmethod
    def _serialize_blocks(response: Message) -> list[dict[str, Any]]:
        """
        Serialize assistant content blocks for replay in history.

        Server tool blocks (web_search_tool_result) carry encrypted_content
        that the API decrypts on later turns, and cited text blocks carry
        encrypted_index. Both must go back exactly as received or the next
        request fails validation, so dump the blocks wholesale rather than
        rebuilding the fields we happen to care about.
        """
        blocks: list[dict[str, Any]] = []
        for block in response.content:
            if hasattr(block, "model_dump"):
                blocks.append(block.model_dump(exclude_none=True))
            elif isinstance(block, dict):
                blocks.append(block)
            elif getattr(block, "type", None) == "tool_use":
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
            elif getattr(block, "text", None):
                blocks.append({"type": "text", "text": block.text})
        return blocks

    def _load_mcp_servers(self) -> list[dict[str, Any]]:
        """
        Enabled MCP servers for this request, or [] when none are registered.

        Best-effort by design: the registry living in the DB must never take
        a conversation down, so lookup failures degrade to "no MCP tools this
        turn" rather than raising.
        """
        try:
            if self.mcp_server_service is None:
                self.mcp_server_service = McpServerService()
            return self.mcp_server_service.connector_servers()
        except Exception as exc:
            print(f"MCP server lookup failed (continuing without MCP): {exc}")
            return []

    @staticmethod
    def _describe_server_tool_uses(response: Message) -> list[dict[str, Any]]:
        """Audit records for tools Anthropic ran server-side (e.g. web search)."""
        records: list[dict[str, Any]] = []
        for block in response.content:
            if getattr(block, "type", None) != "server_tool_use":
                continue
            records.append(
                {
                    "tool": getattr(block, "name", "unknown"),
                    "input": getattr(block, "input", {}),
                    "server_side": True,
                }
            )
        return records

    @staticmethod
    def _describe_mcp_tool_uses(response: Message) -> list[dict[str, Any]]:
        """
        Audit records for MCP tools Anthropic ran through the connector.

        Like server_tool_use blocks, the calls already happened and their
        results are inline in the same response — these records exist for
        persistence and for the UI, not for execution.
        """
        records: list[dict[str, Any]] = []
        for block in response.content:
            if getattr(block, "type", None) != "mcp_tool_use":
                continue
            server_name = getattr(block, "server_name", "mcp")
            tool_name = getattr(block, "name", "unknown")
            records.append(
                {
                    "tool": f"{server_name}.{tool_name}",
                    "input": getattr(block, "input", {}),
                    "server_side": True,
                    "mcp_server": server_name,
                }
            )
        return records

    def conversation_loop_events(
        self,
        prompt: str,
        conversation_uuid: UUID,
        prompt_source: PromptSourceEnum = PromptSourceEnum.CHAT_PROMPT,
    ) -> Iterator[dict[str, Any]]:
        """
        Run a single conversation turn as a bounded ReAct loop, as an event stream.

        Yields dicts the transport layer renders however it likes:
          {"type": "text", "text": ...}        sentence chunk of the reply
          {"type": "status_text", "text": ...} spoken acknowledgment emitted
                                               before tool work starts
          {"type": "tool_call", "tool": ...}   a tool is about to run
          {"type": "artifact", "kind": ...}    renderable output of a tool
                                               (diff, file, terminal)

        Text chunks are sentence-sized because the voice path speaks them; the
        chat path reassembles them. Tool calls run inline between Claude rounds,
        and only text from the terminal no-tool reply is spoken.

        `prompt_source` steers the reply for the medium it will be delivered
        in — a spoken reply gets read aloud by TTS, so it should be short.
        It is applied per request rather than appended to history, so a spoken
        turn does not shorten later typed turns in the same conversation.

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
        # Deterministic order: tools render at the very front of the prompt
        # cache prefix, and the DB returns them unordered — an order flip
        # would silently invalidate the whole cache.
        claude_tools.sort(key=lambda entry: entry["name"])
        tools_arg = claude_tools or None

        # Persona (cached) + per-medium steer (uncached), built once per turn.
        system_blocks = self._system_blocks(str(prompt_source))

        # Remote MCP servers, resolved once per turn so a registry change
        # mid-turn can't flip the tool list between iterations.
        mcp_servers = self._load_mcp_servers() or None

        # At most one spoken acknowledgment per turn: the text Claude writes
        # before its first tool call is real feedback ("Let me pull that up"),
        # but text on later tool rounds is play-by-play narration — it stays
        # in history for the model and is never surfaced to the user.
        status_emitted = False

        for _ in range(_AGENT_MAX_ITERATIONS):
            if time.monotonic() - started_at > _AGENT_LOOP_TIMEOUT_SECONDS:
                fallback = "I hit a time limit while working on that and had to stop."
                history.append({"role": "assistant", "content": fallback})
                self._persist_message(conversation, MessageRole.NOVA, fallback)
                yield {"type": "text", "text": fallback}
                return

            try:
                response = self.claude_service.stream_response(
                    "",
                    context=history,
                    tools=tools_arg,
                    system=system_blocks,
                    mcp_servers=mcp_servers,
                )
            except TimeoutError:
                fallback = "I hit a backend timeout while working on that and had to stop."
                history.append({"role": "assistant", "content": fallback})
                self._persist_message(conversation, MessageRole.NOVA, fallback)
                yield {"type": "text", "text": fallback}
                return
            except Exception as exc:
                fallback = f"Agent loop failed: {str(exc)}"
                history.append({"role": "assistant", "content": fallback})
                self._persist_message(conversation, MessageRole.NOVA, fallback)
                yield {"type": "text", "text": fallback}
                return

            # Only client-side tool_use blocks need execution here; anything
            # Anthropic ran server-side (web search) already has its results
            # inline in this same response.
            tool_uses = [
                block for block in response.content
                if getattr(block, "type", None) == "tool_use"
            ]
            assistant_blocks = self._serialize_blocks(response)

            for record in self._describe_server_tool_uses(response):
                self._persist_message(
                    conversation, MessageRole.TOOL, json.dumps(record)
                )

            # MCP calls already ran server-side; surface them to the UI the
            # same way client tool calls are surfaced, and keep an audit row.
            for record in self._describe_mcp_tool_uses(response):
                self._persist_message(
                    conversation, MessageRole.TOOL, json.dumps(record)
                )
                yield {
                    "type": "tool_call",
                    "tool": record["tool"],
                    "input": record["input"],
                }

            if not tool_uses:
                # A long server-side search can pause the turn; replay the
                # assistant message unchanged to let it finish.
                if getattr(response, "stop_reason", None) == "pause_turn":
                    history.append({"role": "assistant", "content": assistant_blocks})
                    continue

                text = self._extract_text(response)
                # Persist before yielding so a client disconnect mid-stream
                # can't lose the reply.
                self._persist_message(conversation, MessageRole.NOVA, text)
                try:
                    if text:
                        for chunk in self.iter_sentence_chunks([text]):
                            yield {"type": "text", "text": chunk}
                        # Sentence chunks are stripped for TTS, which destroys
                        # the newlines markdown lists and code fences need.
                        # Emit the raw text so a renderer can restore fidelity.
                        yield {"type": "text_final", "text": text}
                finally:
                    # Keep the full blocks (citations, search results) in
                    # history so follow-up turns stay valid; fall back to raw
                    # text when the model returned nothing to serialize.
                    history.append(
                        {"role": "assistant", "content": assistant_blocks or text}
                    )
                return

            history.append({"role": "assistant", "content": assistant_blocks})

            if not status_emitted:
                status = self._extract_text(response).strip()
                if status:
                    status_emitted = True
                    yield {"type": "status_text", "text": status}

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
                yield {"type": "tool_call", "tool": block.name, "input": arguments}
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
                    artifact = self._artifact_for_tool(block.name, arguments, result)
                    if artifact is not None:
                        yield artifact
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
                        yield {"type": "text", "text": fallback}
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
        yield {"type": "text", "text": fallback}

    def run_agent(
        self,
        prompt: str | None = None,
        responsibility_id: int | None = None,
        background: bool = False,
        conversation_uuid: str | None = None,
        report_type: str | None = None,
    ) -> str:
        """
        Run a sub-agent as a bounded Claude + ToolService ReAct loop.

        Context is isolated from any conversation history, so this is how
        background work runs: responsibilities are triggered here by id, and
        the responsibility's own description leads the prompt. Call from
        FastAPI via asyncio.to_thread so the event loop stays free.

        With background=False the caller awaits the loop and gets the agent's
        final reply back. With background=True the loop runs on a daemon
        thread and this returns an acknowledgment immediately; when the agent
        finishes, its summary is recorded as an Update for the user to review
        later. conversation_uuid (injected by the tool harness, never the
        model) links that update to the conversation — and through it the
        project — the work was kicked off from.

        `report_type` says how the user wants to hear about the result: it is
        stamped onto the update this run produces, and the dispatcher delivers
        from there. The sub-agent never delivers anything itself — it is told
        which medium its summary is headed for so it can write for that
        medium, and nothing more.
        """
        if self.tool_service is None:
            self.tool_service = ToolService()

        validated_report_type = self._validate_report_type(report_type)

        parts: list[str] = []
        if responsibility_id is not None:
            responsibility = ResponsibilityDao().get(responsibility_id)
            if responsibility is None:
                raise ValueError(f"Responsibility with id {responsibility_id} not found")
            parts.append(responsibility.to_prompt().strip())
        if prompt and prompt.strip():
            parts.append(prompt.strip())
        if validated_report_type is not None:
            parts.append(self._report_medium_brief(validated_report_type))

        task_prompt = "\n".join(parts).strip()
        if not task_prompt:
            raise ValueError("A prompt or responsibility_id is required.")

        if background:
            thread = threading.Thread(
                target=self._run_background_agent,
                args=(task_prompt, conversation_uuid, validated_report_type),
                name="nova-background-agent",
                daemon=True,
            )
            self.background_threads = [
                t for t in self.background_threads if t.is_alive()
            ]
            self.background_threads.append(thread)
            thread.start()
            if validated_report_type == ReportType.CALL:
                return (
                    "Background agent started. When it finishes, Nova will "
                    "phone the user to report the result. Tell the user to "
                    "expect a call rather than to watch for an update."
                )
            if validated_report_type == ReportType.EMAIL:
                return (
                    "Background agent started. When it finishes, its summary "
                    "will be emailed to the user and also posted as an update."
                )
            return (
                "Background agent started. When it finishes, its summary will "
                "be posted as an update — there is nothing to wait for now; "
                "the user can ask about their updates later."
            )

        return self._run_agent_loop(task_prompt)

    @staticmethod
    def _validate_report_type(report_type: str | None) -> "ReportType | None":
        if report_type is None:
            return None
        candidate = str(report_type).strip().lower()
        if not candidate:
            return None
        try:
            return ReportType(candidate)
        except ValueError:
            raise ToolExecutionError(
                f"Unknown report_type '{report_type}'. Valid types are "
                f"{[str(t) for t in ReportType]}.",
                recoverable=True,
            )

    @staticmethod
    def _report_medium_brief(report_type: "ReportType") -> str:
        """
        Tell the agent what its summary is going to become.

        Deliberately not permission to deliver: delivery happens system-side
        after the run, so this only shapes how the final summary is written.
        """
        if report_type == ReportType.CALL:
            return (
                "When you finish, Nova will phone the user and report your "
                "summary out loud, so write that summary to be spoken. Lead "
                "with the outcome in one sentence, keep the whole thing to a "
                "few sentences, and leave out code, file paths, URLs, and "
                "anything else that cannot be read aloud. Do not try to place "
                "the call yourself — that is handled for you."
            )
        if report_type == ReportType.EMAIL:
            return (
                "When you finish, your summary will be emailed to the user "
                "verbatim, so write it as the body of that email. Do not send "
                "any email yourself — that is handled for you."
            )
        return (
            f"When you finish, your summary is intended to reach the user by "
            f"{report_type}. Write it accordingly, and do not try to send it "
            "yourself."
        )

    def _run_background_agent(
        self,
        task_prompt: str,
        conversation_uuid: str | None,
        report_type: "ReportType | None" = None,
    ) -> None:
        """
        Body of a background=True run: do the work, then record an Update.

        Runs on a daemon thread with nobody awaiting the result, so every
        outcome — success, agent failure, even a crash in the loop — must end
        in an update row; a background task that dies silently would simply
        never be heard from again.
        """
        if self.conversation_service is None:
            self.conversation_service = ConversationService()
        if self.update_service is None:
            self.update_service = UpdateService()

        # Resolve where the work came from, both to tag the update and to let
        # the sub-agent ground itself in the project it is serving.
        linked_conversation_uuid: str | None = None
        project_id: int | None = None
        context_lines: list[str] = []
        try:
            if conversation_uuid:
                conversation = self.conversation_service.get_conversation(
                    UUID(str(conversation_uuid))
                )
                if conversation is not None:
                    linked_conversation_uuid = str(conversation.uuid)
                    project_id = conversation.project_id
                    context_lines.append(
                        "This task was kicked off from a conversation with the user."
                    )
                    if project_id is not None:
                        project = self.conversation_service.project_dao.get(project_id)
                        if project is not None:
                            context_lines.append(
                                f"It belongs to the project '{project.name}' "
                                f"(id {project.id}): "
                                f"{project.description or 'no description'}"
                            )
        except Exception as exc:
            # Context is a nicety; the task itself must still run.
            print(f"Background agent could not resolve conversation context: {exc}")

        full_prompt = "\n\n".join(context_lines + [task_prompt])

        try:
            summary = self._run_agent_loop(
                full_prompt, system=PromptEnums.BACKGROUND_AGENT_PROMPT.load()
            )
        except Exception as exc:
            summary = f"A background task failed before completing: {exc}"

        try:
            self.update_service.create_update(
                update_message=summary.strip()
                or "A background task finished but produced no summary.",
                project_id=project_id,
                conversation_uuid=linked_conversation_uuid,
                report_type=str(report_type) if report_type else None,
            )
        except Exception as exc:
            print(f"Background agent failed to record its update: {exc}")

    def _run_agent_loop(self, task_prompt: str, system: str | None = None) -> str:
        """The bounded ReAct loop shared by foreground and background runs."""
        if self.tool_service is None:
            self.tool_service = ToolService()

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
        # Same determinism rule as the conversation loop: stable tool order
        # keeps the prompt cache prefix valid across requests.
        claude_tools.sort(key=lambda entry: entry["name"])
        tools_arg = claude_tools or None

        # Background agents get the same MCP tool surface as conversations.
        mcp_servers = self._load_mcp_servers() or None

        history: list[dict[str, Any]] = [{"role": "user", "content": task_prompt}]

        for _ in range(_AGENT_MAX_ITERATIONS):
            if time.monotonic() - started_at > _AGENT_LOOP_TIMEOUT_SECONDS:
                return "I hit a time limit while working on that and had to stop."

            try:
                response = self.claude_service.get_response(
                    "",
                    context=history,
                    tools=tools_arg,
                    system=system,
                    mcp_servers=mcp_servers,
                )
            except TimeoutError:
                return "I hit a backend timeout while working on that and had to stop."
            except Exception as exc:
                return f"Agent loop failed: {str(exc)}"

            tool_uses = [
                block for block in response.content
                if getattr(block, "type", None) == "tool_use"
            ]
            assistant_blocks = self._serialize_blocks(response)

            if not tool_uses:
                # A long server-side search can pause the turn; replay the
                # assistant message unchanged to let it finish.
                if getattr(response, "stop_reason", None) == "pause_turn":
                    history.append({"role": "assistant", "content": assistant_blocks})
                    continue
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
