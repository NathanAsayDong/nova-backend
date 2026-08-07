from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from src.model.conversation import Conversation
from enum import StrEnum
from uuid import UUID, uuid4

class MessageRole(StrEnum):
    USER = "user"
    NOVA = "nova"
    TOOL = "tool"

class Message(SQLModel, table=True):
    __tablename__ = "message"
    __table_args__ = {"extend_existing": True}

    #primary key is composite of id and conversation_id
    id: int = Field(default=None, primary_key=True)
    conversation_uuid: UUID = Field(foreign_key="conversation.uuid", primary_key=True)
    content: str | None = None
    role: MessageRole = Field(default=MessageRole.USER)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    conversation: Conversation = Relationship(back_populates="messages")

    def to_payload(self) -> dict:
        return self.model_dump(
            exclude_none=True,
            mode="json",
        )