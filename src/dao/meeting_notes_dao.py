from src.dao.base_dao import BaseDao
from src.model.meeting import MeetingNotes


class MeetingNotesDao(BaseDao):
    """
    DAO for generated meeting notes.

    Notes are append-only per meeting: regenerating writes a new row rather
    than overwriting, so asking for a different cut of the same meeting can
    never destroy the first one.
    """

    _table = "meeting_notes"
    _model_class = MeetingNotes

    def create(self, entity: MeetingNotes) -> MeetingNotes:
        response = self.client.table(self._table).insert(entity.to_payload()).execute()
        return self._to_model(self._model_class, response.data[0])

    def get_latest(self, meeting_id: int) -> MeetingNotes | None:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("meeting_id", int(meeting_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return None
        return self._to_model(self._model_class, rows[0])

    def get_for_meeting(self, meeting_id: int) -> list[MeetingNotes]:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("meeting_id", int(meeting_id))
            .order("created_at", desc=True)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data or []]
