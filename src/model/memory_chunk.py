from __future__ import annotations

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
    project_id: int = Field(foreign_key="project.id")
    project: Project = Relationship(back_populates="memory_chunks")
