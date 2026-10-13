import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from src.model.scheduled_task import ScheduledTask, TaskStatus
from src.service.scheduled_task_service import ScheduledTaskService


def soon(minutes: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


class FakeTaskDao:
    def __init__(self, tasks=()):
        self.tasks = {t.id: t for t in tasks}
        self.finish_calls = []

    def get(self, id):
        return self.tasks.get(int(id))

    def list_by_status(self, status=None):
        return [
            t for t in self.tasks.values() if status is None or str(t.status) == status
        ]

    def get_due(self, now_utc):
        now = datetime.fromisoformat(now_utc)
        return [
            t
            for t in self.tasks.values()
            if t.status == TaskStatus.PENDING and t.run_at <= now
        ]

    def create(self, entity):
        entity.id = max(self.tasks, default=0) + 1
        self.tasks[entity.id] = entity
        return entity

    def claim(self, id, started_at_utc):
        task = self.tasks.get(int(id))
        if task is None or task.status != TaskStatus.PENDING:
            return None
        task.status = TaskStatus.RUNNING
        return task

    def finish(self, id, status, completed_at_utc, result):
        self.finish_calls.append((id, status, result))
        task = self.tasks[int(id)]
        task.status = status
        task.result = result
        return task

    def cancel(self, id):
        task = self.tasks.get(int(id))
        if task is None or task.status != TaskStatus.PENDING:
            return None
        task.status = TaskStatus.CANCELLED
        return task


class FakeProjectDao:
    def get(self, id):
        if int(id) != 7:
            return None
        return SimpleNamespace(id=7)


class FakeUpdateService:
    def __init__(self):
        self.created = []

    def create_update(
        self, update_message, project_id=None, conversation_uuid=None, report_type=None
    ):
        record = {
            "update_message": update_message,
            "project_id": project_id,
            "report_type": report_type,
        }
        self.created.append(record)
        return record


def build_service(tasks=()) -> ScheduledTaskService:
    service = ScheduledTaskService.__new__(ScheduledTaskService)
    service.task_dao = FakeTaskDao(tasks)
    service.project_dao = FakeProjectDao()
    service.update_service = FakeUpdateService()
    return service


def pending(id=1, minutes_ago=5, **kwargs) -> ScheduledTask:
    return ScheduledTask(
        id=id,
        name=kwargs.pop("name", "Check thing"),
        description="Look at the thing.",
        run_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
        status=TaskStatus.PENDING,
        **kwargs,
    )


class CreateTests(unittest.TestCase):
    def test_creates_pending_task(self):
        service = build_service()
        result = service.create_scheduled_task("Ping", "Do the ping.", soon())
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["name"], "Ping")

    def test_blank_name_or_description_refused(self):
        service = build_service()
        with self.assertRaises(ValueError):
            service.create_scheduled_task("  ", "x", soon())
        with self.assertRaises(ValueError):
            service.create_scheduled_task("x", "  ", soon())

    def test_unparseable_run_at_refused(self):
        service = build_service()
        with self.assertRaises(ValueError):
            service.create_scheduled_task("x", "y", "tomorrow at 3pm")

    def test_past_run_at_refused(self):
        service = build_service()
        with self.assertRaises(ValueError):
            service.create_scheduled_task("x", "y", soon(minutes=-30))

    def test_just_past_run_at_is_tolerated(self):
        service = build_service()
        service.create_scheduled_task("x", "y", soon(minutes=-0.5))

    def test_offset_is_honoured(self):
        service = build_service()
        run_at = (datetime.now(timezone.utc) + timedelta(hours=2)).astimezone(
            timezone(timedelta(hours=-6))
        )
        created = service.task_dao.create(
            ScheduledTask(name="x", description="y", run_at=run_at)
        )
        self.assertEqual(created.run_at, run_at)

    def test_naive_run_at_is_read_as_local_time(self):
        service = build_service()
        naive = (datetime.now() + timedelta(hours=1)).replace(microsecond=0)
        result = service.create_scheduled_task("x", "y", naive.isoformat())
        stored = service.task_dao.get(result["id"]).run_at
        self.assertEqual(stored, naive.astimezone())

    def test_unknown_project_refused(self):
        service = build_service()
        with self.assertRaises(ValueError):
            service.create_scheduled_task("x", "y", soon(), project_id=99)

    def test_unknown_report_type_refused(self):
        service = build_service()
        with self.assertRaises(ValueError):
            service.create_scheduled_task("x", "y", soon(), report_type="carrier-pigeon")

    def test_undeliverable_report_type_warns(self):
        service = build_service()
        result = service.create_scheduled_task("x", "y", soon(), report_type="chat")
        self.assertIn("warning", result)


class ListAndCancelTests(unittest.TestCase):
    def test_list_defaults_to_pending(self):
        done = pending(id=2)
        done.status = TaskStatus.DONE
        service = build_service([pending(id=1), done])
        self.assertEqual([t["id"] for t in service.list_scheduled_tasks()], [1])

    def test_list_all(self):
        done = pending(id=2)
        done.status = TaskStatus.DONE
        service = build_service([pending(id=1), done])
        self.assertEqual(len(service.list_scheduled_tasks("all")), 2)

    def test_list_unknown_status_refused(self):
        with self.assertRaises(ValueError):
            build_service().list_scheduled_tasks("nope")

    def test_cancel_pending(self):
        service = build_service([pending(id=1)])
        service.cancel_scheduled_task(1)
        self.assertEqual(service.task_dao.get(1).status, TaskStatus.CANCELLED)

    def test_cancel_finished_refused(self):
        task = pending(id=1)
        task.status = TaskStatus.DONE
        with self.assertRaises(ValueError):
            build_service([task]).cancel_scheduled_task(1)

    def test_cancel_missing_refused(self):
        with self.assertRaises(ValueError):
            build_service().cancel_scheduled_task(404)


class RunTests(unittest.TestCase):
    def _patch_agent(self, result="all done", side_effect=None):
        agent = mock.MagicMock()
        agent.run_agent.side_effect = side_effect
        if side_effect is None:
            agent.run_agent.return_value = result
        patcher = mock.patch("src.harness.agent_loop.AgentLoop", return_value=agent)
        patcher.start()
        self.addCleanup(patcher.stop)
        return agent

    def test_success_marks_done_and_files_update(self):
        agent = self._patch_agent("all done")
        service = build_service([pending(id=1, report_type="email", project_id=7)])

        outcome = service.run_task(1)

        self.assertEqual(outcome, TaskStatus.DONE)
        self.assertEqual(service.task_dao.get(1).status, TaskStatus.DONE)
        self.assertEqual(agent.run_agent.call_args.kwargs["report_type"], "email")
        self.assertIn("Look at the thing.", agent.run_agent.call_args.kwargs["prompt"])
        update = service.update_service.created[0]
        self.assertEqual(update["update_message"], "all done")
        self.assertEqual(update["report_type"], "email")
        self.assertEqual(update["project_id"], 7)

    def test_failure_marks_failed_and_is_not_retried(self):
        self._patch_agent(side_effect=RuntimeError("boom"))
        service = build_service([pending(id=1, report_type="call")])

        self.assertEqual(service.run_task(1), TaskStatus.FAILED)
        self.assertEqual(service.task_dao.get(1).status, TaskStatus.FAILED)
        # A failed run is reported quietly: never a surprise phone call.
        self.assertIsNone(service.update_service.created[0]["report_type"])
        self.assertIn("boom", service.update_service.created[0]["update_message"])

        # Nothing pending is left for a later pass to pick up.
        self.assertEqual(service.run_due_tasks()["due"], 0)

    def test_already_claimed_task_is_left_alone(self):
        agent = self._patch_agent()
        task = pending(id=1)
        task.status = TaskStatus.RUNNING
        service = build_service([task])

        self.assertIsNone(service.run_task(1))
        agent.run_agent.assert_not_called()

    def test_update_failure_does_not_fail_the_run(self):
        self._patch_agent()
        service = build_service([pending(id=1)])
        service.update_service.create_update = mock.Mock(side_effect=RuntimeError("db"))

        self.assertEqual(service.run_task(1), TaskStatus.DONE)


class RunDueTests(unittest.TestCase):
    def setUp(self):
        agent = mock.MagicMock()
        agent.run_agent.return_value = "ok"
        patcher = mock.patch("src.harness.agent_loop.AgentLoop", return_value=agent)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.agent = agent

    def test_runs_only_due_tasks(self):
        future = pending(id=2, minutes_ago=-60)
        service = build_service([pending(id=1), future])

        summary = service.run_due_tasks()

        self.assertEqual(summary, {"due": 1, "ran": 1, "failed": 0})
        self.assertEqual(service.task_dao.get(2).status, TaskStatus.PENDING)

    def test_very_overdue_task_still_runs(self):
        service = build_service([pending(id=1, minutes_ago=60 * 24)])
        self.assertEqual(service.run_due_tasks()["ran"], 1)

    def test_one_failure_does_not_stop_the_rest(self):
        self.agent.run_agent.side_effect = [RuntimeError("boom"), "ok"]
        service = build_service([pending(id=1, minutes_ago=10), pending(id=2)])

        summary = service.run_due_tasks()

        self.assertEqual(summary, {"due": 2, "ran": 1, "failed": 1})

    def test_task_runs_once(self):
        service = build_service([pending(id=1)])
        service.run_due_tasks()
        service.run_due_tasks()
        self.assertEqual(self.agent.run_agent.call_count, 1)


class RecoverStuckTests(unittest.TestCase):
    def test_running_tasks_are_failed_not_rerun(self):
        stuck = pending(id=1, report_type="call")
        stuck.status = TaskStatus.RUNNING
        waiting = pending(id=2)
        service = build_service([stuck, waiting])

        with mock.patch("src.harness.agent_loop.AgentLoop") as agent:
            summary = service.recover_stuck_tasks()

        self.assertEqual(summary, {"recovered": 1})
        self.assertEqual(service.task_dao.get(1).status, TaskStatus.FAILED)
        self.assertEqual(service.task_dao.get(2).status, TaskStatus.PENDING)
        agent.assert_not_called()
        # Quiet update: no phone call for an interruption.
        self.assertIsNone(service.update_service.created[0]["report_type"])

    def test_nothing_stuck_is_a_noop(self):
        service = build_service([pending(id=1)])
        self.assertEqual(service.recover_stuck_tasks(), {"recovered": 0})
        self.assertEqual(service.update_service.created, [])


class CurrentTimeTests(unittest.TestCase):
    def test_reports_offset_aware_now(self):
        result = ScheduledTaskService.get_current_time()
        self.assertIsNotNone(datetime.fromisoformat(result["now"]).tzinfo)
        self.assertTrue(result["weekday"])


if __name__ == "__main__":
    unittest.main()
