from src.dao.base_dao import BaseDao
from src.model.memory_chunk import MemoryChunk


class MemoryChunkDao(BaseDao):
    """
    DAO for MemoryChunk model.
    """
    def __init__(self):
        super().__init__()

    def get_memory_chunks(self, embedding: list[float], project_id: int | None = None) -> list[MemoryChunk]:
        pass

    def insert_memory_chunks(self, memory_chunks: list[MemoryChunk]) -> None:
        pass