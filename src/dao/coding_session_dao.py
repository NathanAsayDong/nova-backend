"""
DAO for coding sessions and their event tail.

Events live here rather than in their own DAO for the same reason meeting
segments do: nothing reads them without a session in hand.
"""

from datetime import datetime, timezone
from uuid import UUID

from src.dao.base_dao import BaseDao
from src.model.coding_session import CodingEvent, CodingSession


class CodingSessionDao(BaseDao):
    _table = "coding_session"
    _event_table = "coding_event"
    _model_class = CodingSession

    # How much of the tail to keep. Enough to describe what a session has been
    # doing; far short of an archive, because the archive is the .jsonl on the
    # Mac and this table would otherwise grow without bound.
    _EVENT_RETENTION = 300

    def create(self, session: CodingSession) -> CodingSession:
        payload = session.model_dump(exclude={"id"}, mode="json")
        response = self.client.table(self._table).insert(payload).execute()
        return self._to_model(self._model_class, response.data[0])

    def get(self, session_id: UUID) -> CodingSession | None:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("session_id", str(session_id))
            .maybe_single()
            .execute()
        )
        if response is None or response.data is None:
            return None
        return self._to_model(self._model_class, response.data)

    # Not named `list`: a method by that name shadows the builtin for the
    # rest of the class body, and every later `list[...]` annotation then
    # tries to subscript a function.
    def list_recent(
        self, limit: int = 20, project_id: int | None = None
    ) -> list[CodingSession]:
        query = self.client.table(self._table).select("*")
        if project_id is not None:
            query = query.eq("project_id", project_id)
        response = query.order("created_at", desc=True).limit(limit).execute()
        return [self._to_model(self._model_class, row) for row in (response.data or [])]

    def list_open(self) -> list[CodingSession]:
        response = (
            self.client.table(self._table)
            .select("*")
            .not_.in_("status", ["closed"])
            .order("created_at", desc=True)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in (response.data or [])]

    def update(self, session_id: UUID, **fields) -> CodingSession | None:
        fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        response = (
            self.client.table(self._table)
            .update(fields)
            .eq("session_id", str(session_id))
            .execute()
        )
        rows = response.data or []
        return self._to_model(self._model_class, rows[0]) if rows else None

    # ---------- events ----------

    def append_event(self, event: CodingEvent) -> None:
        payload = event.model_dump(exclude={"id"}, mode="json")
        # Duplicate seqs are expected, not exceptional: a replay after a
        # reconnect re-sends events the tower may already have. The unique
        # index makes the second write a no-op instead of a double entry.
        try:
            self.client.table(self._event_table).upsert(
                payload, on_conflict="session_id,seq"
            ).execute()
        except Exception as exc:
            print(f"Could not persist coding event {event.seq}: {exc}")

    def events(
        self, session_id: UUID, after_seq: int = 0, limit: int = 200
    ) -> list[CodingEvent]:
        response = (
            self.client.table(self._event_table)
            .select("*")
            .eq("session_id", str(session_id))
            .gt("seq", after_seq)
            .order("seq")
            .limit(limit)
            .execute()
        )
        return [self._to_model(CodingEvent, row) for row in (response.data or [])]

    def prune_events(self, session_id: UUID) -> None:
        """Drop everything older than the retention tail."""
        response = (
            self.client.table(self._event_table)
            .select("seq")
            .eq("session_id", str(session_id))
            .order("seq", desc=True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return
        cutoff = int(rows[0]["seq"]) - self._EVENT_RETENTION
        if cutoff <= 0:
            return
        self.client.table(self._event_table).delete().eq(
            "session_id", str(session_id)
        ).lte("seq", cutoff).execute()
