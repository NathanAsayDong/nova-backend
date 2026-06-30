from src.dao.base_dao import BaseDao
from src.model.project import Project


class ProjectDao(BaseDao):
    """
    DAO for Project model.
    """
    _table = "project"
    _model_class = Project

    def get(self, id: int) -> Project | None:
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

    def get_all(self) -> list[Project]:
        response = self.client.table(self._table).select("*").execute()
        return [self._to_model(self._model_class, row) for row in response.data]

    def create(self, entity: Project) -> Project:
        response = (
            self.client.table(self._table)
            .insert(entity.to_payload())
            .execute()
        )
        return self._to_model(self._model_class, response.data[0])

    def update(self, id: int, entity: Project) -> Project | None:
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
