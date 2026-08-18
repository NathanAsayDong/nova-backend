"""
Updates: Nova's way of surfacing finished background work.

When a sub-agent completes a task the user wasn't around for, a summarizer
writes an Update row. The client shows unviewed updates as a badge, and the
agent loop exposes get_unviewed_updates / mark_all_updates_viewed as tools so
the user can just ask Nova "what's new?" and have the badge clear afterwards.
"""

from uuid import UUID

from src.dao.conversation_dao import ConversationDao
from src.dao.project_dao import ProjectDao
from src.dao.update_dao import UpdateDao
from src.model.report_type import (
    SUPPORTED_REPORT_TYPES,
    DeliveryStatus,
    ReportType,
)
from src.model.update import Update


class UpdateService:
    def __init__(self) -> None:
        self.update_dao = UpdateDao()
        self.project_dao = ProjectDao()
        self.conversation_dao = ConversationDao()

    def _to_dict(self, update: Update) -> dict:
        """
        JSON-serializable view with the project context resolved, so a reader
        (model or client) can tell WHY the background work ran without extra
        lookups.
        """
        project = None
        if update.project_id is not None:
            found = self.project_dao.get(update.project_id)
            if found is not None:
                project = {"id": found.id, **found.to_payload()}

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
            "conversation_uuid": (
                str(update.conversation_uuid) if update.conversation_uuid else None
            ),
            "report_type": str(update.report_type) if update.report_type else None,
            "delivery_status": str(update.delivery_status)
            if update.delivery_status
            else None,
        }

    @staticmethod
    def _validate_report_type(report_type: str | None) -> ReportType | None:
        if report_type is None:
            return None
        candidate = str(report_type).strip().lower()
        if not candidate:
            return None
        try:
            return ReportType(candidate)
        except ValueError:
            raise ValueError(
                f"Unknown report_type '{report_type}'. Valid types are "
                f"{[str(t) for t in ReportType]}."
            )

    def create_update(
        self,
        update_message: str,
        project_id: int | None = None,
        conversation_uuid: str | None = None,
        report_type: str | None = None,
    ) -> dict:
        """
        Record a new update for the user to see.

        Called by the background pipeline after a sub-agent finishes and its
        work has been summarized. Attach the project and/or conversation the
        work came from whenever they are known — that context is what tells
        the user why the agent ran at all.

        `report_type` is the delivery intent chosen when the work was spawned.
        With one set, the update is queued for UpdateDeliveryService to hand
        off to the matching channel; without one it is badge-only. An
        unsupported-but-known type (sms, chat) is recorded on the row and left
        undelivered rather than rejected, so flagging one never costs the user
        the update itself.
        """
        update_message = (update_message or "").strip()
        if not update_message:
            raise ValueError("An update message is required.")

        if project_id is not None:
            if self.project_dao.get(int(project_id)) is None:
                raise ValueError(f"Project {project_id} does not exist.")
            project_id = int(project_id)

        if conversation_uuid is not None:
            uuid_value = UUID(str(conversation_uuid))
            if self.conversation_dao.get_by_uuid(uuid_value) is None:
                raise ValueError(f"Conversation {conversation_uuid} does not exist.")
            conversation_uuid = str(uuid_value)

        validated_type = self._validate_report_type(report_type)
        deliverable = validated_type in SUPPORTED_REPORT_TYPES if validated_type else False

        created = self.update_dao.create(
            Update(
                update_message=update_message,
                project_id=project_id,
                conversation_uuid=conversation_uuid,
                report_type=validated_type,
                delivery_status=(
                    DeliveryStatus.PENDING if deliverable else DeliveryStatus.NOT_REQUIRED
                ),
            )
        )

        result = self._to_dict(created)
        if validated_type is not None and not deliverable:
            result["warning"] = (
                f"Reporting by {validated_type} is not deliverable yet — the "
                "update was recorded and will appear in the updates list, but "
                "nothing was sent. Only email and call can be delivered today."
            )
        return result

    # ---------- delivery ----------

    def get_pending_deliveries(self) -> list[Update]:
        """Updates queued for delivery, oldest first. Read by the dispatcher."""
        return self.update_dao.get_pending_deliveries()

    def claim_for_delivery(self, update_id: int) -> Update | None:
        """Take ownership of a pending update, or None if already claimed."""
        return self.update_dao.claim_for_delivery(int(update_id))

    def mark_delivered(self, update_id: int) -> Update | None:
        """
        Record a successful delivery.

        Also marks the update viewed: the user has now been emailed it or
        heard it read out on the phone, so leaving it lit in the badge would
        be asking them to read the same thing twice.
        """
        return self.update_dao.set_delivery_state(
            int(update_id), DeliveryStatus.DELIVERED, mark_viewed=True
        )

    def mark_delivery_failed(
        self, update_id: int, error: str, attempts: int | None = None
    ) -> Update | None:
        """Record a terminal delivery failure; the update stays unviewed."""
        return self.update_dao.set_delivery_state(
            int(update_id), DeliveryStatus.FAILED, error=str(error), attempts=attempts
        )

    def requeue_delivery(
        self, update_id: int, error: str | None = None, attempts: int | None = None
    ) -> Update | None:
        """
        Put a claimed update back on the queue for a later attempt.

        Used when a delivery didn't happen but is still worth trying — an
        unanswered call, a transient SMTP error — as opposed to one that
        failed for good.
        """
        return self.update_dao.set_delivery_state(
            int(update_id),
            DeliveryStatus.PENDING,
            error=str(error) if error else None,
            attempts=attempts,
        )

    def get_update(self, update_id: int) -> Update | None:
        return self.update_dao.get(int(update_id))

    def get_update_by_call_sid(self, call_sid: str) -> Update | None:
        return self.update_dao.get_by_call_sid(call_sid)

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
