from time import timezone
from sqlmodel import SQLModel, Field
from datetime import datetime

class MemoryChunk(SQLModel, table=True):
    __tablename__ = "memory_chunk"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    content: str | None = None
    embedding: list[float] | None = None
    created_at: datetime = Field(default=datetime.now(timezone.utc))
    project_id: int = Field(foreign_key="project.id")