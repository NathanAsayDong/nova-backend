from datetime import datetime, timedelta
from uuid import UUID
from src.dao.base_dao import BaseDao
from src.model.conversation import Conversation

class ConversationDao(BaseDao):
    _table = "conversation"
    _model_class = Conversation

    def get_by_uuid(self, uuid: UUID) -> Conversation | None:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("uuid", str(uuid))
            .maybe_single()
            .execute()
        )
        if response is None or response.data is None:
            return None
        return self._to_model(self._model_class, response.data)

    def _update_columns(self, uuid: UUID, columns: dict) -> Conversation | None:
        response = (
            self.client.table(self._table)
            .update(columns)
            .eq("uuid", str(uuid))
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])

    def set_project(self, uuid: UUID, project_id: int) -> Conversation | None:
        return self._update_columns(uuid, {"project_id": project_id})

    def get_by_project(self, project_id: int) -> list[Conversation]:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("project_id", project_id)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data]

    def set_closed(self, uuid: UUID) -> Conversation | None:
        return self._update_columns(uuid, {"is_closed": True})

    def get_latest_open_for_sms(self, phone_number: str) -> Conversation | None:
        """
        The open SMS conversation for a number, newest first, or None.

        Ordering by last message rather than creation date is what makes a
        reply land in the thread the user was actually just in.
        """
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("sms_phone_number", phone_number)
            .eq("is_closed", False)
            .order("last_message_timestamp_utc", desc=True)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])

    def set_processed(self, uuid: UUID) -> Conversation | None:
        return self._update_columns(uuid, {"is_processed": True})

    def get_unprocessed_closed(self) -> list[Conversation]:
        """Closed conversations whose messages have not been distilled into memory yet."""
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("is_closed", True)
            .eq("is_processed", False)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data]

    def check_for_stale_conversations(self) -> None:
        """Conversations that are not closed and have no messages within the last 24 hours, update them to closed."""
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("is_closed", False)
            .lt("last_message_timestamp_utc", datetime.now() - timedelta(hours=24))
            .execute()
        )
        for row in response.data:
            self._update_columns(UUID(row["uuid"]), {"is_closed": True})

    def touch_last_message(self, uuid: UUID, timestamp_utc: str) -> Conversation | None:
        return self._update_columns(uuid, {"last_message_timestamp_utc": timestamp_utc})

    def create_conversation(self, conversation: Conversation) -> Conversation:
        response = (
            self.client.table(self._table)
            .insert(conversation.to_payload())
            .execute()
        )
        return self._to_model(self._model_class, response.data[0])

    def update_conversation(self, uuid: UUID, conversation: Conversation) -> Conversation | None:
        response = (
            self.client.table(self._table)
            .update(conversation.to_payload())
            .eq("uuid", uuid)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])