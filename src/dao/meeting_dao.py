from datetime import datetime, timezone
from uuid import UUID

from src.dao.base_dao import BaseDao
from src.model.meeting import Meeting, MeetingSegment, MeetingStatus


class MeetingDao(BaseDao):
    """
    DAO for Meeting and its transcript segments.

    Segments live here rather than in their own DAO because nothing ever reads
    them without a meeting in hand — they are the meeting's body, not an
    entity in their own right.
    """

    _table = "meeting"
    _segment_table = "meeting_segment"
    _model_class = Meeting

    def get(self, id: int) -> Meeting | None:
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

    def get_by_uuid(self, uuid: UUID) -> Meeting | None:
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

    def get_active(self) -> Meeting | None:
        """
        The meeting currently recording, if any.

        This is the whole of Nova's mode state: a row here means meeting mode.
        A unique partial index guarantees there is at most one, so reading the
        first row is not a race waiting to happen.
        """
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("status", str(MeetingStatus.RECORDING))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return None
        return self._to_model(self._model_class, rows[0])

    def get_all(
        self,
        project_id: int | None = None,
        limit: int = 20,
        since: datetime | None = None,
    ) -> list[Meeting]:
        query = self.client.table(self._table).select("*")
        if project_id is not None:
            query = query.eq("project_id", int(project_id))
        if since is not None:
            query = query.gte("started_at", since.isoformat())
        response = query.order("started_at", desc=True).limit(limit).execute()
        return [self._to_model(self._model_class, row) for row in response.data or []]

    def create(self, entity: Meeting) -> Meeting:
        response = self.client.table(self._table).insert(entity.to_payload()).execute()
        return self._to_model(self._model_class, response.data[0])

    def set_status(
        self,
        id: int,
        status: MeetingStatus,
        ended_at: datetime | None = None,
    ) -> Meeting | None:
        payload: dict = {"status": str(status)}
        if ended_at is not None:
            payload["ended_at"] = ended_at.isoformat()
        response = (
            self.client.table(self._table).update(payload).eq("id", int(id)).execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])

    def set_audio_path(self, id: int, audio_path: str | None) -> None:
        self.client.table(self._table).update({"audio_path": audio_path}).eq(
            "id", int(id)
        ).execute()

    def set_title(self, id: int, title: str) -> None:
        self.client.table(self._table).update({"title": title}).eq("id", int(id)).execute()

    def update(self, id: int, changes: dict) -> Meeting | None:
        """Partial update. Callers pass only the columns they mean to change."""
        if not changes:
            return self.get(id)
        response = (
            self.client.table(self._table).update(changes).eq("id", int(id)).execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])

    def close_stale_recordings(self) -> list[Meeting]:
        """
        Fail any meeting left recording by a crash.

        The unique active-meeting index means one abandoned row blocks every
        future meeting, so startup calls this rather than making the user go
        find it in the database.
        """
        response = (
            self.client.table(self._table)
            .update(
                {
                    "status": str(MeetingStatus.FAILED),
                    "ended_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("status", str(MeetingStatus.RECORDING))
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data or []]

    def delete(self, id: int) -> None:
        self.client.table(self._table).delete().eq("id", int(id)).execute()

    # ---------- segments ----------

    def insert_segments(self, segments: list[MeetingSegment]) -> None:
        """
        Write a batch of committed transcript.

        Batched deliberately: an hour of meeting is a few hundred segments and
        a round trip each would make the commit pass slower than the ASR it is
        writing the results of.
        """
        if not segments:
            return
        payloads = [segment.to_payload() for segment in segments]
        self.client.table(self._segment_table).insert(payloads).execute()

    def get_segments(
        self,
        meeting_id: int,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> list[MeetingSegment]:
        query = (
            self.client.table(self._segment_table)
            .select("*")
            .eq("meeting_id", int(meeting_id))
        )
        if start_ms is not None:
            query = query.gte("end_ms", int(start_ms))
        if end_ms is not None:
            query = query.lte("start_ms", int(end_ms))
        response = query.order("start_ms", desc=False).execute()
        return [
            self._to_model(MeetingSegment, row) for row in response.data or []
        ]

    def get_last_segment_end_ms(self, meeting_id: int) -> int:
        """Where committed transcript currently ends, in recording time."""
        response = (
            self.client.table(self._segment_table)
            .select("end_ms")
            .eq("meeting_id", int(meeting_id))
            .order("end_ms", desc=True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return int(rows[0]["end_ms"]) if rows else 0
