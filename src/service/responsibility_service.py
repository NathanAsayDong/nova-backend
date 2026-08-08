import os
from datetime import datetime, timedelta, timezone
from typing import Optional

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
