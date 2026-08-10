import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.dao.project_dao import ProjectDao
from src.dao.responsibility_dao import ResponsibilityDao
from src.model.responsibility import Responsibility, ResponsibilityReportType

# Time-of-day windows a responsibility can be scheduled into. A responsibility
# runs at most once per window, so ["morning", "evening"] means twice a day.
# Night wraps midnight and is handled explicitly below.
WINDOW_MORNING = "morning"
WINDOW_AFTERNOON = "afternoon"
WINDOW_EVENING = "evening"
WINDOW_NIGHT = "night"

_WINDOW_BOUNDS = {
    WINDOW_MORNING: (6, 12),
    WINDOW_AFTERNOON: (12, 17),
    WINDOW_EVENING: (17, 21),
    WINDOW_NIGHT: (21, 6),
}

# Report types Nova can actually deliver today. SMS, call, and chat have no
# tool behind them yet, so a responsibility asking for one still does its work
# and reports in its final reply instead of silently failing.
_SUPPORTED_REPORT_TYPES = {ResponsibilityReportType.EMAIL}


class ResponsibilityService:
    def __init__(self) -> None:
        self.responsibility_dao = ResponsibilityDao()
        self.project_dao = ProjectDao()

    # ---------- crud ----------

    @staticmethod
    def _to_dict(responsibility: Responsibility) -> dict:
        """JSON-serializable view, including whether the report type works yet."""
        report_type = responsibility.report_type
        return {
            "id": responsibility.id,
            "name": responsibility.name,
            "description": responsibility.description,
            "schedule": responsibility.schedule,
            "project_id": responsibility.project_id,
            "report_type": str(report_type) if report_type else None,
            "report_deliverable": report_type in _SUPPORTED_REPORT_TYPES
            if report_type
            else None,
            "last_run": (
                responsibility.last_run.isoformat()
                if hasattr(responsibility.last_run, "isoformat")
                else responsibility.last_run
            ),
        }

    @staticmethod
    def _validate_schedule(schedule: list[str] | None) -> list[str] | None:
        if schedule is None:
            return None
        if isinstance(schedule, str):
            schedule = [schedule]
        if not isinstance(schedule, list) or not schedule:
            raise ValueError(
                "schedule must be a non-empty list of time-of-day windows: "
                f"{sorted(_WINDOW_BOUNDS)}."
            )

        normalized: list[str] = []
        for window in schedule:
            candidate = str(window).strip().lower()
            if candidate not in _WINDOW_BOUNDS:
                raise ValueError(
                    f"Unknown schedule window '{window}'. Valid windows are "
                    f"{sorted(_WINDOW_BOUNDS)}."
                )
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    @staticmethod
    def _validate_report_type(report_type: str | None) -> ResponsibilityReportType | None:
        if report_type is None:
            return None
        candidate = str(report_type).strip().lower()
        if not candidate:
            return None
        try:
            return ResponsibilityReportType(candidate)
        except ValueError:
            raise ValueError(
                f"Unknown report_type '{report_type}'. Valid types are "
                f"{[str(t) for t in ResponsibilityReportType]}."
            )

    def _validate_project(self, project_id: int | None) -> int | None:
        if project_id is None:
            return None
        project = self.project_dao.get(int(project_id))
        if project is None:
            raise ValueError(f"Project {project_id} does not exist.")
        return project.id

    def get_all_responsibilities(self) -> list[dict]:
        return [self._to_dict(item) for item in self.responsibility_dao.get_all()]

    def get_responsibility(self, responsibility_id: int) -> dict:
        responsibility = self.responsibility_dao.get(int(responsibility_id))
        if responsibility is None:
            raise ValueError(f"Responsibility {responsibility_id} does not exist.")
        return self._to_dict(responsibility)

    def create_responsibility(
        self,
        name: str,
        description: str,
        schedule: list[str] | None = None,
        project_id: int | None = None,
        report_type: str | None = None,
    ) -> dict:
        """
        Create a scheduled responsibility.

        The description is the agent's entire brief when it runs later with no
        user present, so it has to stand alone.
        """
        name = (name or "").strip()
        if not name:
            raise ValueError("A responsibility name is required.")

        description = (description or "").strip()
        if not description:
            raise ValueError(
                "A description is required — it is the only instruction the "
                "agent gets when this runs unattended, so state the task fully."
            )

        validated_type = self._validate_report_type(report_type)
        created = self.responsibility_dao.create(
            Responsibility(
                name=name,
                description=description,
                schedule=self._validate_schedule(schedule),
                project_id=self._validate_project(project_id),
                report_type=validated_type,
            )
        )

        result = self._to_dict(created)
        if validated_type is not None and validated_type not in _SUPPORTED_REPORT_TYPES:
            result["warning"] = (
                f"Reporting by {validated_type} is not deliverable yet — no tool "
                "exists for it. The responsibility will still run and summarize "
                "its outcome in its reply. Only email can be delivered today."
            )
        return result

    def update_responsibility(
        self,
        responsibility_id: int,
        name: str | None = None,
        description: str | None = None,
        schedule: list[str] | None = None,
        project_id: int | None = None,
        report_type: str | None = None,
    ) -> dict:
        """Update a responsibility. Omitted fields are left unchanged."""
        responsibility = self.responsibility_dao.get(int(responsibility_id))
        if responsibility is None:
            raise ValueError(f"Responsibility {responsibility_id} does not exist.")

        if name is not None:
            name = name.strip()
            if not name:
                raise ValueError("A responsibility name cannot be blank.")
            responsibility.name = name

        if description is not None:
            description = description.strip()
            if not description:
                raise ValueError("A responsibility description cannot be blank.")
            responsibility.description = description

        if schedule is not None:
            responsibility.schedule = self._validate_schedule(schedule)

        if project_id is not None:
            responsibility.project_id = self._validate_project(project_id)

        if report_type is not None:
            responsibility.report_type = self._validate_report_type(report_type)

        updated = self.responsibility_dao.update(responsibility.id, responsibility)
        if updated is None:
            raise ValueError(f"Responsibility {responsibility_id} could not be updated.")
        return self._to_dict(updated)

    def delete_responsibility(self, responsibility_id: int) -> dict:
        """
        Delete a responsibility so it stops running on its schedule.

        Only the schedule entry goes away — anything it already did (files,
        emails, memory) is untouched, so this needs no confirmation dance.
        """
        responsibility = self.responsibility_dao.get(int(responsibility_id))
        if responsibility is None:
            raise ValueError(f"Responsibility {responsibility_id} does not exist.")

        self.responsibility_dao.delete(responsibility.id)
        return {"status": "deleted", "responsibility": self._to_dict(responsibility)}

    # ---------- scheduling ----------

    @staticmethod
    def current_window(now: datetime | None = None) -> tuple[str, datetime]:
        """
        The time-of-day window `now` falls in, plus when that window opened.

        The window start is what makes "run once per window" work: a
        responsibility is due only if it hasn't run since the window opened.
        """
        now = now or datetime.now().astimezone()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

        for name in (WINDOW_MORNING, WINDOW_AFTERNOON, WINDOW_EVENING):
            start_hour, end_hour = _WINDOW_BOUNDS[name]
            if start_hour <= now.hour < end_hour:
                return name, midnight + timedelta(hours=start_hour)

        # Night runs 21:00 -> 06:00, so before 6am the window opened yesterday.
        night_start = midnight + timedelta(hours=_WINDOW_BOUNDS[WINDOW_NIGHT][0])
        if now.hour < 6:
            night_start -= timedelta(days=1)
        return WINDOW_NIGHT, night_start

    @staticmethod
    def _normalize(value: datetime | str | None) -> datetime | None:
        """
        Coerce a stored timestamp into an aware datetime.

        SQLModel table models skip validation, so a timestamp read back from
        the database arrives as the raw ISO string rather than a datetime.
        Naive values are treated as UTC so comparisons never raise.
        """
        if value is None:
            return None
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def is_due(self, responsibility: Responsibility, now: datetime | None = None) -> bool:
        """
        Whether a responsibility should run right now.

        Due when the current window is one it's scheduled for and it hasn't
        already run since that window opened.
        """
        now = now or datetime.now().astimezone()
        window, window_start = self.current_window(now)

        # A null schedule means the model default: every window.
        schedule = responsibility.schedule
        if schedule is None:
            schedule = list(_WINDOW_BOUNDS)
        if window not in schedule:
            return False

        last_run = self._normalize(responsibility.last_run)
        return last_run is None or last_run < window_start

    # ---------- execution ----------

    @staticmethod
    def _report_instruction(responsibility: Responsibility) -> str:
        """
        Tell the agent how to report, and authorize it to do so.

        A responsibility with report_type=email is standing permission from the
        user for this specific report, which is why it overrides send_email's
        usual "ask before sending" rule.
        """
        report_type = responsibility.report_type
        if report_type is None:
            return ""

        if report_type not in _SUPPORTED_REPORT_TYPES:
            return (
                f"This responsibility is configured to report by {report_type}, "
                "but no tool for that exists yet. Do not attempt it and do not "
                "substitute another channel — complete the work and summarize "
                "the outcome in your final reply instead."
            )

        recipient = os.getenv("NOVA_REPORT_EMAIL") or os.getenv("EMAIL_SENDER")
        if not recipient:
            return (
                "This responsibility is configured to report by email, but no "
                "recipient is configured (set NOVA_REPORT_EMAIL or "
                "EMAIL_SENDER). Summarize the outcome in your final reply "
                "instead of sending anything."
            )

        return (
            f"{responsibility.report_type_prompt()} "
            f"Send it with the send_email tool to {recipient}. The user set up "
            "this responsibility to be reported by email, so that email is "
            "already authorized — send it without asking for confirmation, "
            "since this runs in the background with nobody to ask. Use a "
            f"subject line identifying the responsibility ('{responsibility.name}') "
            "and keep the body to what you actually did and found."
        )

    def preform_responsibility(
        self, responsibility_id: int, prompt: Optional[str] = None
    ) -> str:
        """
        Run one responsibility to completion and stamp it as run.

        last_run is stamped even when the agent reports a failure: the run did
        happen, and re-firing it every tick of the same window would spam the
        model. A genuinely failed run gets retried in the next window.
        """
        responsibility = self.responsibility_dao.get(responsibility_id)
        if responsibility is None:
            raise ValueError(f"Responsibility with id {responsibility_id} not found")

        instructions = [part for part in [prompt, self._report_instruction(responsibility)] if part]

        # Imported here so the module-level import graph stays acyclic: the
        # agent loop reaches back into responsibilities to build its prompt.
        from src.harness.agent_loop import AgentLoop

        try:
            result = AgentLoop().run_agent(
                prompt="\n".join(instructions) or None,
                responsibility_id=responsibility_id,
            )
        finally:
            self.responsibility_dao.set_last_run(
                responsibility_id, datetime.now(timezone.utc).isoformat()
            )

        return result

    def check_for_responsibilities(self, now: datetime | None = None) -> dict:
        """
        Run every responsibility that is past due for the current window.

        Called by the worker on a schedule. One responsibility failing must not
        stop the others, so failures are caught per responsibility. `now`
        defaults to local time — windows like "morning" are local-clock
        concepts — and is injectable for testing.
        """
        now = now or datetime.now().astimezone()
        window, _ = self.current_window(now)

        try:
            responsibilities = self.responsibility_dao.get_all()
        except Exception as exc:
            print(f"Failed to load responsibilities: {exc}")
            return {"window": window, "due": 0, "ran": 0, "failed": 0}

        due = [r for r in responsibilities if self.is_due(r, now)]
        ran = 0
        failed = 0

        for responsibility in due:
            print(f"Running responsibility {responsibility.id}: {responsibility.name}")
            try:
                self.preform_responsibility(responsibility.id)
                ran += 1
            except Exception as exc:
                failed += 1
                print(f"Responsibility {responsibility.id} failed: {exc}")

        summary = {
            "window": window,
            "checked": len(responsibilities),
            "due": len(due),
            "ran": ran,
            "failed": failed,
        }
        print(f"check_for_responsibilities: {summary}")
        return summary
