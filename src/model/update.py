from datetime import datetime, timezone
from sqlmodel import SQLModel, Field


class Update(SQLModel, table=True):
    __tablename__ = "update"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    update_message: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_viewed: bool = Field(default=False)
    project_id: int | None = Field(default=None, foreign_key="project.id")
    conversation_id: int | None = Field(default=None, foreign_key="conversation.id")

    def to_payload(self) -> dict:
        return self.model_dump(
            exclude={"id"},
            exclude_none=True,
            mode="json",
        )
