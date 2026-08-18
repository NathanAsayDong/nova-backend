from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field
from datetime import datetime

from src.model.report_type import ReportType

# Report types are no longer specific to responsibilities — a background agent
# can be given one too, and both paths converge on the Update that carries it.
# Kept as an alias so existing call sites and stored values keep working.
ResponsibilityReportType = ReportType

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
    report_type: ReportType | None = None

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
        """
        How this responsibility's outcome reaches the user.

        Delivery is handled system-side once the run produces an Update, so
        this is context for the agent's own writing — it should know whether
        its summary will be read on a screen or spoken down a phone line — and
        never an instruction to deliver anything itself.
        """
        if self.report_type == ReportType.EMAIL:
            return (
                "Your summary of this run will be emailed to the user verbatim, "
                "so write it as the body of that email."
            )
        elif self.report_type == ReportType.CALL:
            return (
                "Nova will phone the user and report this run out loud, using "
                "your summary as the basis for the conversation. Write it to be "
                "spoken: lead with the outcome, keep it short, and leave out "
                "code, file paths, and anything unreadable aloud."
            )
        elif self.report_type == ReportType.SMS:
            return "Your summary of this run will be texted to the user, so keep it very short."
        elif self.report_type == ReportType.CHAT:
            return "Your summary of this run will be shown to the user in chat."
        return ""