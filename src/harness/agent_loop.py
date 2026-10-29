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
from prompting.host_environment_prompt import host_environment_prompt
from prompting.prompt_enums import PromptEnums
from prompting.prompt_source_prompt import (
    SIDEKICK_EXPECTS_REPLY,
    SIDEKICK_PASS,
    PromptSourceEnum,
)
from src.model.conversation import Conversation
from src.model.message import MessageRole
from src.model.report_type import ReportType
from src.harness.spoken_reply import (
    NO_SCREEN_LINE,
    SCREEN_ONLY_LINE,
    LiveReply,
    clamp_spoken,
    is_repeat,
    speech_summary,
    strip_speak_tags,
)
from src.service.claude_service import TOOL_USE_STARTED, ClaudeService
from src.service.conversation_service import (
    ConversationClosedError,
    ConversationService,
)
from src.service.mcp_server_service import McpServerService
from src.service.memory_chunk_service import MemoryChunkService
from src.service.persona_service import PersonaService
from src.service.tool_service import ToolExecutionError, ToolService
from src.service.update_service import UpdateService
from src.harness.turn_timer import TurnTimer, mark as _mark_timing

_SENTENCE_END = re.compile(r"[.!?][\"')\]]*\s")
_MIN_SENTENCE_CHARS = 30
_AGENT_MAX_ITERATIONS = 50

# Stand-in for a tool_result the agent loop never got to record — the tool
# call was interrupted by a timeout, a retry, or a crash partway through.
# Anthropic rejects every later request on a conversation with a dangling
# tool_use id, so every one must get a result before the next request goes
# out; see `AgentLoop.repair_tool_pairing`.
_INTERRUPTED_TOOL_RESULT = "Tool call was interrupted and returned no result."

# Stand-in content for an assistant message that `repair_tool_pairing` emptied
# out entirely — every block it carried was an orphaned server-executed tool
# call or result (mcp_tool_use/mcp_tool_result, server_tool_use/*_tool_result)
# with no matching counterpart. An empty content list is invalid, so this
# keeps the message (and the role alternation around it) valid.
_ORPHANED_TOOL_CALL_TEXT = "[a tool call was interrupted and removed from history]"

# How many progress lines one turn may say out loud before it stops narrating
# and just works. A multi-step turn should not leave the user in silence, but
# it should not talk the whole way through either — past about three, the
# updates stop being reassurance and become the thing you are waiting out.
_MAX_SPOKEN_PROGRESS_LINES = 3
_AGENT_LOOP_TIMEOUT_SECONDS = 120.0

# The turn's setup work — memory retrieval, the tool list, the MCP registry —
# and its write-behind persistence all run here, so they overlap instead of
# queueing behind one another on the way to the first word. Small and shared:
# a turn submits a handful of jobs, and the sockets serve one user.
_SETUP_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix="nova-setup")

# How long the end of a turn waits for a write-behind insert that has not
# landed yet. They normally finish during the model request; this only bounds
# the wait when the database is having a bad day.
_WRITE_BEHIND_TIMEOUT_SECONDS = 5.0

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

# What a photo becomes once it is no longer sent: in the transcript, and in
# history once a newer photo has replaced it.
_PHOTO_MARKER = "[photo]"
_IN_VIEW_OPEN = "<in_view>"
_IN_VIEW_CLOSE = "</in_view>"

# A run launched from a responsibility has nobody present to catch it
# scheduling more unattended work on itself — that's how ids ~41 and ~44
# became duplicate responsibilities spawned from a responsibility's own run.
# These tool names are withheld from such runs; the responsibility itself is
# still managed by whoever is in the foreground conversation.
_RESPONSIBILITY_RESTRICTED_TOOLS = frozenset(
    {
        "create_responsibility",
        "create_scheduled_task",
        "update_responsibility",
        "delete_responsibility",
    }
)

_RESPONSIBILITY_RUN_RESTRICTION = (
    "Do the work described above. Do not create or modify responsibilities "
    "or scheduled tasks — you will not have those tools available."
)


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"false", "0", "no", "off"}


def is_sidekick_pass(text: str) -> bool:
    """Whether a sidekick reply is the pass sentinel and nothing else."""
    return re.sub(r"[\s.!]", "", text or "").lower() == SIDEKICK_PASS


def strip_expects_reply(text: str) -> tuple[str, bool]:
    """
    Pull the `expects_reply` control token off the end of a sidekick reply.

    The model appends it, with nothing after it, to a remark that ends in a
    question or a request for confirmation. `SpokenProse` holds back any text
    with no closing sentence punctuation until the round ends, and the token
    has none, so it only ever surfaces as a trailing fragment — here, or as
    its own event out of `LiveReply.finish()` (see `_strip_expects_reply_events`).
    """
    stripped = (text or "").rstrip()
    if stripped.lower().endswith(SIDEKICK_EXPECTS_REPLY):
        return stripped[: -len(SIDEKICK_EXPECTS_REPLY)].rstrip(), True
    return text, False


def _strip_expects_reply_events(
    events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    """Apply `strip_expects_reply` to a round's held-back final events."""
    found = False
    cleaned: list[dict[str, Any]] = []
    for event in events:
        text = event.get("text")
        if text is None:
            cleaned.append(event)
            continue
        new_text, hit = strip_expects_reply(text)
        found = found or hit
        if new_text:
            cleaned.append({**event, "text": new_text})
    return cleaned, found


class _PassHold:
    """
    Holds a sidekick round's live events until they cannot be a pass.

    A sidekick turn that decides it has nothing to say replies with the
    sentinel. Prose streams live, so without this the sentinel itself would
    be spoken a word into the reply. Events are held only while everything
    written so far could still be the sentinel — in practice the first
    character or two of a real reply — and then released in order. For any
    other medium it is a pass-through.
    """

    def __init__(self, active: bool) -> None:
        self._held: list[dict[str, Any]] | None = [] if active else None
        self._text = ""

    @staticmethod
    def _could_be_pass(text: str) -> bool:
        return SIDEKICK_PASS.startswith(text.strip().lower())

    def feed(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self._held is None:
            return events
        for event in events:
            self._held.append(event)
            if event["type"] == "text":
                self._text += event["text"]
                undecided = self._could_be_pass(self._text)
            else:
                undecided = self._could_be_pass(event.get("text", ""))
            if not undecided:
                return self.flush([])
        return []

    def flush(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Release whatever is held, then `events`, and stop holding."""
        held = self._held or []
        self._held = None
        return [*held, *events]


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
        # Nova's identity — WHO the assistant is and HOW it behaves. Built
        # lazily (see the persona_prompt property below): it now comes from
        # the database by default, live-editable via the update_persona tool,
        # and falls back to the shipped markdown file when the database has
        # nothing usable.
        self.persona_service: PersonaService | None = None
        # WHERE Nova is running — the tower or the Mac itself. It decides what
        # run_terminal_command and run_mac_command actually mean, so the model
        # has to be told rather than left to assume the tower. Fixed for the
        # life of the process, like the persona.
        self.host_prompt = host_environment_prompt()
        # Live handles to background=True runs, mostly for tests and
        # observability; finished threads are pruned on the next spawn.
        self.background_threads: list[threading.Thread] = []

    @property
    def persona_prompt(self) -> str:
        """
        Nova's identity text, read fresh (through PersonaService's own short
        TTL cache) on every call rather than cached on `self` — unlike the
        host block, the persona can now change mid-process via the
        update_persona tool, and the next turn should see it without a
        restart.
        """
        if self.persona_service is None:
            self.persona_service = PersonaService()
        return self.persona_service.get_active_content()

    def _system_blocks(self, steer: str = "") -> list[dict[str, Any]]:
        """
        Assemble the system prompt for one conversation request.

        The persona and the host description are the stable prefix, and the
        LAST of them carries the cache breakpoint — tools render before system
        in the prompt, so this one marker caches the tool list, the persona and
        the host together. The host block is a process-lifetime constant; the
        persona is not any more (see the property above) but changes rarely
        enough that caching it under the same breakpoint is still the right
        trade — an update invalidates the prompt cache for the next turn,
        which is the correct behavior, not a bug. The per-medium steer (e.g.
        the spoken-reply brevity instruction) changes between chat and voice
        turns, so it must come AFTER the breakpoint or every switch of medium
        would invalidate the cache.
        """
        blocks: list[dict[str, Any]] = [
            {"type": "text", "text": self.persona_prompt},
            {
                "type": "text",
                "text": self.host_prompt,
                "cache_control": {"type": "ephemeral"},
            },
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
            return _SETUP_POOL.submit(
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
    def _collect_memory(
        memory_future: "Future | None", timer: "TurnTimer | None" = None
    ) -> str:
        """Retrieved memory, or "" if there was none or it ran out of time."""
        if memory_future is None:
            return ""
        started_at = time.monotonic()
        try:
            result = memory_future.result(timeout=_MEMORY_RETRIEVAL_TIMEOUT_SECONDS) or ""
            _mark_timing(
                timer,
                "memory_collected",
                blocked_ms=round((time.monotonic() - started_at) * 1000),
                result="block" if result else "empty",
            )
            return result
        except FutureTimeout:
            print("Memory retrieval exceeded its budget; answering without it.")
            _mark_timing(
                timer,
                "memory_collected",
                blocked_ms=round((time.monotonic() - started_at) * 1000),
                result="timeout",
            )
            return ""
        except Exception as exc:
            print(f"Memory retrieval failed (continuing without it): {exc}")
            _mark_timing(
                timer,
                "memory_collected",
                blocked_ms=round((time.monotonic() - started_at) * 1000),
                result="error",
            )
            return ""

    @staticmethod
    def _augment(prompt: str, memory_block: str) -> str:
        """The user's turn with any recalled memory in front of it."""
        if not memory_block:
            return prompt
        return (
            f"{_MEMORY_OPEN_TAG}\n{memory_block}\n{_MEMORY_CLOSE_TAG}\n\n{prompt}"
        )

    @staticmethod
    def _tool_result_content(result: Any) -> str | list[dict[str, Any]]:
        """
        A tool's return value as tool_result content.

        Text by default. A list of content blocks (the `look` tool's photo and
        `<in_view>` note) goes through as-is, because a photo flattened to
        JSON is just a very long string to the model.
        """
        if isinstance(result, str):
            return result
        if (
            isinstance(result, list)
            and result
            and all(
                isinstance(block, dict) and block.get("type") in ("text", "image")
                for block in result
            )
        ):
            return result
        try:
            return json.dumps(result)
        except TypeError:
            return str(result)

    @staticmethod
    def _interrupted_tool_result(tool_use_id: str) -> dict[str, Any]:
        """A placeholder tool_result for a tool_use id that never got one."""
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": _INTERRUPTED_TOOL_RESULT,
            "is_error": True,
        }

    @staticmethod
    def _tool_use_ids(message: dict[str, Any] | None) -> list[str]:
        """tool_use ids carried by an assistant message's content blocks, in order."""
        if not message:
            return []
        content = message.get("content")
        if not isinstance(content, list):
            return []
        return [
            block["id"]
            for block in content
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("id")
        ]

    @classmethod
    def repair_tool_pairing(cls, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Make `history` valid for the next request to the model, in place.

        A tool call interrupted mid-flight — a timeout, a retry, a crash
        before the result was recorded — can leave an assistant tool_use
        block in history with no matching tool_result in the user message
        right after it. The Anthropic API rejects every later request on
        that conversation with a 400 once that happens ("tool_use ids were
        found without tool_result blocks immediately after"), and the
        in-process history for a conversation (`self.conversations`) is
        never rehydrated from the DB again once it exists, so the break
        would otherwise persist for the life of the process. This runs
        before every request:

        - any tool_use id with no tool_result in the following message gets
          a placeholder tool_result inserted (or a whole placeholder user
          message, if none follows at all);
        - any tool_result block that doesn't answer a tool_use id from the
          message immediately before it is dropped as an orphan.

        Server-executed tool calls — `mcp_tool_use`/`mcp_tool_result` from an
        MCP connector, `server_tool_use`/`*_tool_result` from a built-in tool
        like web search — are different: both the call and its result are
        blocks inside the *same* assistant message rather than spanning two
        messages. An interrupted turn can still leave one side missing (a
        Teams check through an MCP server has persisted its `mcp_tool_use`
        audit row and then the turn ended with no result recorded), and
        Anthropic rejects that the same way. For every assistant message:

        - any `*_tool_use` block (other than the plain client `tool_use`,
          handled above) with no `*_tool_result` block answering its id in
          the same message is dropped as an orphan;
        - any `*_tool_result` block (other than the plain client
          `tool_result`) that doesn't answer a `*_tool_use` id in the same
          message is dropped as an orphan;
        - if that leaves the message with no content at all, it is replaced
          with a short placeholder so the role alternation around it stays
          valid.

        This is a backstop. The agent loop itself should never create the
        broken state in the first place (see the tool-call loop in
        `_conversation_turn`, which always records a result — real or
        placeholder — for every tool_use before moving on); this exists for
        whatever gets past that, including history assembled or edited by
        other code paths.

        Returns `history` for convenience; the list is also mutated in place
        so a caller holding the same reference sees the fix.
        """
        i = 0
        while i < len(history):
            message = history[i]
            role = message.get("role")

            if role == "assistant" and isinstance(message.get("content"), list):
                content = message["content"]
                use_ids = {
                    block["id"]
                    for block in content
                    if isinstance(block, dict)
                    and isinstance(block.get("type"), str)
                    and block["type"] != "tool_use"
                    and block["type"].endswith("_tool_use")
                    and block.get("id")
                }
                result_ids = {
                    block["tool_use_id"]
                    for block in content
                    if isinstance(block, dict)
                    and isinstance(block.get("type"), str)
                    and block["type"] != "tool_result"
                    and block["type"].endswith("_tool_result")
                    and block.get("tool_use_id")
                }
                if use_ids or result_ids:
                    filtered = [
                        block
                        for block in content
                        if not (
                            isinstance(block, dict)
                            and isinstance(block.get("type"), str)
                            and (
                                (
                                    block["type"] != "tool_use"
                                    and block["type"].endswith("_tool_use")
                                    and block.get("id") not in result_ids
                                )
                                or (
                                    block["type"] != "tool_result"
                                    and block["type"].endswith("_tool_result")
                                    and block.get("tool_use_id") not in use_ids
                                )
                            )
                        )
                    ]
                    if not filtered:
                        filtered = [{"type": "text", "text": _ORPHANED_TOOL_CALL_TEXT}]
                    if filtered != content:
                        message = {**message, "content": filtered}
                        history[i] = message

            if role == "user" and isinstance(message.get("content"), list):
                prev = history[i - 1] if i > 0 else None
                prev_ids = set(cls._tool_use_ids(prev)) if prev and prev.get("role") == "assistant" else set()
                content = message["content"]
                has_tool_result = any(
                    isinstance(block, dict) and block.get("type") == "tool_result"
                    for block in content
                )
                if has_tool_result or prev_ids:
                    # Keep every non-tool_result block, and only tool_result
                    # blocks that answer this round's tool_use ids — anything
                    # else is an orphan.
                    kept = [
                        block
                        for block in content
                        if not (
                            isinstance(block, dict)
                            and block.get("type") == "tool_result"
                            and block.get("tool_use_id") not in prev_ids
                        )
                    ]
                    present_ids = {
                        block.get("tool_use_id")
                        for block in kept
                        if isinstance(block, dict) and block.get("type") == "tool_result"
                    }
                    missing = [tid for tid in prev_ids if tid not in present_ids]
                    if missing:
                        kept = kept + [cls._interrupted_tool_result(tid) for tid in missing]
                    if kept != content:
                        history[i] = {**message, "content": kept}
                i += 1
                continue

            if role == "assistant":
                pending_ids = cls._tool_use_ids(message)
                if pending_ids:
                    next_message = history[i + 1] if i + 1 < len(history) else None
                    next_is_user_list = (
                        next_message is not None
                        and next_message.get("role") == "user"
                        and isinstance(next_message.get("content"), list)
                    )
                    if not next_is_user_list:
                        # Nothing follows this tool_use at all (end of
                        # history, or the next message isn't a tool_result
                        # carrier) — insert one so every pending id gets
                        # answered before the next request. The following
                        # loop iteration fills it in via the branch above.
                        history.insert(
                            i + 1,
                            {
                                "role": "user",
                                "content": [
                                    cls._interrupted_tool_result(tid) for tid in pending_ids
                                ],
                            },
                        )
            i += 1

        return history

    @staticmethod
    def _without_images(content: Any) -> Any:
        """Content with every image block replaced by a `[photo]` marker."""
        if not isinstance(content, list):
            return content
        replaced = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "image":
                replaced.append({"type": "text", "text": _PHOTO_MARKER})
            elif isinstance(block, dict) and block.get("type") == "tool_result":
                replaced.append(
                    {**block, "content": AgentLoop._without_images(block.get("content"))}
                )
            else:
                replaced.append(block)
        return replaced

    @staticmethod
    def _photo_note(prompt: str, images: list[dict[str, Any]] | None) -> str:
        """
        What the transcript keeps of an image turn: the words, `[photo]`, and
        the face matcher's note — never the photo itself.
        """
        if not images:
            return prompt
        count = sum(1 for block in images if block.get("type") == "image")
        marker = _PHOTO_MARKER if count <= 1 else f"[{count} photos]"
        notes = [
            block.get("text", "")
            .replace(_IN_VIEW_OPEN, "")
            .replace(_IN_VIEW_CLOSE, "")
            .strip()
            for block in images
            if block.get("type") == "text"
        ]
        note = " ".join(part for part in notes if part)
        return f"{prompt}\n\n{marker} {note}".rstrip()

    @staticmethod
    def _has_image(message: dict[str, Any]) -> bool:
        content = message.get("content")
        if not isinstance(content, list):
            return False
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "image":
                return True
            if block.get("type") == "tool_result" and isinstance(block.get("content"), list):
                if any(
                    isinstance(inner, dict) and inner.get("type") == "image"
                    for inner in block["content"]
                ):
                    return True
        return False

    @classmethod
    def _strip_old_images(cls, history: list[dict[str, Any]]) -> None:
        """
        Drop photos from every user turn but the most recent one with a photo.

        History is resent on every request, so a photo left in it is paid for
        on every turn after it. The latest one stays so a follow-up ("what
        colour is it?") still has it to look at. A photo can arrive as the
        user's message or as a `look` tool result; the most recent image turn
        runs from the user message that opened it to the end of history, so
        a turn that looked twice keeps both. Dropped photos become `[photo]`
        markers: the request stays valid and the model knows something was
        there.
        """
        last_turn_start: int | None = None
        for index in range(len(history) - 1, -1, -1):
            message = history[index]
            if message.get("role") != "user" or not cls._has_image(message):
                continue
            # Walk back to the user message that opened this turn: the one
            # whose content is the user's words rather than tool results.
            start = index
            while start > 0 and cls._continues_turn(history[start]):
                start -= 1
            last_turn_start = start
            break
        if last_turn_start is None:
            return
        for index in range(last_turn_start):
            message = history[index]
            if message.get("role") == "user" and cls._has_image(message):
                history[index] = {**message, "content": cls._without_images(message["content"])}

    @staticmethod
    def _continues_turn(message: dict[str, Any]) -> bool:
        content = message.get("content")
        return (
            message.get("role") == "user"
            and isinstance(content, list)
            and bool(content)
            and all(
                isinstance(block, dict) and block.get("type") == "tool_result"
                for block in content
            )
        ) or message.get("role") == "assistant"

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

    def _persist_message_later(
        self,
        conversation: Conversation,
        role: MessageRole,
        content: str,
    ) -> Future:
        """
        `_persist_message`, off the turn's critical path.

        The insert runs on the pool while the model request goes out. The
        caller keeps the future and collects it before the turn is handed
        back (`_await_writes`), so the transcript is whole by then and message
        order in the table is preserved.
        """
        return _SETUP_POOL.submit(self._persist_message, conversation, role, content)

    @staticmethod
    def _await_writes(pending: list[Future]) -> None:
        for future in pending:
            try:
                future.result(timeout=_WRITE_BEHIND_TIMEOUT_SECONDS)
            except FutureTimeout:
                print("A write-behind message insert is still running; not waiting on it.")
            except Exception as exc:
                # _persist_message swallows its own errors; this is the pool.
                print(f"Write-behind message insert failed: {exc}")

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

    # Every tool whose result is terminal output, on either host. Background
    # processes are here too: a dev server's log is exactly as worth showing as
    # a test run's, and it is the only view Nate gets of something that is
    # still running.
    _SHELL_TOOLS = (
        "run_terminal_command",
        "run_mac_command",
        "start_background_command",
        "check_background_command",
        "stop_background_command",
        "start_mac_background_command",
        "check_mac_background_command",
        "stop_mac_background_command",
    )

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

        if tool_name in cls._SHELL_TOOLS:
            # Two output shapes reach here. A command that finishes returns the
            # two streams separately; a long-lived one returns a single
            # interleaved `output`, because for a server the ordering between
            # stdout and stderr is the thing you need and there is no final
            # exit code to wait for.
            streams = [
                payload.get("stdout") or "",
                payload.get("stderr") or "",
                payload.get("output") or "",
            ]
            content = "\n".join(part for part in streams if part.strip())
            if not content:
                return None
            return {
                "type": "artifact",
                "kind": "terminal",
                # check/stop are given a process_id rather than a command, so
                # the command comes back from the payload for those.
                "title": arguments.get("command") or payload.get("command") or "",
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
            spoken = self._spoken_track(prompt_source, text)
            if spoken:
                yield {"type": "speech_text", "text": spoken, "role": "final"}
        yield {"type": "text", "text": text}

    @staticmethod
    def _spoken_track(
        prompt_source: PromptSourceEnum,
        written: str,
        *,
        required: bool = False,
    ) -> str | None:
        """
        Decide what, if anything, a reply that arrived complete should say.

        Returns None for every medium that does not deliver a reply to an ear
        and a screen at once — a phone call and an SMS are already written for
        their one audience, and a chat turn has no audience for audio.

        For the voice UI: the written prose, said as written, with the
        markdown (code, tables, lists) left on the screen. Nothing is
        shortened or rewritten; the live path says exactly the same words as
        the stream goes by.

        `required` marks the place where saying nothing is not an option. An
        answer made entirely of table rows or a code block reduces to no
        sayable prose at all, and for a progress line that is fine — skip it.
        For the ANSWER it is not: the user asked a question out loud and is
        waiting for a reply, and silence tells them the turn failed. So the
        answer falls back to a line that at least points at the screen.
        """
        if not prompt_source.wants_spoken_summary():
            return None
        spoken = speech_summary(written)
        if spoken:
            return spoken
        if required and written.strip():
            return SCREEN_ONLY_LINE if prompt_source.has_screen() else NO_SCREEN_LINE
        return None

    def conversation_loop_events(
        self,
        prompt: str,
        conversation_uuid: UUID,
        prompt_source: PromptSourceEnum = PromptSourceEnum.CHAT_PROMPT,
        conversation: Conversation | None = None,
        images: list[dict[str, Any]] | None = None,
        persist_prompt_as: str | None = None,
        timer: "TurnTimer | None" = None,
    ) -> Iterator[dict[str, Any]]:
        """
        Run a single conversation turn as a bounded ReAct loop, as an event stream.

        Yields dicts the transport layer renders however it likes:
          {"type": "text", "text": ...}        a piece of the written reply,
                                               whitespace-exact, for the
                                               screen — streamed as the model
                                               writes it
          {"type": "speech_text", "text": ...} what is read aloud: the prose of
                                               the written reply, markdown
                                               left out, with a "role" of
                                               "status" or "final"
          {"type": "status_text", "text": ...} acknowledgment shown before tool
                                               work starts
          {"type": "tool_call", "tool": ...}   a tool is about to run
          {"type": "artifact", "kind": ...}    renderable output of a tool
                                               (diff, file, terminal)
          {"type": "silent"}                   a sidekick turn passed (replied
                                               with the pass sentinel): nothing
                                               was said and nothing persisted

        What is spoken is what is written, minus the markdown. `speech_text`
        carries the prose of the reply a sentence or two at a time, as it is
        written, so a transport can start talking before the answer is done;
        code blocks, tables and lists appear only in `text` / `text_final`.
        A transport speaks `speech_text` and nothing else, because that is
        where the markdown has already been taken out.

        Prose is streamed as the model writes it, held back only for as long
        as it takes to tell an answer from a pre-tool acknowledgment (see
        `LiveReply`); `text_final` then carries the whole reply, tags
        stripped, so a renderer can swap in exactly what was written. Tool
        calls run inline between Claude rounds.

        `prompt_source` steers the reply for the medium it will be delivered
        in, and decides whether there is a spoken track at all — see
        `_spoken_track`. It is applied per request rather than appended to
        history, so a spoken turn does not shorten later typed turns in the
        same conversation.

        `conversation` is the row for `conversation_uuid` when the caller has
        already fetched it (transports check for a closed conversation before
        opening their stream); it saves the loop fetching it again.

        `images` is Claude content to put in front of the user's words: photo
        blocks from the glasses and the `<in_view>` text naming who the face
        matcher saw (see VisionService.content_blocks). Only the words and a
        `[photo]` note are persisted, and once a later turn brings a new photo
        the old one is dropped from history (`_strip_old_images`), so a photo
        is not paid for on every turn after it.

        `persist_prompt_as` is what to keep of `prompt` once the model has read
        it: the row written to the message table and, after the turn, the
        user message left in history. Sidekick uses it so the overheard
        excerpt it prompts with is not kept, only the line that set it off.

        `timer` is an optional `TurnTimer` (see src/harness/turn_timer.py) for
        `[timing]` latency logs on a voice turn — None everywhere else (chat
        SSE, sidekick, calls, sms, background agents), which is a no-op.

        Turns are persisted to the conversation/message tables. Raises
        ConversationClosedError before yielding anything if the conversation
        has been closed — closed conversations can never be continued.
        """
        _mark_timing(timer, "loop_entered")
        pending_writes: list[Future] = []
        turn_state: dict[str, Any] = {}
        try:
            yield from self._conversation_turn(
                prompt,
                conversation_uuid,
                prompt_source,
                conversation,
                pending_writes,
                images,
                persist_prompt_as,
                turn_state,
                timer,
            )
        finally:
            user_message = turn_state.get("user_message")
            if persist_prompt_as is not None and user_message is not None:
                user_message["content"] = persist_prompt_as
            history = self.conversations.get(conversation_uuid)
            if history:
                self._strip_old_images(history)
            # Write-behind persistence is collected here rather than left to
            # finish on its own, so the transcript is complete by the time
            # the caller sees the turn end.
            self._await_writes(pending_writes)

    def _conversation_turn(
        self,
        prompt: str,
        conversation_uuid: UUID,
        prompt_source: PromptSourceEnum,
        conversation: Conversation | None,
        pending_writes: list[Future],
        images: list[dict[str, Any]] | None = None,
        persist_prompt_as: str | None = None,
        turn_state: dict[str, Any] | None = None,
        timer: "TurnTimer | None" = None,
    ) -> Iterator[dict[str, Any]]:
        if self.tool_service is None:
            self.tool_service = ToolService()
        if self.conversation_service is None:
            self.conversation_service = ConversationService()

        # Everything the request needs that does not depend on the
        # conversation goes out first, in parallel. The tool list and the MCP
        # registry are database round trips that used to run one after the
        # other, after the conversation lookups; now they overlap with them
        # and with each other, and are collected below.
        tools_future = _SETUP_POOL.submit(self.tool_service.list_tools)
        mcp_future = _SETUP_POOL.submit(self._load_mcp_servers)

        # Gate the turn on the persisted conversation state (may raise
        # ConversationClosedError), creating the row on first use. A caller
        # that already fetched the row hands it in; the gate still applies.
        if conversation is None or str(conversation.uuid) != str(conversation_uuid):
            conversation = self.conversation_service.ensure_open_conversation(
                conversation_uuid
            )
        elif conversation.is_closed:
            raise ConversationClosedError(
                f"Conversation {conversation_uuid} is closed and cannot be continued."
            )
        _mark_timing(timer, "conversation_ready")

        # Kick off memory retrieval now and collect it just before the request
        # goes out. The history load below does not depend on it, so the
        # embed-and-search runs inside time the turn was already spending.
        memory_future = self._start_memory_retrieval(prompt, conversation)

        # Rehydrate LLM history from persisted messages when this process
        # hasn't seen the conversation yet (e.g. after a restart).
        rehydrated = conversation_uuid not in self.conversations
        if rehydrated:
            self.conversations[conversation_uuid] = self.conversation_service.load_history(
                conversation
            )
        history = self.conversations[conversation_uuid]
        # Where this turn starts in history, so a sidekick pass can take the
        # whole turn back out.
        history_start = len(history)
        _mark_timing(timer, "history_loaded", rehydrated=rehydrated, messages=len(history))

        # A sidekick turn may end in a pass, and a pass leaves no trace: the
        # overheard excerpt is not kept unless Nova actually said something
        # about it. So its rows wait here until the reply is known.
        sidekick = prompt_source is PromptSourceEnum.SIDEKICK_PROMPT
        deferred_rows: list[tuple[MessageRole, str]] = []

        def persist(role: MessageRole, content: str) -> None:
            """
            Persist a message of this turn, in order.

            The user's message was written behind (below); everything after it
            waits for that write to land first, so the table never shows a
            reply ahead of the question it answers. By the time anything else
            is persisted the model has replied, so the wait is free.

            A sidekick turn holds every row until Nova's own reply is
            persisted, then writes them all in order.
            """
            if sidekick and role is not MessageRole.NOVA:
                deferred_rows.append((role, content))
                return
            if pending_writes:
                self._await_writes(pending_writes)
                pending_writes.clear()
            for deferred_role, deferred_content in deferred_rows:
                self._persist_message(conversation, deferred_role, deferred_content)
            deferred_rows.clear()
            self._persist_message(conversation, role, content)

        tool_context = {"conversation_uuid": str(conversation_uuid)}

        started_at = time.monotonic()

        tools_wait_started = time.monotonic()
        try:
            tools = tools_future.result()
        except Exception:
            tools = []
        _mark_timing(
            timer,
            "tools_collected",
            blocked_ms=round((time.monotonic() - tools_wait_started) * 1000),
            count=len(tools),
        )

        tools_by_name: dict[str, Any] = {}
        claude_tools: list[dict[str, Any]] = []
        excluded = prompt_source.excluded_tools()
        for tool in tools:
            name = (tool.name or "").strip()
            config = tool.config if isinstance(tool.config, dict) else {}
            input_schema = config.get("input_schema")
            if not name or not isinstance(input_schema, dict) or name in excluded:
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
        # mid-turn can't flip the tool list between iterations. The lookup
        # never raises (see _load_mcp_servers).
        mcp_wait_started = time.monotonic()
        mcp_servers = mcp_future.result() or None
        _mark_timing(
            timer,
            "mcp_collected",
            blocked_ms=round((time.monotonic() - mcp_wait_started) * 1000),
            count=len(mcp_servers or []),
        )

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
        memory_block = self._collect_memory(memory_future, timer)
        user_text = self._augment(prompt, memory_block)
        if images:
            # Images before the text, as Claude reads them best.
            history.append(
                {
                    "role": "user",
                    "content": [*images, {"type": "text", "text": user_text}],
                }
            )
        else:
            history.append({"role": "user", "content": user_text})
        if turn_state is not None:
            turn_state["user_message"] = history[-1]
        _mark_timing(timer, "user_message_appended")
        user_row = self._photo_note(
            prompt if persist_prompt_as is None else persist_prompt_as, images
        )
        # Write-behind. The message is already in history; the model request
        # should not wait on the insert. Collected before the turn returns.
        if sidekick:
            persist(MessageRole.USER, user_row)
        else:
            pending_writes.append(
                self._persist_message_later(conversation, MessageRole.USER, user_row)
            )

        # Progress reporting across a multi-round turn.
        #
        # This used to be a single flag: one acknowledgment per turn, and every
        # later round silent, on the theory that round-by-round text is
        # play-by-play narration. Spoken, that theory is wrong. A turn that
        # calls three tools said "let me pull that up" and then went quiet for
        # the length of the work, which sounds like Nova stopped listening.
        #
        # So a voice turn may speak again as it goes, bounded by
        # `_MAX_SPOKEN_PROGRESS_LINES` and by not repeating itself. A turn with
        # no voice keeps the old behaviour exactly — one status line, because
        # there is no silence there to fill.
        progress_spoken = 0
        last_progress = ""
        status_shown = False

        # Whether this turn has a speaker. The live events below carry speech
        # regardless, and this is where a chat turn drops it.
        speak = prompt_source.wants_spoken_summary()
        early_line: str | None = None
        first_speech_marked = False

        def mark_first_speech(role: str, text: str) -> None:
            """Mark the turn's first spoken line, once, across every round."""
            nonlocal first_speech_marked
            if not first_speech_marked:
                first_speech_marked = True
                _mark_timing(timer, "first_speech_line", role=role, chars=len(text))

        def deliver(events: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
            """
            Yield a round's live events under the turn's limits.

            `LiveReply` decides WHAT a round says and shows and WHEN; this
            decides WHETHER, which is a turn-level question: a progress line
            past the narration cap, or one that repeats the last, is dropped
            here exactly as the end-of-round path would drop it. What was said
            is noted in `early_line` so the end of the round never says it
            again.
            """
            nonlocal early_line
            for event in events:
                if event["type"] == "text":
                    yield event
                    continue
                if not speak:
                    continue
                # Progress lines are held to a couple of sentences; an answer
                # is said as written.
                say = (
                    clamp_spoken(event["text"])
                    if event["role"] == "status"
                    else event["text"].strip()
                )
                if not say:
                    continue
                if event["role"] == "status" and (
                    progress_spoken >= _MAX_SPOKEN_PROGRESS_LINES
                    or is_repeat(say, last_progress)
                ):
                    continue
                early_line = say
                mark_first_speech(event["role"], say)
                yield {"type": "speech_text", "text": say, "role": event["role"]}

        for round_no in range(1, _AGENT_MAX_ITERATIONS + 1):
            if time.monotonic() - started_at > _AGENT_LOOP_TIMEOUT_SECONDS:
                fallback = "I hit a time limit while working on that and had to stop."
                # Persisted to the DB and spoken to the user below, but never
                # appended to the replayable `history` — this is a loop-level
                # giveup, not an assistant turn, and leaving it in history
                # would just be more text for the next request to carry.
                persist(MessageRole.NOVA, fallback)
                del history[history_start:]
                yield from self._failure_events(prompt_source, fallback)
                return

            # Whether this round already said something out loud. The reply is
            # read as it is written, so the spoken line usually goes out well
            # before the round finishes; the end-of-round paths below check
            # this so a turn never says the same thing twice.
            early_line = None
            live = LiveReply()
            hold = _PassHold(sidekick)
            # Set once this round retries after a pairing repair, so a
            # request that fails again never retries a second time.
            retried_after_pairing_repair = False

            while True:
                try:
                    # Repair before every request, not just the first: a
                    # dangling tool_use can also be left by a round that failed
                    # further down in this same loop (see the tool-call loop
                    # below). Cheap no-op when history is already well-formed.
                    self.repair_tool_pairing(history)
                    _mark_timing(
                        timer,
                        "model_request_sent",
                        round=round_no,
                        model=self.claude_service.get_current_model(),
                        effort=self.claude_service.effort,
                        tools=len(tools_arg or []),
                        history_msgs=len(history),
                    )
                    # `timer`/`round_no` are only passed when there is a timer:
                    # several tests stub `stream_response` with a fixed signature
                    # that has no room for extra kwargs, and timer is None on
                    # every one of them, so there is nothing for those kwargs to
                    # log anyway.
                    stream_kwargs: dict[str, Any] = {}
                    if timer is not None:
                        stream_kwargs = {"timer": timer, "round_no": round_no}
                    turn = self.claude_service.stream_response(
                        "",
                        context=history,
                        tools=tools_arg,
                        system=system_blocks,
                        mcp_servers=mcp_servers,
                        **stream_kwargs,
                    )
                    # This is the latency win, on both tracks. The `<speak>` block
                    # is written first, so its closing tag lands while the markdown
                    # answer beneath it is still being generated — and the moment
                    # it does, TTS can start. The prose then streams to the screen
                    # as it is written, and a pre-tool acknowledgment is spoken
                    # the instant the tool_use block opens rather than after its
                    # arguments finish. Waiting for the final message here (as
                    # this used to) meant every voice turn paid for the length of
                    # the WRITTEN answer before a word of the spoken one was said,
                    # and every chat turn saw nothing until the last token.
                    for item in turn:
                        if item is TOOL_USE_STARTED:
                            yield from deliver(hold.flush(live.tool_use_started()))
                        else:
                            yield from deliver(hold.feed(live.push(item)))
                    response = turn.message
                    break
                except TimeoutError:
                    # A line that had closed but was still waiting on its role is
                    # said now: the stream got far enough to say it.
                    yield from deliver(hold.flush(live.finish()))
                    fallback = "I hit a backend timeout while working on that and had to stop."
                    persist(MessageRole.NOVA, fallback)
                    del history[history_start:]
                    yield from self._failure_events(
                        prompt_source, fallback, early_line is not None
                    )
                    return
                except Exception as exc:
                    # Anthropic's 400 for a dangling tool_use/mcp_tool_use is
                    # recoverable: `repair_tool_pairing` fixes exactly what it
                    # is complaining about, so retry the request once before
                    # giving up. Anything else, or a second failure after the
                    # repair, falls through to the fallback below.
                    status = getattr(exc, "status_code", None)
                    lowered = str(exc).lower()
                    looks_like_pairing_error = (
                        not retried_after_pairing_repair
                        and (status == 400 or (status is None and "400" in lowered))
                        and "invalid_request_error" in lowered
                        and ("tool_result" in lowered or "tool_use" in lowered)
                    )
                    if looks_like_pairing_error:
                        retried_after_pairing_repair = True
                        self.repair_tool_pairing(history)
                        early_line = None
                        live = LiveReply()
                        hold = _PassHold(sidekick)
                        continue
                    yield from deliver(hold.flush(live.finish()))
                    fallback = f"Agent loop failed: {str(exc)}"
                    persist(MessageRole.NOVA, fallback)
                    del history[history_start:]
                    yield from self._failure_events(
                        prompt_source, fallback, early_line is not None
                    )
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
                persist(MessageRole.TOOL, json.dumps(record))

            # MCP calls already ran server-side; surface them to the UI the
            # same way client tool calls are surfaced, and keep an audit row.
            for record in self._describe_mcp_tool_uses(response):
                persist(MessageRole.TOOL, json.dumps(record))
                yield {
                    "type": "tool_call",
                    "tool": record["tool"],
                    "input": record["input"],
                }

            if not tool_uses and getattr(response, "stop_reason", None) == "pause_turn":
                # A long server-side search can pause the turn; replay the
                # assistant message unchanged to let it finish.
                history.append({"role": "assistant", "content": assistant_blocks})
                continue

            if not tool_uses:
                raw_text = self._extract_text(response)
                display_text = strip_speak_tags(raw_text)
                if sidekick and is_sidekick_pass(display_text):
                    # Nothing worth saying. The held live events are dropped
                    # unsaid, the turn is taken back out of history, and none
                    # of its rows are written.
                    del history[history_start:]
                    deferred_rows.clear()
                    yield {"type": "silent"}
                    return
                expects_reply = False
                if sidekick:
                    display_text, expects_reply = strip_expects_reply(display_text)
                # required: this is the answer the user asked for out loud.
                # A reply that is all table or all code reduces to no sayable
                # prose, and ending a turn in silence reads as failure.
                spoken_text = self._spoken_track(
                    prompt_source, display_text, required=True
                )
                # Persist before yielding so a client disconnect mid-stream
                # can't lose the reply.
                persist(MessageRole.NOVA, display_text)
                try:
                    # The round is over: whatever LiveReply was still holding
                    # — a spoken line waiting on its role, prose short of
                    # going live — goes out first. Inside the try, so a
                    # consumer that stops reading after the first piece still
                    # leaves the reply in history. The token has no closing
                    # punctuation, so it is always part of what was still
                    # held — never spoken earlier in the stream.
                    finish_events = hold.flush(live.finish())
                    if sidekick:
                        finish_events, held_token = _strip_expects_reply_events(
                            finish_events
                        )
                        expects_reply = expects_reply or held_token
                    yield from deliver(finish_events)
                    # Speech first, so the transport can start synthesizing
                    # before the prose is sent.
                    if spoken_text and early_line is None:
                        mark_first_speech("final", spoken_text)
                        yield {
                            "type": "speech_text",
                            "text": spoken_text,
                            "role": "final",
                        }
                    if display_text:
                        # The prose normally reached the screen as it was
                        # written; a round too short to have gone live sends
                        # it whole here. Either way the final event carries
                        # the tag-stripped text so a renderer can replace what
                        # it streamed with exactly what was written.
                        if not live.streamed:
                            yield {"type": "text", "text": display_text}
                        text_final_event = {"type": "text_final", "text": display_text}
                        if expects_reply:
                            text_final_event["expects_reply"] = True
                        yield text_final_event
                finally:
                    # Keep the full blocks (citations, search results) in
                    # history so follow-up turns stay valid; fall back to raw
                    # text when the model returned nothing to serialize.
                    history.append(
                        {"role": "assistant", "content": assistant_blocks or raw_text}
                    )
                return

            history.append({"role": "assistant", "content": assistant_blocks})

            # A turn handed in complete never saw the tool_use marker, so
            # LiveReply is told what the round was; a line it was still
            # holding is spoken here as the progress line it is.
            yield from deliver(hold.flush(live.finish(tool_round=True)))

            # What this round said before reaching for its tools.
            status_display = strip_speak_tags(self._extract_text(response))
            if status_display and early_line is not None:
                # Already said out loud, mid-generation, having passed the same
                # limits below. Count it, caption it, do not repeat it.
                progress_spoken += 1
                last_progress = early_line
                status_shown = True
                if not live.streamed:
                    yield {"type": "status_text", "text": status_display}

            elif status_display:
                # The line goes through the same ceiling as the answer, so a
                # model that turns chatty before a tool call cannot stall the
                # turn with narration the user has to sit through.
                progress_line = self._spoken_track(prompt_source, status_display)
                if progress_line:
                    progress_line = clamp_spoken(progress_line)
                say_it = (
                    progress_line is not None
                    and progress_spoken < _MAX_SPOKEN_PROGRESS_LINES
                    and not is_repeat(progress_line, last_progress)
                )

                # Show it when it is about to be said — audio with no caption
                # is worse than no audio — and otherwise only for the first
                # round, which is the one-acknowledgment behaviour every
                # medium without a speaker still gets.
                if say_it or not status_shown:
                    status_shown = True
                    # Unless the prose already streamed as prose — a long
                    # preamble before a tool call is on the screen already.
                    if not live.streamed:
                        yield {"type": "status_text", "text": status_display}

                if say_it:
                    progress_spoken += 1
                    last_progress = progress_line
                    mark_first_speech("status", progress_line)
                    yield {
                        "type": "speech_text",
                        "text": progress_line,
                        "role": "status",
                    }

            # `abort_reason` is set the moment a tool call turns out fatal —
            # an unrecoverable ToolExecutionError, or anything that escaped
            # ToolService's own wrapping entirely (a crash, a hard timeout,
            # a cancellation). The loop still finishes bookkeeping for every
            # tool_use below before acting on it: the assistant message
            # already in history (above) has every one of these ids, and the
            # API will reject the very next request unless each gets a
            # tool_result now, real or placeholder.
            tool_results: list[dict[str, Any]] = []
            abort_reason: str | None = None
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
                    persist(
                        MessageRole.TOOL,
                        json.dumps({"tool": block.name, "error": "Unknown tool."}),
                    )
                    continue

                if abort_reason is not None:
                    # An earlier tool_use in this same round already ended
                    # the turn; the rest never ran, but they still need a
                    # result so none of them is left dangling.
                    tool_results.append(self._interrupted_tool_result(block.id))
                    continue

                arguments = block.input if isinstance(block.input, dict) else {}
                yield {"type": "tool_call", "tool": block.name, "input": arguments}
                tool_started_at = time.monotonic()
                try:
                    print(f"Calling tool: {tool.name} with arguments: {arguments}")
                    result = self.tool_service.call_tool(tool, arguments, context=tool_context)
                    _mark_timing(
                        timer,
                        "tool_done",
                        name=tool.name,
                        dur_ms=round((time.monotonic() - tool_started_at) * 1000),
                    )
                    content = self._tool_result_content(result)
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
                    persist(
                        MessageRole.TOOL,
                        json.dumps(
                            {
                                "tool": block.name,
                                "input": arguments,
                                "result": self._without_images(content),
                            }
                        ),
                    )
                except ToolExecutionError as exc:
                    _mark_timing(
                        timer,
                        "tool_done",
                        name=tool.name,
                        dur_ms=round((time.monotonic() - tool_started_at) * 1000),
                        error=True,
                    )
                    persist(
                        MessageRole.TOOL,
                        json.dumps(
                            {"tool": block.name, "input": arguments, "error": str(exc)}
                        ),
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(exc),
                            "is_error": True,
                        }
                    )
                    if not exc.recoverable:
                        abort_reason = "I ran into a tool execution issue and had to stop."
                except Exception as exc:
                    # Anything else is a tool call that never produced a
                    # result at all — a crash, a timeout that escaped
                    # ToolService, a cancellation. A placeholder goes in its
                    # place so this tool_use is never left dangling; the
                    # repair step before the next request would otherwise
                    # have to catch it instead.
                    _mark_timing(
                        timer,
                        "tool_done",
                        name=tool.name,
                        dur_ms=round((time.monotonic() - tool_started_at) * 1000),
                        error=True,
                    )
                    try:
                        persist(
                            MessageRole.TOOL,
                            json.dumps(
                                {"tool": block.name, "input": arguments, "error": str(exc)}
                            ),
                        )
                    except Exception:
                        pass
                    tool_results.append(self._interrupted_tool_result(block.id))
                    abort_reason = "I ran into a tool execution issue and had to stop."

            # Every tool_use from this round has a result now, so the pairing
            # is valid the moment this message lands in history — never
            # append the assistant's tool_use blocks and the fallback text
            # without it in between.
            history.append({"role": "user", "content": tool_results})

            if abort_reason is not None:
                history.append({"role": "assistant", "content": abort_reason})
                persist(MessageRole.NOVA, abort_reason)
                yield from self._failure_events(
                    prompt_source, abort_reason, early_line is not None
                )
                return

        fallback = "I hit a loop limit while working on that and had to stop."
        history.append({"role": "assistant", "content": fallback})
        persist(MessageRole.NOVA, fallback)
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

        restrict_management_tools = responsibility_id is not None

        parts: list[str] = []
        if responsibility_id is not None:
            responsibility = ResponsibilityDao().get(responsibility_id)
            if responsibility is None:
                raise ValueError(f"Responsibility with id {responsibility_id} not found")
            parts.append(responsibility.to_prompt().strip())
            parts.append(_RESPONSIBILITY_RUN_RESTRICTION)
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
                kwargs={"restrict_management_tools": restrict_management_tools},
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

        return self._run_agent_loop(
            task_prompt, restrict_management_tools=restrict_management_tools
        )

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
        restrict_management_tools: bool = False,
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
                full_prompt,
                system=PromptEnums.BACKGROUND_AGENT_PROMPT.load(),
                restrict_management_tools=restrict_management_tools,
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

    def _run_agent_loop(
        self,
        task_prompt: str,
        system: str | None = None,
        restrict_management_tools: bool = False,
    ) -> str:
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
            if restrict_management_tools and name in _RESPONSIBILITY_RESTRICTED_TOOLS:
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

            # Set once this round retries after a pairing repair, so a
            # request that fails again never retries a second time.
            retried_after_pairing_repair = False
            while True:
                try:
                    # Same backstop as the conversation loop: fix any dangling
                    # tool_use/tool_result pairing before it reaches the API.
                    self.repair_tool_pairing(history)
                    response = self.claude_service.get_response(
                        "",
                        context=history,
                        tools=tools_arg,
                        system=system,
                        mcp_servers=mcp_servers,
                    )
                    break
                except TimeoutError:
                    return "I hit a backend timeout while working on that and had to stop."
                except Exception as exc:
                    # Same self-heal as the conversation loop: a 400 for a
                    # dangling tool_use/mcp_tool_use is exactly what
                    # `repair_tool_pairing` fixes, so retry once before
                    # giving up.
                    status = getattr(exc, "status_code", None)
                    lowered = str(exc).lower()
                    looks_like_pairing_error = (
                        not retried_after_pairing_repair
                        and (status == 400 or (status is None and "400" in lowered))
                        and "invalid_request_error" in lowered
                        and ("tool_result" in lowered or "tool_use" in lowered)
                    )
                    if looks_like_pairing_error:
                        retried_after_pairing_repair = True
                        self.repair_tool_pairing(history)
                        continue
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
                    content = self._tool_result_content(result)
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
