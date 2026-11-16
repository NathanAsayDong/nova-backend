from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field
from datetime import datetime

from src.model.report_type import ReportType, normalize_report_types

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
    # Bare value or JSON-encoded list — see Update.channels and
    # src.model.report_type.normalize_report_types/encode_report_types.
    report_type: str | None = None

    @property
    def channels(self) -> list[ReportType]:
        return normalize_report_types(self.report_type)

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
        its summary will be read on a screen, spoken down a phone line, or
        both — and never an instruction to deliver anything itself. One
        responsibility can carry several channels at once (e.g. ["chat",
        "speak"]), in which case every applicable sentence below is included.
        """
        sentences: list[str] = []
        for channel in self.channels:
            if channel == ReportType.EMAIL:
                sentences.append(
                    "Your summary of this run will be emailed to the user "
                    "verbatim, so write it as the body of that email."
                )
            elif channel == ReportType.CALL:
                sentences.append(
                    "Nova will phone the user and report this run out loud, "
                    "using your summary as the basis for the conversation. "
                    "Write it to be spoken: lead with the outcome, keep it "
                    "short, and leave out code, file paths, and anything "
                    "unreadable aloud."
                )
            elif channel == ReportType.SMS:
                sentences.append(
                    "Your summary of this run will be texted to the user, so "
                    "keep it very short."
                )
            elif channel == ReportType.SPEAK:
                sentences.append(
                    "If Sidekick mode is on and the user is free, Nova will "
                    "also speak your summary out loud right away, so keep it "
                    "short and spoken-friendly: no code, file paths, or URLs."
                )
            elif channel == ReportType.CHAT:
                sentences.append(
                    "Your summary of this run will be shown to the user in chat."
                )
        return " ".join(sentences)