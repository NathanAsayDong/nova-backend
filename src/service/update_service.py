"""
Updates: Nova's way of surfacing finished background work.

When a sub-agent completes a task the user wasn't around for, a summarizer
writes an Update row. The client shows unviewed updates as a badge, and the
agent loop exposes get_unviewed_updates / mark_all_updates_viewed as tools so
the user can just ask Nova "what's new?" and have the badge clear afterwards.
"""

from src.dao.conversation_dao import ConversationDao
from src.dao.project_dao import ProjectDao
from src.dao.update_dao import UpdateDao
from src.model.update import Update


class UpdateService:
    def __init__(self) -> None:
        self.update_dao = UpdateDao()
        self.project_dao = ProjectDao()
        self.conversation_dao = ConversationDao()

    def _to_dict(self, update: Update) -> dict:
        """
        JSON-serializable view with the project/conversation context resolved,
        so a reader (model or client) can tell WHY the background work ran
        without extra lookups.
        """
        project = None
        if update.project_id is not None:
            found = self.project_dao.get(update.project_id)
            if found is not None:
                project = {"id": found.id, **found.to_payload()}

        conversation_uuid = None
        if update.conversation_id is not None:
            conversation = self.conversation_dao.get_by_id(update.conversation_id)
            if conversation is not None:
                conversation_uuid = str(conversation.uuid)

        return {
            "id": update.id,
            "update_message": update.update_message,
            "is_viewed": update.is_viewed,
            "created_at": (
                update.created_at.isoformat()
                if hasattr(update.created_at, "isoformat")
                else update.created_at
            ),
            "project": project,
            "conversation_id": update.conversation_id,
            "conversation_uuid": conversation_uuid,
        }

    def create_update(
        self,
        update_message: str,
        project_id: int | None = None,
        conversation_id: int | None = None,
    ) -> dict:
        """
        Record a new update for the user to see.

        Called by the background pipeline after a sub-agent finishes and its
        work has been summarized. Attach the project and/or conversation the
        work came from whenever they are known — that context is what tells
        the user why the agent ran at all.
        """
        update_message = (update_message or "").strip()
        if not update_message:
            raise ValueError("An update message is required.")

        if project_id is not None:
            if self.project_dao.get(int(project_id)) is None:
                raise ValueError(f"Project {project_id} does not exist.")
            project_id = int(project_id)

        if conversation_id is not None:
            if self.conversation_dao.get_by_id(int(conversation_id)) is None:
                raise ValueError(f"Conversation {conversation_id} does not exist.")
            conversation_id = int(conversation_id)

        created = self.update_dao.create(
            Update(
                update_message=update_message,
                project_id=project_id,
                conversation_id=conversation_id,
            )
        )
        return self._to_dict(created)

    def get_unviewed_updates(self) -> list[dict]:
        """
        Updates the user hasn't seen yet, oldest first.

        Exposed to the agent loop as a tool: when the user asks Nova to report
        on their updates, this is where the report comes from.
        """
        return [self._to_dict(update) for update in self.update_dao.get_unviewed()]

    def get_all_updates(self) -> list[dict]:
        """Every update, newest first."""
        return [self._to_dict(update) for update in self.update_dao.get_all()]

    def get_unviewed_count(self) -> int:
        """Cheap badge count for the client's updates indicator."""
        return len(self.update_dao.get_unviewed())

    def mark_update_viewed(self, update_id: int) -> dict:
        update = self.update_dao.mark_viewed(int(update_id))
        if update is None:
            raise ValueError(f"Update {update_id} does not exist.")
        return self._to_dict(update)

    def mark_all_updates_viewed(self) -> dict:
        """
        Clear the unviewed badge.

        Exposed to the agent loop as a tool so Nova can mark updates viewed
        after reporting them to the user.
        """
        flipped = self.update_dao.mark_all_viewed()
        return {"status": "viewed", "count": len(flipped)}
