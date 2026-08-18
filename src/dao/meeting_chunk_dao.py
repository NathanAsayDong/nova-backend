from datetime import datetime

from src.dao.base_dao import BaseDao
from src.model.meeting import MeetingChunk


class MeetingChunkDao(BaseDao):
    """
    DAO for the embedded retrieval passages of a meeting.

    Mirrors MemoryChunkDao: PostgREST cannot order by pgvector distance, so
    the search goes through a Postgres function.
    """

    _table = "meeting_chunk"
    _model_class = MeetingChunk

    def insert_chunks(self, chunks: list[MeetingChunk]) -> None:
        if not chunks:
            return
        payloads = [chunk.to_payload() for chunk in chunks]
        self.client.table(self._table).insert(payloads).execute()

    def search(
        self,
        embedding: list[float],
        project_id: int | None = None,
        meeting_id: int | None = None,
        since: datetime | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """
        Nearest-neighbour passages via the match_meeting_chunks function.

        Returns raw rows rather than models: every caller wants the meeting
        title, date, and similarity that the function joins in, none of which
        belong on the MeetingChunk row itself.
        """
        response = self.client.rpc(
            "match_meeting_chunks",
            {
                "query_embedding": embedding,
                "match_count": limit,
                "filter_project": project_id,
                "filter_meeting": meeting_id,
                "since": since.isoformat() if since is not None else None,
            },
        ).execute()
        return list(response.data or [])

    def delete_for_meeting(self, meeting_id: int) -> None:
        """Clear a meeting's passages so it can be re-chunked from scratch."""
        self.client.table(self._table).delete().eq(
            "meeting_id", int(meeting_id)
        ).execute()
