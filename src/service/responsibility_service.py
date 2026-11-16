from datetime import datetime, timedelta, timezone
from typing import Optional

from src.dao.project_dao import ProjectDao
from src.dao.responsibility_dao import ResponsibilityDao
from src.model.report_type import (
    SUPPORTED_REPORT_TYPES,
    ReportType,
    encode_report_types,
    normalize_report_types,
)
from src.model.responsibility import Responsibility
from src.service.update_service import UpdateService

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


class ResponsibilityService:
    def __init__(self) -> None:
        self.responsibility_dao = ResponsibilityDao()
        self.project_dao = ProjectDao()
        self.update_service = UpdateService()

    # ---------- crud ----------

    @staticmethod
    def _to_dict(responsibility: Responsibility) -> dict:
        """JSON-serializable view, including whether each report channel works yet."""
        channels = responsibility.channels
        return {
            "id": responsibility.id,
            "name": responsibility.name,
            "description": responsibility.description,
            "schedule": responsibility.schedule,
            "project_id": responsibility.project_id,
            "report_type": str(responsibility.report_type) if responsibility.report_type else None,
            "channels": [str(c) for c in channels],
            "report_deliverable": (
                all(c in SUPPORTED_REPORT_TYPES for c in channels) if channels else None
            ),
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
    def _validate_report_type(report_type: "str | list[str] | None") -> list[ReportType]:
        """Normalize a single channel or a list of them. See Update._validate_report_type."""
        return normalize_report_types(report_type)

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
        report_type: "str | list[str] | None" = None,
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

        if not schedule:
            raise ValueError(
                "A schedule is required: choose one or more of "
                f"{sorted(_WINDOW_BOUNDS)}. These are coarse windows "
                "(morning=6-12, afternoon=12-17, evening=17-21, night=21-6), "
                "not exact clock times — for an exact time use "
                "create_scheduled_task instead."
            )

        channels = self._validate_report_type(report_type)
        undeliverable = [c for c in channels if c not in SUPPORTED_REPORT_TYPES]
        created = self.responsibility_dao.create(
            Responsibility(
                name=name,
                description=description,
                schedule=self._validate_schedule(schedule),
                project_id=self._validate_project(project_id),
                report_type=encode_report_types(channels),
            )
        )

        result = self._to_dict(created)
        if undeliverable:
            names = ", ".join(str(c) for c in undeliverable)
            result["warning"] = (
                f"Reporting by {names} is not deliverable yet — no channel "
                "exists for it. The responsibility will still run and post "
                "its outcome as an update. Only email, sms, call, and speak "
                "can be delivered today."
            )
        return result

    def update_responsibility(
        self,
        responsibility_id: int,
        name: str | None = None,
        description: str | None = None,
        schedule: list[str] | None = None,
        project_id: int | None = None,
        report_type: "str | list[str] | None" = None,
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
            responsibility.report_type = encode_report_types(
                self._validate_report_type(report_type)
            )

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

    def preform_responsibility(
        self, responsibility_id: int, prompt: Optional[str] = None
    ) -> str:
        """
        Run one responsibility to completion, record its outcome, stamp it as run.

        The run's summary becomes an Update carrying the responsibility's
        report_type, and delivery happens from there — the agent is never asked
        to email or call anyone itself. That split is what lets a report be
        retried, rate-limited, or held until morning without the agent (which
        is long gone by then) being involved.

        last_run is stamped even when the agent reports a failure: the run did
        happen, and re-firing it every tick of the same window would spam the
        model. A genuinely failed run gets retried in the next window.

        A failure still gets its own Update (and delivery, if one was asked
        for) -- see the except branch below -- rather than disappearing the
        moment run_agent raises, so an explicit report_type still reaches
        Nate when the run never produced a result to hand to
        _record_outcome.
        """
        responsibility = self.responsibility_dao.get(responsibility_id)
        if responsibility is None:
            raise ValueError(f"Responsibility with id {responsibility_id} not found")

        # Imported here so the module-level import graph stays acyclic: the
        # agent loop reaches back into responsibilities to build its prompt.
        from src.harness.agent_loop import AgentLoop

        try:
            result = AgentLoop().run_agent(
                prompt=prompt,
                responsibility_id=responsibility_id,
                report_type=responsibility.report_type,
            )
        except Exception as exc:
            self._record_outcome(
                responsibility,
                f"Responsibility '{responsibility.name}' failed and was not "
                f"retried: {exc}",
                failed=True,
            )
            raise
        finally:
            self.responsibility_dao.set_last_run(
                responsibility_id, datetime.now(timezone.utc).isoformat()
            )

        self._record_outcome(responsibility, result)
        return result

    # Marker the agent can lead its final reply with (see
    # AgentLoop._RESPONSIBILITY_RUN_RESTRICTION) to flag that a routine-looking
    # run actually needs Nate's attention right now. There is no dedicated
    # column for this on Responsibility/Update -- adding one would be a schema
    # change -- so this text convention is the least invasive hook: it is
    # stripped from the stored message before filing, so the badge/email/call
    # never shows the raw marker.
    _NEEDS_ATTENTION_MARKER = "NEEDS ATTENTION:"

    def _record_outcome(
        self, responsibility: Responsibility, result: str, failed: bool = False
    ) -> None:
        """
        Turn a finished run into an Update, queued for delivery only when it's
        earned one.

        Delivery (email/call/sms) is reserved for a failed run or one that
        explicitly flagged itself as needing attention (see
        _NEEDS_ATTENTION_MARKER) -- a routine success is filed as an Update
        the same as always, still visible via get_unviewed_updates and the
        badge, but nothing is pushed for it. `failed` comes from
        preform_responsibility's except branch; a routine completion never
        sets it.

        Best-effort: the work already happened, so failing to file the update
        must not turn a successful run into a raised exception that the worker
        logs as a failure and retries.
        """
        summary = (result or "").strip()

        needs_attention = False
        if not failed and summary.upper().startswith(self._NEEDS_ATTENTION_MARKER):
            needs_attention = True
            summary = summary[len(self._NEEDS_ATTENTION_MARKER) :].strip()

        if not summary:
            summary = (
                f"Responsibility '{responsibility.name}' ran but produced no summary."
            )

        deliverable = failed or needs_attention

        try:
            self.update_service.create_update(
                update_message=summary,
                project_id=responsibility.project_id,
                report_type=(
                    responsibility.report_type
                    if responsibility.report_type and deliverable
                    else None
                ),
            )
        except Exception as exc:
            print(
                f"Responsibility {responsibility.id} could not record its update: {exc}"
            )

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
