from datetime import datetime, timedelta, timezone

from src.dao.project_dao import ProjectDao
from src.dao.scheduled_task_dao import ScheduledTaskDao
from src.model.report_type import SUPPORTED_REPORT_TYPES, ReportType
from src.model.scheduled_task import ScheduledTask, TaskStatus
from src.service.update_service import UpdateService

# How far in the past a run_at may be and still be accepted. A little slack
# covers the gap between Nova computing "in a minute" and the call landing; any
# more almost always means the model got a date or offset wrong, and accepting
# it would fire the task immediately instead of when the user meant.
_PAST_TOLERANCE = timedelta(minutes=1)


class ScheduledTaskService:
    def __init__(self) -> None:
        self.task_dao = ScheduledTaskDao()
        self.project_dao = ProjectDao()
        self.update_service = UpdateService()

    # ---------- helpers ----------

    @staticmethod
    def _parse_time(value: datetime | str | None) -> datetime | None:
        """
        Coerce a timestamp into an aware datetime.

        SQLModel table models skip validation, so a timestamp read back from
        the database arrives as the raw ISO string. A value with no offset is
        read as server-local time, the same clock windows and quiet hours use.
        """
        if value is None:
            return None
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.strip())
            except ValueError:
                return None
        if value.tzinfo is None:
            return value.astimezone()
        return value

    @staticmethod
    def _to_dict(task: ScheduledTask) -> dict:
        report_type = task.report_type
        run_at = ScheduledTaskService._parse_time(task.run_at)
        return {
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "run_at": run_at.astimezone().isoformat() if run_at else None,
            "status": str(task.status) if task.status else None,
            "project_id": task.project_id,
            "report_type": str(report_type) if report_type else None,
            "report_deliverable": report_type in SUPPORTED_REPORT_TYPES
            if report_type
            else None,
            "result": task.result,
        }

    @staticmethod
    def _validate_report_type(report_type: str | None) -> ReportType | None:
        if report_type is None:
            return None
        candidate = str(report_type).strip().lower()
        if not candidate:
            return None
        try:
            return ReportType(candidate)
        except ValueError:
            raise ValueError(
                f"Unknown report_type '{report_type}'. Valid types are "
                f"{[str(t) for t in ReportType]}."
            )

    def _validate_project(self, project_id: int | None) -> int | None:
        if project_id is None:
            return None
        project = self.project_dao.get(int(project_id))
        if project is None:
            raise ValueError(f"Project {project_id} does not exist.")
        return project.id

    @staticmethod
    def get_current_time() -> dict:
        """
        The server's current local time, for working out a run_at.

        Nova's prompt carries no clock, so without this it has nothing to
        resolve "tomorrow at 3pm" against.
        """
        now = datetime.now().astimezone()
        return {
            "now": now.isoformat(),
            "weekday": now.strftime("%A"),
            "timezone": now.tzname(),
            "utc_offset": now.strftime("%z"),
        }

    # ---------- crud ----------

    def create_scheduled_task(
        self,
        name: str,
        description: str,
        run_at: str,
        project_id: int | None = None,
        report_type: str | None = None,
    ) -> dict:
        """
        Schedule a task to run once at `run_at`.

        The description is the agent's entire brief when it runs later with
        nobody present, so it has to stand alone.
        """
        name = (name or "").strip()
        if not name:
            raise ValueError("A task name is required.")

        description = (description or "").strip()
        if not description:
            raise ValueError(
                "A description is required — it is the only instruction the "
                "agent gets when this runs unattended, so state the task fully."
            )

        when = self._parse_time(run_at)
        if when is None:
            raise ValueError(
                f"run_at '{run_at}' is not a valid ISO-8601 timestamp. Use "
                "something like 2026-10-14T15:00:00-06:00; call get_current_time "
                "first if you need the current date and UTC offset."
            )
        if when < datetime.now(timezone.utc) - _PAST_TOLERANCE:
            raise ValueError(
                f"run_at {when.isoformat()} is in the past. Call "
                "get_current_time and schedule a moment that hasn't happened yet."
            )

        validated_type = self._validate_report_type(report_type)
        created = self.task_dao.create(
            ScheduledTask(
                name=name,
                description=description,
                run_at=when,
                project_id=self._validate_project(project_id),
                report_type=validated_type,
            )
        )

        result = self._to_dict(created)
        if validated_type is not None and validated_type not in SUPPORTED_REPORT_TYPES:
            result["warning"] = (
                f"Reporting by {validated_type} is not deliverable yet — no "
                "channel exists for it. The task will still run and post its "
                "outcome as an update. Only email, sms and call can be delivered."
            )
        return result

    def list_scheduled_tasks(self, status: str | None = None) -> list[dict]:
        """List tasks, soonest first. Defaults to the ones still waiting to run."""
        candidate = (status or TaskStatus.PENDING.value).strip().lower()
        if candidate == "all":
            tasks = self.task_dao.list_by_status()
        else:
            try:
                tasks = self.task_dao.list_by_status(TaskStatus(candidate).value)
            except ValueError:
                raise ValueError(
                    f"Unknown status '{status}'. Valid statuses are "
                    f"{[str(s) for s in TaskStatus]} or 'all'."
                )
        return [self._to_dict(task) for task in tasks]

    def cancel_scheduled_task(self, task_id: int) -> dict:
        """Cancel a task that hasn't started. Running or finished tasks can't be."""
        task = self.task_dao.get(int(task_id))
        if task is None:
            raise ValueError(f"Scheduled task {task_id} does not exist.")

        cancelled = self.task_dao.cancel(task.id)
        if cancelled is None:
            raise ValueError(
                f"Scheduled task {task_id} is {task.status} and can no longer "
                "be cancelled — only pending tasks can."
            )
        return {"status": "cancelled", "task": self._to_dict(cancelled)}

    # ---------- execution ----------

    def run_task(self, task_id: int) -> TaskStatus | None:
        """
        Run one task to completion and record how it went.

        Returns the final status (DONE or FAILED), or None if the task was
        already claimed or cancelled by the time we got to it. A failure is recorded on the
        row and filed as an update rather than raised, and it is never
        retried: the agent may already have sent or changed something, and
        running it again would do that twice.
        """
        now = datetime.now(timezone.utc)
        task = self.task_dao.claim(int(task_id), now.isoformat())
        if task is None:
            return None

        # Imported here so the module-level import graph stays acyclic: the
        # agent loop reaches back into the services to build its tools.
        from src.harness.agent_loop import AgentLoop

        report_type = str(task.report_type) if task.report_type else None
        try:
            result = AgentLoop().run_agent(
                prompt=task.to_prompt(),
                report_type=report_type,
            )
        except Exception as exc:
            self._finish(task, TaskStatus.FAILED, str(exc))
            self._record_update(
                task,
                f"Scheduled task '{task.name}' failed and was not retried: {exc}",
                report_type=None,
            )
            return TaskStatus.FAILED

        summary = (result or "").strip()
        if not summary:
            summary = f"Scheduled task '{task.name}' ran but produced no summary."
        self._finish(task, TaskStatus.DONE, summary)
        self._record_update(task, summary, report_type=report_type)
        return TaskStatus.DONE

    def _finish(self, task: ScheduledTask, status: TaskStatus, result: str) -> None:
        try:
            self.task_dao.finish(
                task.id, status, datetime.now(timezone.utc).isoformat(), result
            )
        except Exception as exc:
            print(f"Scheduled task {task.id} could not record its outcome: {exc}")

    def _record_update(
        self, task: ScheduledTask, message: str, report_type: str | None
    ) -> None:
        """
        File the outcome as an Update, queued for delivery if one was asked for.

        Best-effort: the work already happened, so failing to file the update
        must not turn into an error the worker logs as a failed run.
        """
        try:
            self.update_service.create_update(
                update_message=message,
                project_id=task.project_id,
                report_type=report_type,
            )
        except Exception as exc:
            print(f"Scheduled task {task.id} could not record its update: {exc}")

    def recover_stuck_tasks(self) -> dict:
        """
        Fail any task left `running` by a worker that died mid-run.

        Call once at worker startup, when nothing can legitimately be running:
        the worker runs tasks one at a time on its own thread, so a row still
        marked running belongs to a process that no longer exists. It is marked
        failed, not re-run — the agent may have got partway through, and
        running it again could repeat what it already did. A quiet update says
        so, because otherwise the task would just never report back.
        """
        try:
            stuck = self.task_dao.list_by_status(TaskStatus.RUNNING.value)
        except Exception as exc:
            print(f"Failed to look for stuck scheduled tasks: {exc}")
            return {"recovered": 0}

        for task in stuck:
            message = (
                f"Scheduled task '{task.name}' was interrupted when the worker "
                "restarted, so it may be only partly done. It was not re-run."
            )
            print(f"Recovering stuck scheduled task {task.id}: {task.name}")
            self._finish(task, TaskStatus.FAILED, message)
            self._record_update(task, message, report_type=None)

        return {"recovered": len(stuck)}

    def run_due_tasks(self, now: datetime | None = None) -> dict:
        """
        Run every pending task whose time has come.

        Called by the worker every minute. Overdue tasks always run, however
        late — if the worker was down, the work still happened-late rather
        than not at all. One task failing must not stop the others.
        """
        now = now or datetime.now(timezone.utc)

        try:
            due = self.task_dao.get_due(now.astimezone(timezone.utc).isoformat())
        except Exception as exc:
            print(f"Failed to load scheduled tasks: {exc}")
            return {"due": 0, "ran": 0, "failed": 0}

        ran = 0
        failed = 0
        for task in due:
            print(f"Running scheduled task {task.id}: {task.name}")
            try:
                outcome = self.run_task(task.id)
                if outcome == TaskStatus.DONE:
                    ran += 1
                elif outcome == TaskStatus.FAILED:
                    failed += 1
            except Exception as exc:
                failed += 1
                print(f"Scheduled task {task.id} failed: {exc}")

        summary = {"due": len(due), "ran": ran, "failed": failed}
        print(f"run_due_tasks: {summary}")
        return summary
