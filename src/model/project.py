from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

from src.model.memory_chunk import MemoryChunk

if TYPE_CHECKING:
    from src.model.conversation import Conversation
    from src.model.meeting import Meeting


class Project(SQLModel, table=True):
    __tablename__ = "project"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    name: str | None = None
    description: str | None = None

    memory_chunks: list[MemoryChunk] = Relationship(back_populates="project")
    conversations: list["Conversation"] = Relationship(back_populates="project")
    meetings: list["Meeting"] = Relationship(back_populates="project")

    def to_payload(self) -> dict:
        return self.model_dump(
            exclude={"id", "memory_chunks"},
            exclude_none=True,
            mode="json",
        )


# Registers Meeting with the SQLModel class registry so the "meetings"
# relationship above can resolve by name. Without it, any code path that
# reaches Project without having imported Meeting first fails at mapper
# configuration with "expression 'Meeting' failed to locate a name".
#
# A plain module import, not `from ... import Meeting`: meeting.py imports
# Project from here, so a from-import would deadlock whenever meeting.py
# happens to be the module imported first.
import src.model.meeting  # noqa: E402,F401  (imported for its side effect)
