from src.dao.memory_chunk_dao import MemoryChunkDao
from src.model.memory_chunk import MemoryChunk
from src.service.conversation_service import ConversationService

class MemoryChunkService:
    def __init__(self):
        self.memory_chunk_dao = MemoryChunkDao()
        self.conversation_service = ConversationService()

    def process_conversations(self) -> None:
        """
        Fetchs all converesations that are closed. 
        Loads messages and processes them into memory chunks. 
        If conversation has project_id, the fk will be attached to the memory chunk.
        """
        pass

    def fetch_memory(self, prompt: str, project_id: int | None = None) -> str:
        """
        Uses vector embedding to do nearest neighbor search on the memory chunks.
        """
        pass