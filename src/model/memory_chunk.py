from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from src.model.project import Project


class MemoryChunk(SQLModel, table=True):
    __tablename__ = "memory_chunk"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    content: str | None = None
    embedding: list[float] | None = Field(default=None, sa_column=Column(Vector(1536)))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Nullable: chunks from conversations without a project are general memory.
    project_id: int | None = Field(default=None, foreign_key="project.id")
    project: Project = Relationship(back_populates="memory_chunks")

    def to_payload(self) -> dict:
        return self.model_dump(
            exclude={"id"},
            exclude_none=True,
            mode="json",
        )


@dataclass(frozen=True)
class MemoryMatch:
    """
    A memory chunk together with how well it matched the query.

    The similarity is a property of one lookup rather than of the row, so it
    lives here instead of on MemoryChunk. Callers that inject memory into a
    prompt unasked need it: a nearest-neighbour search always returns its k
    nearest rows, and without a score there is no way to tell "the user's
    deploy preferences" from "the nearest thing we had, which was nothing
    like the question".
    """

    chunk: MemoryChunk
    similarity: float
