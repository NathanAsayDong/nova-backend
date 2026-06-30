from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field

class Tool(SQLModel, table=True):
    __tablename__ = "tool"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    name: str | None = None
    description: str | None = None
    config: dict | None = Field(default=None, sa_column=Column(JSON))

    def to_payload(self) -> dict:
        return self.model_dump(
            exclude={"id"},
            exclude_none=True,
            mode="json",
        )