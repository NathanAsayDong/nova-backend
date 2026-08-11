from src.dao.base_dao import BaseDao
from src.model.mcp_server import McpServer


class McpServerDao(BaseDao):
    _table = "mcp_server"
    _model_class = McpServer

    def get(self, id: int) -> McpServer | None:
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

    def get_by_oauth_state(self, state: str) -> McpServer | None:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("oauth_state", state)
            .maybe_single()
            .execute()
        )
        if response is None or response.data is None:
            return None
        return self._to_model(self._model_class, response.data)

    def get_by_name(self, name: str) -> McpServer | None:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("name", name)
            .maybe_single()
            .execute()
        )
        if response is None or response.data is None:
            return None
        return self._to_model(self._model_class, response.data)

    def get_all(self) -> list[McpServer]:
        response = (
            self.client.table(self._table)
            .select("*")
            .order("name", desc=False)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data]

    def get_enabled(self) -> list[McpServer]:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("enabled", True)
            .order("name", desc=False)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data]

    def create(self, entity: McpServer) -> McpServer:
        response = (
            self.client.table(self._table)
            .insert(entity.to_payload())
            .execute()
        )
        return self._to_model(self._model_class, response.data[0])

    def update(self, id: int, columns: dict) -> McpServer | None:
        response = (
            self.client.table(self._table)
            .update(columns)
            .eq("id", id)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])

    def delete(self, id: int) -> None:
        self.client.table(self._table).delete().eq("id", id).execute()
