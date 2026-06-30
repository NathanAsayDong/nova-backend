from sqlmodel import SQLModel, Field

class Tool(SQLModel, table=True):
    __tablename__ = "tool"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    name: str | None = None
    description: str | None = None
    config: dict | None = None