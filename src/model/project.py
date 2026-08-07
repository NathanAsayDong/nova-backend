from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

from src.model.memory_chunk import MemoryChunk

if TYPE_CHECKING:
    from src.model.conversation import Conversation


class Project(SQLModel, table=True):
    __tablename__ = "project"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    name: str | None = None
    description: str | None = None

    memory_chunks: list[MemoryChunk] = Relationship(back_populates="project")
    conversations: list["Conversation"] = Relationship(back_populates="project")

    def to_payload(self) -> dict:
        return self.model_dump(
            exclude={"id", "memory_chunks"},
            exclude_none=True,
            mode="json",
        )