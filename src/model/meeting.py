"""
Meeting mode's tables.

A meeting is a recording session Nova transcribes without answering: the
agent loop never runs, nothing is spoken back, and the only output is text.
Its status column doubles as Nova's mode — exactly one meeting may be
'recording' at a time, and while one is, Nova is in meeting mode.

The transcript is stored in three shapes because three things read it:
segments are what the client renders live, chunks are what search embeds,
and notes are what a person actually reads afterwards.
"""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

# Imported at module level, not under TYPE_CHECKING: SQLAlchemy resolves a
# relationship annotation of "Project | None" by name and cannot parse a
# union out of a string. conversation.py imports Project the same way.
from src.model.project import Project


class MeetingStatus(StrEnum):
    """
    Lifecycle of one meeting.

    RECORDING is the mode flag: while a meeting is in it, Nova is in meeting
    mode. PROCESSING covers the gap between the user stopping and the notes
    being ready, which is seconds to a couple of minutes and needs to be
    visible rather than looking like a hang.
    """

    RECORDING = "recording"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class Meeting(SQLModel, table=True):
    __tablename__ = "meeting"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    uuid: UUID = Field(default_factory=uuid4, unique=True, index=True)
    title: str | None = Field(default=None)
    status: MeetingStatus = Field(default=MeetingStatus.RECORDING)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = Field(default=None)
    # Nullable: a meeting can belong to no project, the same way a
    # conversation can. Set from the calling conversation's project when a
    # meeting is started by voice.
    project_id: int | None = Field(default=None, foreign_key="project.id")
    # Where the captured audio landed on disk. Cleared when the audio is
    # deleted after processing, so a null here means "transcript only".
    audio_path: str | None = Field(default=None)

    project: Project | None = Relationship(back_populates="meetings")

    def to_payload(self) -> dict:
        return self.model_dump(exclude={"id"}, exclude_none=True, mode="json")


class MeetingSegment(SQLModel, table=True):
    """One committed window of transcript, timed from the start of the recording."""

    __tablename__ = "meeting_segment"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    meeting_id: int = Field(foreign_key="meeting.id")
    start_ms: int = Field(default=0)
    end_ms: int = Field(default=0)
    text: str = Field(default="")

    def to_payload(self) -> dict:
        return self.model_dump(exclude={"id"}, exclude_none=True, mode="json")


class MeetingChunk(SQLModel, table=True):
    """
    A retrieval passage: several segments rolled together and embedded.

    Segments are single utterances and retrieve badly on their own — "yeah,
    agreed" carries no searchable meaning. Chunks are the unit that does.
    """

    __tablename__ = "meeting_chunk"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    meeting_id: int = Field(foreign_key="meeting.id")
    content: str = Field(default="")
    embedding: list[float] | None = Field(default=None, sa_column=Column(Vector(1536)))
    start_ms: int = Field(default=0)
    end_ms: int = Field(default=0)

    def to_payload(self) -> dict:
        return self.model_dump(exclude={"id"}, exclude_none=True, mode="json")


class MeetingNotes(SQLModel, table=True):
    """
    What a person reads instead of the transcript.

    Regenerating is additive — a new row, same meeting — so asking for a
    different cut of the same meeting never destroys the first one.
    """

    __tablename__ = "meeting_notes"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    meeting_id: int = Field(foreign_key="meeting.id")
    summary_md: str = Field(default="")
    # Plain strings: 'we're going with the 15-minute reporting interval'.
    decisions: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    # Objects: {task, owner, due}. owner/due are often null — a meeting
    # rarely assigns both, and inventing them is worse than leaving them out.
    action_items: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    model: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_payload(self) -> dict:
        return self.model_dump(exclude={"id"}, exclude_none=True, mode="json")
