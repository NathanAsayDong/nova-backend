from uuid import UUID

from src.dao.base_dao import BaseDao
from src.model.message import Message


class MessageDao(BaseDao):
    _table = "message"
    _model_class = Message

    def create_message(self, message: Message) -> Message:
        response = (
            self.client.table(self._table)
            .insert(message.to_payload())
            .execute()
        )
        return self._to_model(self._model_class, response.data[0])

    def count_for_conversations(self, conversation_uuids: list[UUID]) -> int:
        if not conversation_uuids:
            return 0
        response = (
            self.client.table(self._table)
            .select("id")
            .in_("conversation_uuid", [str(uuid) for uuid in conversation_uuids])
            .execute()
        )
        return len(response.data or [])

    def get_for_conversation(self, conversation_uuid: UUID) -> list[Message]:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("conversation_uuid", str(conversation_uuid))
            .order("created_at", desc=False)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data]