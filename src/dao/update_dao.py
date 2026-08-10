from src.dao.base_dao import BaseDao
from src.model.update import Update


class UpdateDao(BaseDao):
    _table = "update"
    _model_class = Update

    def get(self, id: int) -> Update | None:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("id", id)
            .maybe_single()
            .execute()
        )
        if response is None or response.data is None:
            return None
        return self._to_model(self._model_class, response.data)

    def get_all(self) -> list[Update]:
        response = (
            self.client.table(self._table)
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data]

    def get_unviewed(self) -> list[Update]:
        """Unviewed updates, oldest first so they read chronologically."""
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("is_viewed", False)
            .order("created_at", desc=False)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data]

    def create(self, entity: Update) -> Update:
        response = (
            self.client.table(self._table)
            .insert(entity.to_payload())
            .execute()
        )
        return self._to_model(self._model_class, response.data[0])

    def mark_viewed(self, id: int) -> Update | None:
        response = (
            self.client.table(self._table)
            .update({"is_viewed": True})
            .eq("id", id)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])

    def mark_all_viewed(self) -> list[Update]:
        """Mark every unviewed update as viewed; returns the rows that flipped."""
        response = (
            self.client.table(self._table)
            .update({"is_viewed": True})
            .eq("is_viewed", False)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data or []]

    def delete(self, id: int) -> None:
        self.client.table(self._table).delete().eq("id", id).execute()
