import json
import os
import re
import threading
import time
from collections.abc import Iterable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout
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
from src.harness.spoken_reply import (
    SpokenLineWatcher,
    clamp_spoken,
    speech_summary,
    split_spoken_reply,
)
from src.service.claude_service import ClaudeService
from src.service.conversation_service import ConversationService
from src.service.mcp_server_service import McpServerService
from src.service.memory_chunk_service import MemoryChunkService
from src.service.tool_service import ToolExecutionError, ToolService
from src.service.update_service import UpdateService

_SENTENCE_END = re.compile(r"[.!?][\"')\]]*\s")
_MIN_SENTENCE_CHARS = 30
_AGENT_MAX_ITERATIONS = 50
_AGENT_LOOP_TIMEOUT_SECONDS = 120.0

# Memory retrieval is overlapped with the turn's other setup work, so it needs
# somewhere to run. Small and shared: at most one retrieval is in flight per
# turn, and the sockets serve one user.
_RETRIEVAL_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="nova-retrieval")

# Hard ceiling on how long a turn will wait for memory it did not ask for.
# Retrieval normally finishes inside the setup work it overlaps with; if the
# embedding API or the vector store is having a bad day, the turn goes ahead
# without memory rather than making the user wait for it.
_MEMORY_RETRIEVAL_TIMEOUT_SECONDS = 1.5

# Delimiters for the injected block. Explicit tags rather than bare prose so
# the model can tell recalled memory from the user's own words, and so the
# block stays findable in a transcript.
_MEMORY_OPEN_TAG = "<recalled_memory>"
_MEMORY_CLOSE_TAG = "</recalled_memory>"


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"false", "0", "no", "off"}


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
        # Built on the first turn that needs it, so a deployment without an
        # embedding key or vector store still serves chat.
        self.memory_chunk_service: MemoryChunkService | None = None
        # Whether every turn gets relevant memory pre-loaded into its prompt.
        # The fetch_memory tool is unaffected either way.
        self.memory_retrieval_enabled = _env_flag("NOVA_MEMORY_INJECTION", True)
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

    # ---------- memory retrieval ----------
    #
    # Memory used to be reachable only through the fetch_memory tool, which
    # meant it was only ever consulted when the model thought to ask — and it
    # rarely did, because deciding to search requires already suspecting there
    # is something to find. Retrieving on every turn and putting what clears
    # the relevance gate in front of the model inverts that: recall becomes the
    # default, and the tool becomes what it should have been all along, a way
    # to dig deeper than the automatic pass reached.

    def _start_memory_retrieval(
        self, prompt: str, conversation: Conversation
    ) -> "Future | None":
        """
        Begin the lookup for this turn off-thread, or None when not applicable.

        Returns immediately either way; the work is collected by
        `_collect_memory` once the turn's other setup is done.
        """
        if not self.memory_retrieval_enabled:
            return None
        if not (prompt or "").strip():
            return None
        try:
            return _RETRIEVAL_POOL.submit(
                self._retrieve_memory, prompt, conversation.project_id
            )
        except Exception as exc:
            print(f"Could not start memory retrieval (continuing without it): {exc}")
            return None

    def _retrieve_memory(self, prompt: str, project_id: int | None) -> str | None:
        """The retrieval itself. Runs on the pool; never raises."""
        try:
            if self.memory_chunk_service is None:
                self.memory_chunk_service = MemoryChunkService()
            return self.memory_chunk_service.retrieve_context(
                prompt, project_id=project_id
            )
        except Exception as exc:
            print(f"Memory retrieval failed (continuing without it): {exc}")
            return None

    @staticmethod
    def _collect_memory(memory_future: "Future | None") -> str:
        """Retrieved memory, or "" if there was none or it ran out of time."""
        if memory_future is None:
            return ""
        try:
            return memory_future.result(
                timeout=_MEMORY_RETRIEVAL_TIMEOUT_SECONDS
            ) or ""
        except FutureTimeout:
            print("Memory retrieval exceeded its budget; answering without it.")
            return ""
        except Exception as exc:
            print(f"Memory retrieval failed (continuing without it): {exc}")
            return ""

    @staticmethod
    def _augment(prompt: str, memory_block: str) -> str:
        """The user's turn with any recalled memory in front of it."""
        if not memory_block:
            return prompt
        return (
            f"{_MEMORY_OPEN_TAG}\n{memory_block}\n{_MEMORY_CLOSE_TAG}\n\n{prompt}"
        )

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

    def _failure_events(
        self,
        prompt_source: PromptSourceEnum,
        text: str,
        spoke_early: bool = False,
    ) -> Iterator[dict[str, Any]]:
        """
        Emit one of the loop's own failure messages on both tracks.

        A timeout, a dead tool, the iteration ceiling. These are short by
        construction so there is nothing to summarize, but they do have to be
        SAID: now that only `speech_text` reaches TTS, a voice turn that
        yielded a bare `text` event would leave the user listening to silence,
        waiting for an answer that has already given up.

        `spoke_early` covers the case where the stream got far enough to say
        something before it fell over — the turn does not follow "here you go"
        with "I had to stop" out loud, it just shows the failure on screen.
        """
        if not spoke_early:
            spoken = self._spoken_track(prompt_source, text, text)
            if spoken:
                yield {"type": "speech_text", "text": spoken, "role": "final"}
        yield {"type": "text", "text": text}

    @staticmethod
    def _spoken_track(
        prompt_source: PromptSourceEnum,
        tagged: str | None,
        written: str,
    ) -> str | None:
        """
        Decide what, if anything, this turn should say out loud.

        Returns None for every medium that does not deliver a reply to an ear
        and a screen at once — a phone call and an SMS are already written for
        their one audience, and a chat turn has no audience for audio.

        For the voice UI: the model's own `<speak>` line when it wrote one,
        and otherwise the opening of the written answer, reduced to something
        sayable. Either way the result goes through the length ceiling. The
        prompt asks for brevity, which a model can decline; this is where it
        stops being optional.
        """
        if not prompt_source.wants_spoken_summary():
            return None
        spoken = clamp_spoken(tagged) if tagged else speech_summary(written)
        return spoken or None

    def conversation_loop_events(
        self,
        prompt: str,
        conversation_uuid: UUID,
        prompt_source: PromptSourceEnum = PromptSourceEnum.CHAT_PROMPT,
    ) -> Iterator[dict[str, Any]]:
        """
        Run a single conversation turn as a bounded ReAct loop, as an event stream.

        Yields dicts the transport layer renders however it likes:
          {"type": "text", "text": ...}        sentence chunk of the written
                                               reply, for the screen
          {"type": "speech_text", "text": ...} the ONLY thing meant to be read
                                               aloud, with a "role" of
                                               "status" or "final"
          {"type": "status_text", "text": ...} acknowledgment shown before tool
                                               work starts
          {"type": "tool_call", "tool": ...}   a tool is about to run
          {"type": "artifact", "kind": ...}    renderable output of a tool
                                               (diff, file, terminal)

        Written text and spoken text are two different tracks, not one text
        used twice. `speech_text` carries what goes to TTS — at most a couple
        of sentences, because audio has to be listened through in real time.
        `text` / `text_final` carry the full answer at whatever length the
        question deserves, because a screen can be skimmed. A transport that
        speaks anything other than `speech_text` has reunited them by mistake.

        Text chunks are sentence-sized so the chat panel can stream them in;
        the chat path reassembles them. Tool calls run inline between Claude
        rounds.

        `prompt_source` steers the reply for the medium it will be delivered
        in, and decides whether there is a spoken track at all — see
        `_spoken_track`. It is applied per request rather than appended to
        history, so a spoken turn does not shorten later typed turns in the
        same conversation.

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

        # Kick off memory retrieval now and collect it just before the request
        # goes out. The turn's remaining setup is three network round trips
        # (history, tools, MCP registry) that do not depend on it, so the
        # embed-and-search runs inside time the turn was already spending.
        memory_future = self._start_memory_retrieval(prompt, conversation)

        # Rehydrate LLM history from persisted messages when this process
        # hasn't seen the conversation yet (e.g. after a restart).
        if conversation_uuid not in self.conversations:
            self.conversations[conversation_uuid] = self.conversation_service.load_history(
                conversation
            )
        history = self.conversations[conversation_uuid]

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

        # Everything the retrieval was overlapping with is done; collect it and
        # open the turn.
        #
        # The memory rides on the user message rather than in a system block so
        # the prompt cache survives: system renders before messages, so a block
        # that changes every turn would invalidate the whole conversation
        # history behind it. Appended to history in the augmented form for the
        # same reason — the next turn's cached prefix has to be byte-identical
        # to what this turn sent. Only the user's own words are persisted; the
        # memory is derived, and re-derives on rehydration.
        memory_block = self._collect_memory(memory_future)
        history.append({"role": "user", "content": self._augment(prompt, memory_block)})
        self._persist_message(conversation, MessageRole.USER, prompt)

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
                yield from self._failure_events(prompt_source, fallback)
                return

            # Whether this round already said something out loud. The reply is
            # read as it is written, so the spoken line usually goes out well
            # before the round finishes; the end-of-round paths below check
            # this so a turn never says the same thing twice.
            spoke_early = False
            watcher = (
                SpokenLineWatcher() if prompt_source.wants_spoken_summary() else None
            )

            try:
                turn = self.claude_service.stream_response(
                    "",
                    context=history,
                    tools=tools_arg,
                    system=system_blocks,
                    mcp_servers=mcp_servers,
                )
                # This is the latency win. The `<speak>` block is written
                # first, so its closing tag lands while the markdown answer
                # beneath it is still being generated — and the moment it
                # does, TTS can start. Waiting for the final message here (as
                # this used to) meant every voice turn paid for the length of
                # the WRITTEN answer before a word of the spoken one was said.
                for delta in turn:
                    if watcher is None:
                        continue
                    line = watcher.push(delta)
                    if line is None:
                        continue
                    say = clamp_spoken(line)
                    if say:
                        spoke_early = True
                        yield {"type": "speech_text", "text": say, "role": "final"}
                response = turn.message
            except TimeoutError:
                fallback = "I hit a backend timeout while working on that and had to stop."
                history.append({"role": "assistant", "content": fallback})
                self._persist_message(conversation, MessageRole.NOVA, fallback)
                yield from self._failure_events(prompt_source, fallback, spoke_early)
                return
            except Exception as exc:
                fallback = f"Agent loop failed: {str(exc)}"
                history.append({"role": "assistant", "content": fallback})
                self._persist_message(conversation, MessageRole.NOVA, fallback)
                yield from self._failure_events(prompt_source, fallback, spoke_early)
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

                raw_text = self._extract_text(response)
                display_text, spoken_text = split_spoken_reply(raw_text)
                spoken_text = self._spoken_track(
                    prompt_source, spoken_text, display_text
                )
                # Persist before yielding so a client disconnect mid-stream
                # can't lose the reply. The written answer is the turn of
                # record: the spoken line is a lossy view of it, and a
                # transcript reread later should show what was actually said
                # in full, not the summary that went to the speaker.
                self._persist_message(conversation, MessageRole.NOVA, display_text)
                try:
                    # Speech first. It is the only thing the user is actually
                    # waiting on — the written answer arrives faster than it
                    # can be read either way — so the transport gets it before
                    # the prose and can start synthesizing immediately.
                    if spoken_text and not spoke_early:
                        yield {
                            "type": "speech_text",
                            "text": spoken_text,
                            "role": "final",
                        }
                    if display_text:
                        for chunk in self.iter_sentence_chunks([display_text]):
                            yield {"type": "text", "text": chunk}
                        # Sentence chunks are stripped, which destroys the
                        # newlines markdown lists and code fences need. Emit
                        # the whole text so a renderer can restore fidelity.
                        yield {"type": "text_final", "text": display_text}
                finally:
                    # Keep the full blocks (citations, search results) in
                    # history so follow-up turns stay valid; fall back to raw
                    # text when the model returned nothing to serialize. The
                    # <speak> block is deliberately left in history — seeing
                    # its own format is what keeps the model producing it.
                    history.append(
                        {"role": "assistant", "content": assistant_blocks or raw_text}
                    )
                return

            history.append({"role": "assistant", "content": assistant_blocks})

            if not status_emitted:
                status_display, status_spoken = split_spoken_reply(
                    self._extract_text(response).strip()
                )
                if status_display:
                    status_emitted = True
                    yield {"type": "status_text", "text": status_display}
                    # The ack goes through the same ceiling as the reply, so a
                    # model that turns chatty before a tool call cannot stall
                    # the turn with narration the user has to sit through.
                    spoken_ack = (
                        None
                        if spoke_early
                        else self._spoken_track(
                            prompt_source, status_spoken, status_display
                        )
                    )
                    if spoken_ack:
                        yield {
                            "type": "speech_text",
                            "text": spoken_ack,
                            "role": "status",
                        }

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
                        yield from self._failure_events(
                            prompt_source, fallback, spoke_early
                        )
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
        yield from self._failure_events(prompt_source, fallback)

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
