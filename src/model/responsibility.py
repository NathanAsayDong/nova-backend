from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field
from datetime import datetime
from enum import StrEnum

class ResponsibilityReportType(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    CALL = "call"
    CHAT = "chat"

class Responsibility(SQLModel, table=True):
    __tablename__ = "responsibility"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    name: str | None = None
    description: str | None = None
    schedule: list[str] | None = Field(
        default_factory=lambda: ["morning", "afternoon", "evening", "night"],
        sa_column=Column(JSON),
    )
    last_run: datetime | None = None
    project_id: int | None = None
    report_type: ResponsibilityReportType | None = None

    def to_payload(self) -> dict:
        return self.model_dump(
            exclude={"id"},
            exclude_none=True,
            mode="json",
        )

    def to_prompt(self) -> str:
        base = f"""
        Agent, this responsibility is: {self.name}. Your job is to complete the responsibility.
        {self.description}
        """
        if self.project_id:
            base += f"Project: {self.project_id}"
        return base

    def report_type_prompt(self) -> str:
        if self.report_type == ResponsibilityReportType.EMAIL:
            return f"Report the result of the responsibility to the user by email."
        elif self.report_type == ResponsibilityReportType.SMS:
            return f"Report the result of the responsibility to the user by SMS."
        elif self.report_type == ResponsibilityReportType.CALL:
            return f"Report the result of the responsibility to the user by call."
        elif self.report_type == ResponsibilityReportType.CHAT:
            return f"Report the result of the responsibility to the user by chat."
        return ""