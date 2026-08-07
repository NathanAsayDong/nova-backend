from datetime import datetime
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4
from src.model.project import Project

if TYPE_CHECKING:
    from src.model.message import Message


class Conversation(SQLModel, table=True):
    __tablename__ = "conversation"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    uuid: UUID = Field(default_factory=uuid4, unique=True, index=True)

    project_id: int | None = Field(default=None, foreign_key="project.id")
    last_message_timestamp_utc: datetime | None = Field(default=None)
    is_closed: bool = Field(default=False)
    is_processed: bool = Field(default=False)

    project: Project | None = Relationship(back_populates="conversations")
    messages: list["Message"] = Relationship(back_populates="conversation")

    def to_payload(self) -> dict:
        return self.model_dump(
            exclude={"id", "project_id", "created_at", "updated_at"},
            exclude_none=True,
            mode="json",
        )
