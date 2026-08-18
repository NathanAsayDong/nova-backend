from datetime import datetime, timezone
from typing import ClassVar
from uuid import UUID, uuid4

from src.dao.conversation_dao import ConversationDao
from src.dao.message_dao import MessageDao
from src.dao.project_dao import ProjectDao
from src.model.conversation import Conversation
from src.model.message import Message, MessageRole


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
        """Check for conversations that have been open for too long and closes them."""
        self.conversation_dao.check_for_stale_conversations()

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
