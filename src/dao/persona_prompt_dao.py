from typing import Any

from src.dao.base_dao import BaseDao
from src.model.persona_prompt import PersonaPrompt


class PersonaPromptDao(BaseDao):
    """
    DAO for PersonaPrompt. Reads are plain table selects; writes go through
    the create_persona_version / activate_persona_version Postgres functions
    (migration 009) so "insert a new row and flip is_active" always happens
    in one transaction, never as two separate round trips from here.
    """
    _table = "persona_prompt"
    _model_class = PersonaPrompt

    def get_active(self, name: str = "nova") -> PersonaPrompt | None:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("name", name)
            .eq("is_active", True)
            .maybe_single()
            .execute()
        )
        if response is None or response.data is None:
            return None
        return self._to_model(self._model_class, response.data)

    def get_by_version(self, version: int, name: str = "nova") -> PersonaPrompt | None:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("name", name)
            .eq("version", version)
            .maybe_single()
            .execute()
        )
        if response is None or response.data is None:
            return None
        return self._to_model(self._model_class, response.data)

    def get(self, id: int) -> PersonaPrompt | None:
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

    def list_versions(self, name: str = "nova") -> list[PersonaPrompt]:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("name", name)
            .order("version", desc=True)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data or []]

    def create_version(
        self,
        content: str,
        name: str = "nova",
        created_by: str | None = None,
        notes: str | None = None,
    ) -> PersonaPrompt:
        response = self.client.rpc(
            "create_persona_version",
            {
                "p_name": name,
                "p_content": content,
                "p_created_by": created_by,
                "p_notes": notes,
            },
        ).execute()
        row = self._single_row(response.data)
        return self._to_model(self._model_class, row)

    def activate_version(self, id: int) -> PersonaPrompt | None:
        response = self.client.rpc("activate_persona_version", {"p_id": id}).execute()
        row = self._single_row(response.data)
        if row is None:
            return None
        return self._to_model(self._model_class, row)

    @staticmethod
    def _single_row(data: Any) -> dict | None:
        """
        PostgREST answers a `returns <row type>` function with either a bare
        object or a one-element list depending on client/library version;
        normalize to the dict either way.
        """
        if isinstance(data, list):
            return data[0] if data else None
        return data
