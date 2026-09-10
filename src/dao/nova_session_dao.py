"""
DAO for login sessions.

Lookups are always by token hash: the browser presents a token, the service
hashes it, and this is the only thing the table is ever asked. Everything else
here exists for sign-out and the devices list.
"""

from datetime import datetime, timezone

from src.dao.base_dao import BaseDao
from src.model.nova_session import NovaSession

_DATETIME_FIELDS = ("created_at", "expires_at", "last_seen_at", "revoked_at")


def row_to_session(row: dict) -> NovaSession:
    """
    Build a NovaSession from a Supabase row, with real datetimes.

    SQLModel does not validate `table=True` models, so a row read back keeps
    exactly what the JSON gave it: ISO strings where the annotation says
    datetime. Every comparison in the auth service (is it expired? how long
    since it was seen?) needs the real thing, so they are parsed here, once,
    at the boundary. Same lesson as coding_session_dao.
    """
    data = dict(row)
    for field in _DATETIME_FIELDS:
        value = data.get(field)
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            data[field] = parsed
    return NovaSession(**data)


class NovaSessionDao(BaseDao):
    _table = "nova_sessions"
    _model_class = NovaSession

    def _to_model(self, model_class, row):  # type: ignore[override]
        return row_to_session(row)

    def create(self, session: NovaSession) -> NovaSession:
        payload = session.model_dump(mode="json")
        response = self.client.table(self._table).insert(payload).execute()
        return self._to_model(self._model_class, response.data[0])

    def get_by_token_hash(self, token_hash: str) -> NovaSession | None:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("token_hash", token_hash)
            .maybe_single()
            .execute()
        )
        if response is None or response.data is None:
            return None
        return self._to_model(self._model_class, response.data)

    def list_active(self) -> list[NovaSession]:
        now = datetime.now(timezone.utc).isoformat()
        response = (
            self.client.table(self._table)
            .select("*")
            .is_("revoked_at", "null")
            .gt("expires_at", now)
            .order("last_seen_at", desc=True)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in (response.data or [])]

    def touch(self, token_hash: str, last_seen_at: datetime, expires_at: datetime) -> None:
        """Record use and slide the expiry."""
        (
            self.client.table(self._table)
            .update(
                {
                    "last_seen_at": last_seen_at.isoformat(),
                    "expires_at": expires_at.isoformat(),
                }
            )
            .eq("token_hash", token_hash)
            .execute()
        )

    def revoke(self, token_hash: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        (
            self.client.table(self._table)
            .update({"revoked_at": now})
            .eq("token_hash", token_hash)
            .is_("revoked_at", "null")
            .execute()
        )

    def revoke_all(self) -> int:
        """Revoke every live session. Returns how many were."""
        now = datetime.now(timezone.utc).isoformat()
        response = (
            self.client.table(self._table)
            .update({"revoked_at": now})
            .is_("revoked_at", "null")
            .execute()
        )
        return len(response.data or [])

    def purge_expired(self) -> int:
        """Delete rows long past use. Returns how many were removed."""
        now = datetime.now(timezone.utc).isoformat()
        response = (
            self.client.table(self._table)
            .delete()
            .lt("expires_at", now)
            .execute()
        )
        return len(response.data or [])
