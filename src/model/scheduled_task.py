from datetime import datetime
from enum import StrEnum

from sqlmodel import SQLModel, Field

from src.model.report_type import ReportType


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduledTask(SQLModel, table=True):
    """
    Work that runs once, at `run_at`, rather than on a repeating schedule.
    """

    __tablename__ = "scheduled_task"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    name: str | None = None
    description: str | None = None
    run_at: datetime | None = None
    status: TaskStatus | None = TaskStatus.PENDING
    project_id: int | None = None
    report_type: ReportType | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: str | None = None

    def to_payload(self) -> dict:
        return self.model_dump(
            exclude={"id", "created_at", "started_at", "completed_at", "result"},
            exclude_none=True,
            mode="json",
        )

    def to_prompt(self) -> str:
        base = f"""
        Agent, this is a one-time task: {self.name}. Your job is to complete it.
        It was scheduled earlier and you are running it now, with nobody present.
        {self.description}
        """
        if self.project_id:
            base += f"Project: {self.project_id}"
        return base
