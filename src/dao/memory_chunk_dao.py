from src.dao.base_dao import BaseDao
from src.model.memory_chunk import MemoryChunk


class MemoryChunkDao(BaseDao):
    """
    DAO for MemoryChunk model.
    """
    def __init__(self):
        super().__init__()