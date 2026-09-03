"""
A coding session: one Claude Code thread running on Nate's Mac.

Deliberately thin. The transcript, the file edits, and the git history all
live on the Mac — this row is the tower's handle on them: which project the
work belongs to, what it was asked to do, and enough of a summary that Nova
can answer a spoken question about it without waking the laptop.
"""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from src.model.project import Project  # noqa: F401  (see meeting.py on why)


class CodingStatus(StrEnum):
    """
    Where a session is, from the tower's point of view.

    STARTING covers the gap between Nova asking and the Mac confirming — a
    worktree checkout plus a CLI boot, which is seconds but is visible.
    QUEUED is its unhappy twin: the Mac is asleep or offline, and the request
    is waiting for it rather than having failed.
    """

    STARTING = "starting"
    QUEUED = "queued"
    WORKING = "working"
    IDLE = "idle"
    ERROR = "error"
    CLOSED = "closed"


# Statuses where nothing more will happen without someone asking for it.
TERMINAL_STATUSES = {CodingStatus.CLOSED}


class CodingSession(SQLModel, table=True):
    __tablename__ = "coding_session"

    id: int | None = Field(default=None, primary_key=True)
    session_id: UUID = Field(default_factory=uuid4, index=True)
    title: str
    status: str = Field(default=CodingStatus.STARTING)
    repo: str
    branch: str | None = None
    cwd: str | None = None
    instructions: str
    rollup: str | None = None
    last_result: str | None = None
    last_seq: int = 0
    project_id: int | None = Field(default=None, foreign_key="project.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: datetime | None = None


class CodingEvent(SQLModel, table=True):
    __tablename__ = "coding_event"

    id: int | None = Field(default=None, primary_key=True)
    session_id: UUID
    seq: int
    type: str
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
