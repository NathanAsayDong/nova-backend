from datetime import datetime

from sqlmodel import SQLModel, Field


class PersonaPrompt(SQLModel, table=True):
    """
    One version of Nova's persona prompt.

    Versioned rather than mutated in place: an update inserts a new row and
    flips is_active, so every past persona is still here under its own
    version number. Only one row per `name` is active at a time, enforced by
    a partial unique index in the migration rather than here.
    """
    __tablename__ = "persona_prompt"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    name: str = "nova"
    content: str
    version: int
    is_active: bool = False
    created_at: datetime | None = None
    created_by: str | None = None
    notes: str | None = None

    def to_payload(self) -> dict:
        return self.model_dump(
            exclude={"id"},
            exclude_none=True,
            mode="json",
        )
