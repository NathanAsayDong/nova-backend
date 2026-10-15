from datetime import datetime

from sqlmodel import SQLModel


class Person(SQLModel):
    """
    Someone Nathan enrolled for face recognition, with their agreement.

    A row of the `person` table. Their face samples live in `face_sample`
    (embeddings only, never photos) and cascade away with them.
    """

    id: int | None = None
    name: str | None = None
    consent_note: str | None = None
    consented_at: datetime | None = None
    created_at: datetime | None = None
    # Not a column: how many face samples the person has, filled in by reads.
    samples: int = 0

    def to_payload(self) -> dict:
        return self.model_dump(
            exclude={"id", "created_at", "consented_at", "samples"},
            exclude_none=True,
            mode="json",
        )
