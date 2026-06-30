from src.dao.base_dao import BaseDao
from src.model.responsibility import Responsibility


class ResponsibilityDao(BaseDao):
    """
    DAO for Responsibility model.
    """
    _table = "responsibility"
    _model_class = Responsibility

    def get(self, id: int) -> Responsibility | None:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("id", id)
            .maybe_single()
            .execute()
        )
        if response.data is None:
            return None
        return self._to_model(self._model_class, response.data)

    def get_all(self) -> list[Responsibility]:
        response = self.client.table(self._table).select("*").execute()
        return [self._to_model(self._model_class, row) for row in response.data]

    def create(self, entity: Responsibility) -> Responsibility:
        response = (
            self.client.table(self._table)
            .insert(entity.to_payload())
            .execute()
        )
        return self._to_model(self._model_class, response.data[0])

    def update(self, id: int, entity: Responsibility) -> Responsibility | None:
        response = (
            self.client.table(self._table)
            .update(entity.to_payload())
            .eq("id", id)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])

    def delete(self, id: int) -> None:
        self.client.table(self._table).delete().eq("id", id).execute()
