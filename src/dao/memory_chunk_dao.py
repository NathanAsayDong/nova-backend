from src.dao.base_dao import BaseDao
from src.model.memory_chunk import MemoryChunk, MemoryMatch


class MemoryChunkDao(BaseDao):
    """
    DAO for MemoryChunk model.
    """
    _table = "memory_chunk"
    _model_class = MemoryChunk

    def __init__(self):
        super().__init__()

    def match_memory_chunks(
        self,
        embedding: list[float],
        project_id: int | None = None,
        limit: int = 5,
    ) -> list[MemoryMatch]:
        """
        Nearest-neighbor search over memory chunks via the match_memory_chunks
        Postgres function (PostgREST cannot order by pgvector distance itself),
        keeping each row's cosine similarity.

        When project_id is given, matches chunks for that project plus general
        (project-less) chunks; when None, searches all memory.
        """
        response = self.client.rpc(
            "match_memory_chunks",
            {
                "query_embedding": embedding,
                "match_count": limit,
                "filter_project_id": project_id,
            },
        ).execute()

        matches: list[MemoryMatch] = []
        for row in response.data or []:
            matches.append(
                MemoryMatch(
                    chunk=MemoryChunk(
                        id=row.get("id"),
                        content=row.get("content"),
                        project_id=row.get("project_id"),
                    ),
                    similarity=float(row.get("similarity") or 0.0),
                )
            )
        return matches

    def get_memory_chunks(
        self,
        embedding: list[float],
        project_id: int | None = None,
        limit: int = 5,
    ) -> list[MemoryChunk]:
        """Same search, for callers that only want the rows."""
        return [
            match.chunk
            for match in self.match_memory_chunks(
                embedding, project_id=project_id, limit=limit
            )
        ]

    def insert_memory_chunks(self, memory_chunks: list[MemoryChunk]) -> None:
        if not memory_chunks:
            return
        payloads = [chunk.to_payload() for chunk in memory_chunks]
        self.client.table(self._table).insert(payloads).execute()

    def count_for_project(self, project_id: int) -> int:
        response = (
            self.client.table(self._table)
            .select("id")
            .eq("project_id", project_id)
            .execute()
        )
        return len(response.data or [])

    def delete_for_project(self, project_id: int) -> None:
        """
        Delete a project's memory chunks directly.

        Deleting the project itself already cascades to these rows; this is for
        clearing a project's memory without deleting the project.
        """
        self.client.table(self._table).delete().eq("project_id", project_id).execute()
