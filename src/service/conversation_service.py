import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, ClassVar
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from src.dao.conversation_dao import ConversationDao
from src.dao.message_dao import MessageDao
from src.dao.project_dao import ProjectDao
from src.model.conversation import Conversation
from src.model.message import Message, MessageRole

# How long an SMS thread stays "the same conversation" before a new text
# starts a fresh one instead of resuming it. Defined here (not in
# sms_controller) so sms_controller's same-thread check and the worker's
# auto-close job share one source of truth instead of two literals that
# could drift; sms_controller imports this constant.
SMS_THREAD_IDLE_HOURS = 12

# How long a non-SMS conversation (voice/app/glasses) may sit idle before the
# worker auto-closes it, unless overridden by NOVA_CONVERSATION_IDLE_HOURS.
# Much shorter than the SMS window: voice/app sessions do not have the
# "reply days later" pattern SMS has to accommodate, and a short default is
# what makes conversations actually reach memory (see check_for_stale_conversations).
_DEFAULT_CONVERSATION_IDLE_HOURS = 3

# Nate's rule: no conversation — of any kind — carries over from one local
# day into the next, independent of the idle thresholds above. A chatty
# conversation active right up to 11:59pm still closes at midnight. zoneinfo
# (not a fixed UTC offset) is required so this tracks America/Denver's
# daylight-saving transitions correctly instead of drifting an hour twice a
# year.
_DEFAULT_CONVERSATION_ROLLOVER_TZ = "America/Denver"


def _most_recent_local_midnight_utc(tz_name: str, now_utc: datetime) -> datetime:
    """
    The most recent local midnight in tz_name, as a UTC-aware datetime.

    Recomputed fresh from "now" on every call rather than scheduled to fire
    at a clock time — that is what makes the daily rollover restart-safe: if
    the worker is down over a midnight, the next run still asks "what's the
    most recent local midnight before right now", which is today's, so a
    conversation from two days ago still closes. There is no missed-event
    state that needs recovering.
    """
    tz = ZoneInfo(tz_name)
    local_now = now_utc.astimezone(tz)
    local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_midnight.astimezone(timezone.utc)


class ConversationClosedError(Exception):
    """Raised when a turn targets a conversation that has been closed."""


class ConversationService:
    # In-process registry of conversations closed by switch_project, mapping
    # old uuid -> successor uuid. Class-level because the tool layer builds a
    # fresh service instance per call while the controller holds its own; the
    # controller pops entries after each turn to redirect the client.
    _switch_targets: ClassVar[dict[UUID, UUID]] = {}

    # Conversations where Nova decided the user is done talking this turn,
    # mapping uuid -> the reason it gave. Same lifecycle as _switch_targets:
    # the tool layer writes it, the controller pops it at the end of the turn
    # and acts on it in whatever way its transport calls "stop" — going idle
    # on the browser socket, hanging up on a phone call.
    _stop_requests: ClassVar[dict[UUID, str]] = {}

    # Per-conversation silent mode: when True, Nova's live replies are not
    # spoken (text/events to the client are unaffected). Class-level for the
    # same reason as the two dicts above — the tool layer builds a fresh
    # service instance per call, the controller holds its own, and this has
    # to be visible to both. Unlike _switch_targets/_stop_requests this is
    # read (not popped) on every line of a turn's speech, since it has to
    # keep applying for the whole conversation, not just the turn that set
    # it. Defaults to OFF and is never persisted: a fresh process (reconnect
    # included, since nothing keys this off a browser session) starts quiet
    # mode off, per spec — it is a live toggle, not a durable preference.
    _silent_mode: ClassVar[dict[UUID, bool]] = {}

    # conversation_uuid -> the live /ws/transcribe sockets listening for
    # that conversation's silent-mode changes, each as a coroutine function
    # that sends one event down that socket. Same pattern as
    # VisionService.cameras / SidekickService._connections: the connection
    # that owns the live websocket hands this process-wide registry a way
    # to reach it, rather than this module importing the controller (a
    # cycle) or trying to hold the websocket itself. A list, not a single
    # entry, because unlike the glasses camera a conversation can have more
    # than one live listener (e.g. a browser tab and the iOS app open on
    # the same conversation at once).
    _silent_mode_listeners: ClassVar[dict[UUID, list[Callable[[dict], Awaitable[None]]]]] = {}

    # The API process's event loop, bound once at startup (see main.py's
    # lifespan, same as VisionService.bind_loop / SidekickService.bind_loop).
    # set_silent_mode can run on the agent loop's worker thread (the
    # set_silent_mode tool executes there, same as the `look` tool), so
    # reaching a listener requires scheduling onto this loop rather than a
    # bare await.
    loop: ClassVar[Any] = None

    @classmethod
    def bind_loop(cls, loop: Any) -> None:
        """Attach this process's event loop, so silent-mode pushes can schedule onto it."""
        cls.loop = loop

    @classmethod
    def register_silent_mode_listener(
        cls, conversation_uuid: UUID, send: Callable[[dict], Awaitable[None]]
    ) -> None:
        """A /ws/transcribe connection just learned its conversation id: it can now be pushed to."""
        listeners = cls._silent_mode_listeners.setdefault(conversation_uuid, [])
        if send not in listeners:
            listeners.append(send)

    @classmethod
    def unregister_silent_mode_listener(
        cls, conversation_uuid: UUID, send: Callable[[dict], Awaitable[None]]
    ) -> None:
        listeners = cls._silent_mode_listeners.get(conversation_uuid)
        if not listeners:
            return
        if send in listeners:
            listeners.remove(send)
        if not listeners:
            del cls._silent_mode_listeners[conversation_uuid]

    def __init__(self):
        self.conversation_dao = ConversationDao()
        self.message_dao = MessageDao()
        self.project_dao = ProjectDao()

    def ensure_open_conversation(self, conversation_uuid: UUID) -> Conversation:
        """
        Fetch the conversation for a turn, creating it on first use.

        Closed conversations are terminal by design — they can never be
        reopened or appended to.
        """
        conversation = self.conversation_dao.get_by_uuid(conversation_uuid)
        if conversation is None:
            return self.conversation_dao.create_conversation(
                Conversation(uuid=conversation_uuid)
            )
        if conversation.is_closed:
            raise ConversationClosedError(
                f"Conversation {conversation_uuid} is closed and cannot be continued."
            )
        return conversation

    def record_message(
        self,
        conversation: Conversation,
        role: MessageRole,
        content: str,
    ) -> Message:
        message = self.message_dao.create_message(
            Message(
                conversation_uuid=conversation.uuid,
                role=role,
                content=content,
            )
        )
        self.conversation_dao.touch_last_message(
            conversation.uuid,
            datetime.now(timezone.utc).isoformat(),
        )
        return message

    def load_history(self, conversation: Conversation) -> list[dict]:
        """
        Rebuild Claude-format history from persisted messages.

        Only user/nova rows become turns. Tool rows are audit records of
        tool_use/tool_result pairs; they cannot be replayed as plain text
        without breaking the Claude message format, so they are skipped.
        """
        history: list[dict] = []
        for message in self.message_dao.get_for_conversation(conversation.uuid):
            if not message.content:
                continue
            if message.role == MessageRole.USER:
                history.append({"role": "user", "content": message.content})
            elif message.role == MessageRole.NOVA:
                history.append({"role": "assistant", "content": message.content})
        return history

    def close_conversation(self, conversation_uuid: UUID) -> Conversation | None:
        """Close a conversation. Idempotent; closed conversations stay closed."""
        return self.conversation_dao.set_closed(conversation_uuid)

    def get_unprocessed_closed_conversations(self) -> list[Conversation]:
        """Closed conversations awaiting memory-chunk processing."""
        return self.conversation_dao.get_unprocessed_closed()

    def check_for_stale_conversations(self) -> None:
        """
        Auto-close conversations the worker hasn't heard from in a while, and
        separately close every open conversation left over from a prior
        local day (the daily rollover — see _most_recent_local_midnight_utc).

        Non-SMS conversations use NOVA_CONVERSATION_IDLE_HOURS (default 3h);
        SMS threads use SMS_THREAD_IDLE_HOURS (12h) so this matches the
        continuity window sms_controller uses to decide whether an incoming
        text resumes the existing thread rather than starting a new one. The
        rollover applies on top of both — it closes a conversation even if it
        is well within its idle window, as long as its last activity predates
        the most recent local midnight in NOVA_CONVERSATION_ROLLOVER_TZ
        (default America/Denver).
        """
        idle_hours = float(
            os.getenv("NOVA_CONVERSATION_IDLE_HOURS", str(_DEFAULT_CONVERSATION_IDLE_HOURS))
        )
        rollover_tz = os.getenv("NOVA_CONVERSATION_ROLLOVER_TZ", _DEFAULT_CONVERSATION_ROLLOVER_TZ)
        rollover_cutoff_utc = _most_recent_local_midnight_utc(
            rollover_tz, datetime.now(timezone.utc)
        )
        self.conversation_dao.check_for_stale_conversations(
            idle_hours, SMS_THREAD_IDLE_HOURS, rollover_cutoff_utc
        )

    def mark_processed(self, conversation_uuid: UUID) -> Conversation | None:
        return self.conversation_dao.set_processed(conversation_uuid)

    def get_messages(self, conversation_uuid: UUID) -> list[Message]:
        return self.message_dao.get_for_conversation(conversation_uuid)

    def get_conversation(self, conversation_uuid: UUID) -> Conversation | None:
        return self.conversation_dao.get_by_uuid(conversation_uuid)

    def assign_project(self, project_id: int, conversation_uuid: str) -> dict:
        """
        Attach the current conversation to a project.

        A conversation can belong to at most one project, ever. Re-homing
        messages is not allowed — the caller must open a new conversation to
        work under a different project. Exposed to the agent loop as a tool;
        conversation_uuid is injected by the harness, not the model.
        """
        uuid = UUID(str(conversation_uuid))

        conversation = self.conversation_dao.get_by_uuid(uuid)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_uuid} does not exist.")
        if conversation.is_closed:
            raise ConversationClosedError(
                f"Conversation {conversation_uuid} is closed."
            )
        if conversation.project_id is not None:
            raise ValueError(
                "This conversation is already attached to a project. "
                "Conversations can belong to at most one project — use the "
                "switch_project tool to continue under a different project "
                "in a fresh conversation."
            )

        project = self.project_dao.get(int(project_id))
        if project is None:
            raise ValueError(f"Project {project_id} does not exist.")

        self.conversation_dao.set_project(uuid, project.id)
        return {
            "status": "assigned",
            "conversation_uuid": str(uuid),
            "project": {"id": project.id, **project.to_payload()},
        }

    def switch_project(self, project_id: int, conversation_uuid: str) -> dict:
        """
        Continue the user's session under a different project.

        Messages and conversations belong to at most one project, ever, so a
        "switch" never re-homes anything. If the current conversation has no
        project yet, it is simply attached in place. Otherwise the current
        conversation is closed and a fresh conversation attached to the target
        project takes its place; the controller redirects the client to the
        successor at the end of the turn. Exposed to the agent loop as a tool;
        conversation_uuid is injected by the harness, not the model.
        """
        uuid = UUID(str(conversation_uuid))

        conversation = self.conversation_dao.get_by_uuid(uuid)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_uuid} does not exist.")
        if conversation.is_closed:
            raise ConversationClosedError(f"Conversation {conversation_uuid} is closed.")

        project = self.project_dao.get(int(project_id))
        if project is None:
            raise ValueError(f"Project {project_id} does not exist.")
        project_payload = {"id": project.id, **project.to_payload()}

        if conversation.project_id == project.id:
            return {
                "status": "unchanged",
                "conversation_uuid": str(uuid),
                "project": project_payload,
                "note": "This conversation is already attached to that project.",
            }

        if conversation.project_id is None:
            # Nothing to re-home — attach the current conversation in place.
            self.conversation_dao.set_project(uuid, project.id)
            return {
                "status": "assigned",
                "conversation_uuid": str(uuid),
                "project": project_payload,
            }

        # Create the successor first so a failure here leaves the current
        # conversation untouched and usable.
        successor = self.conversation_dao.create_conversation(
            Conversation(uuid=uuid4())
        )
        self.conversation_dao.set_project(successor.uuid, project.id)
        self.record_message(
            successor,
            MessageRole.NOVA,
            f"(Continued under project '{project.name}' after switching from a "
            "previous conversation. That conversation's history belongs to its "
            "own project and does not carry over.)",
        )
        self.conversation_dao.set_closed(uuid)
        ConversationService._switch_targets[uuid] = successor.uuid

        return {
            "status": "switched",
            "closed_conversation_uuid": str(uuid),
            "new_conversation_uuid": str(successor.uuid),
            "project": project_payload,
            "note": (
                "The previous conversation was closed and the chat will continue "
                "under the new conversation automatically — no action needed "
                "from the user."
            ),
        }

    def pop_switch_target(self, conversation_uuid: UUID) -> UUID | None:
        """Successor of a conversation closed by switch_project this turn, if any."""
        return ConversationService._switch_targets.pop(conversation_uuid, None)

    def end_session(self, conversation_uuid: str, reason: str | None = None) -> dict:
        """
        Signal that the user is finished talking for now.

        Exposed to the agent loop as a tool so Nova can end a session by
        understanding what the user meant rather than by matching a phrase.
        The spoken paths have a hardcoded stop-phrase list as a fast path, but
        it only catches the exact wordings someone thought of in advance —
        "alright I'm good", "cool, later", or a simple "that's it" all sail
        past it and leave Nova listening.

        This ends the *session*, not the conversation: the conversation stays
        open and the user can pick it straight back up. What "end" means is
        left to the transport — the browser socket returns to idle, a phone
        call hangs up. conversation_uuid is injected by the harness, not the
        model.
        """
        uuid = UUID(str(conversation_uuid))
        ConversationService._stop_requests[uuid] = (reason or "").strip() or (
            "The user indicated they were finished."
        )
        return {
            "status": "ending",
            "note": (
                "Say a short goodbye and nothing else. The session ends as soon "
                "as this turn finishes; the conversation stays open, so the user "
                "can start talking again whenever they like."
            ),
        }

    def pop_stop_request(self, conversation_uuid: UUID) -> str | None:
        """Reason Nova ended the session this turn, if it did."""
        return ConversationService._stop_requests.pop(conversation_uuid, None)

    def set_silent_mode(self, conversation_uuid: str, enabled: bool) -> dict:
        """
        Turn silent mode on or off for this conversation.

        Only the live-reply TTS is affected: the ASR pipeline, the agent
        loop, and the text sent to the client all keep working exactly as
        normal — only the speaker is muted. Background Sidekick reports
        (report_type 'speak') are a separate path and are never affected by
        this flag, by design.

        Shared by the `set_silent_mode` voice tool (conversation_uuid
        injected by the harness) and the REST endpoint the web/iOS toggle
        calls, so both ways of flipping it go through one setter and can
        never drift out of sync.
        """
        uuid = UUID(str(conversation_uuid))
        enabled = bool(enabled)
        ConversationService._silent_mode[uuid] = enabled
        ConversationService._push_silent_mode_state(uuid, enabled)
        return {"status": "ok", "silentMode": enabled}

    def is_silent(self, conversation_uuid: UUID) -> bool:
        """Whether live replies should be spoken for this conversation. Defaults to False."""
        return ConversationService._silent_mode.get(conversation_uuid, False)

    @classmethod
    def _push_silent_mode_state(cls, conversation_uuid: UUID, enabled: bool) -> None:
        """
        Notify every live /ws/transcribe socket for this conversation that
        silent mode changed, so a client never has to poll GET
        /conversations/{id} to see what the set_silent_mode tool (or another
        client's REST call) just did.

        Best-effort and fire-and-forget: no listener for this conversation,
        or no loop bound yet (e.g. a unit test with no running server), is
        the normal case, not an error — the state is still recorded in
        _silent_mode above regardless of whether anyone is listening right
        now, which is what a fresh connection reads via is_silent() on
        connect.
        """
        listeners = cls._silent_mode_listeners.get(conversation_uuid)
        if not listeners or cls.loop is None:
            return
        payload = {"type": "silent_mode_state", "enabled": enabled}
        for send in list(listeners):
            try:
                asyncio.run_coroutine_threadsafe(send(payload), cls.loop)
            except Exception:
                continue
