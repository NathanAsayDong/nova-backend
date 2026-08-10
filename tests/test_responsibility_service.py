import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from src.model.responsibility import Responsibility, ResponsibilityReportType
from src.service.responsibility_service import ResponsibilityService


def at(hour: int, minute: int = 0, day: int = 15) -> datetime:
    return datetime(2026, 8, day, hour, minute, tzinfo=timezone.utc)


class FakeResponsibilityDao:
    def __init__(self, responsibilities=()):
        self.responsibilities = {r.id: r for r in responsibilities}
        self.last_run_calls = []

    def get(self, id):
        return self.responsibilities.get(int(id))

    def get_all(self):
        return list(self.responsibilities.values())

    def set_last_run(self, id, timestamp_utc):
        self.last_run_calls.append((id, timestamp_utc))
        return self.responsibilities.get(int(id))

    def create(self, entity):
        entity.id = max(self.responsibilities, default=0) + 1
        self.responsibilities[entity.id] = entity
        return entity

    def update(self, id, entity):
        if int(id) not in self.responsibilities:
            return None
        self.responsibilities[int(id)] = entity
        return entity

    def delete(self, id):
        self.responsibilities.pop(int(id), None)


class FakeProjectDao:
    def __init__(self, project_ids=(1, 7)):
        self.project_ids = set(project_ids)

    def get(self, id):
        if int(id) not in self.project_ids:
            return None
        return SimpleNamespace(id=int(id), name=f"Project {id}")


def build_service(responsibilities=()) -> ResponsibilityService:
    service = ResponsibilityService.__new__(ResponsibilityService)
    service.responsibility_dao = FakeResponsibilityDao(responsibilities)
    service.project_dao = FakeProjectDao()
    return service


class WindowTests(unittest.TestCase):
    def test_window_names_by_hour(self):
        service = build_service()
        cases = {
            6: "morning",
            11: "morning",
            12: "afternoon",
            16: "afternoon",
            17: "evening",
            20: "evening",
            21: "night",
            23: "night",
            0: "night",
            5: "night",
        }
        for hour, expected in cases.items():
            with self.subTest(hour=hour):
                self.assertEqual(service.current_window(at(hour))[0], expected)

    def test_window_start_is_window_open_time(self):
        service = build_service()
        _, start = service.current_window(at(14, 30))
        self.assertEqual(start, at(12))

    def test_night_before_dawn_started_yesterday(self):
        service = build_service()
        window, start = service.current_window(at(2, 0, day=16))
        self.assertEqual(window, "night")
        self.assertEqual(start, at(21, 0, day=15))

    def test_night_after_dusk_started_today(self):
        service = build_service()
        _, start = service.current_window(at(22, 0, day=15))
        self.assertEqual(start, at(21, 0, day=15))


class DueTests(unittest.TestCase):
    def setUp(self):
        self.service = build_service()

    def test_never_run_is_due(self):
        r = Responsibility(id=1, name="x", schedule=["morning"], last_run=None)
        self.assertTrue(self.service.is_due(r, at(8)))

    def test_not_due_outside_scheduled_window(self):
        r = Responsibility(id=1, name="x", schedule=["morning"], last_run=None)
        self.assertFalse(self.service.is_due(r, at(14)))

    def test_not_due_again_within_same_window(self):
        r = Responsibility(id=1, name="x", schedule=["morning"], last_run=at(7))
        self.assertFalse(self.service.is_due(r, at(9)))

    def test_due_again_in_next_window(self):
        r = Responsibility(
            id=1, name="x", schedule=["morning", "afternoon"], last_run=at(7)
        )
        self.assertTrue(self.service.is_due(r, at(13)))

    def test_ran_yesterday_is_due_today(self):
        r = Responsibility(id=1, name="x", schedule=["morning"], last_run=at(8, day=14))
        self.assertTrue(self.service.is_due(r, at(8, day=15)))

    def test_null_schedule_defaults_to_every_window(self):
        r = Responsibility(id=1, name="x", schedule=None, last_run=None)
        for hour in (8, 14, 19, 23):
            with self.subTest(hour=hour):
                self.assertTrue(self.service.is_due(r, at(hour)))

    def test_empty_schedule_never_runs(self):
        r = Responsibility(id=1, name="x", schedule=[], last_run=None)
        self.assertFalse(self.service.is_due(r, at(8)))

    def test_last_run_as_iso_string_is_parsed(self):
        """SQLModel table models skip validation, so the db hands back a str."""
        r = Responsibility(id=1, name="x", schedule=["morning"])
        r.last_run = "2026-08-15T07:00:00+00:00"
        self.assertFalse(self.service.is_due(r, at(9)))

        r.last_run = "2026-08-14T07:00:00+00:00"
        self.assertTrue(self.service.is_due(r, at(9)))

    def test_unparseable_last_run_is_treated_as_never_run(self):
        r = Responsibility(id=1, name="x", schedule=["morning"])
        r.last_run = "not a timestamp"
        self.assertTrue(self.service.is_due(r, at(9)))

    def test_naive_last_run_is_treated_as_utc(self):
        r = Responsibility(
            id=1,
            name="x",
            schedule=["morning"],
            last_run=datetime(2026, 8, 15, 7, 0),  # naive
        )
        self.assertFalse(self.service.is_due(r, at(9)))


class ReportInstructionTests(unittest.TestCase):
    def test_no_report_type_gives_no_instruction(self):
        r = Responsibility(id=1, name="x", report_type=None)
        self.assertEqual(ResponsibilityService._report_instruction(r), "")

    @mock.patch.dict("os.environ", {"NOVA_REPORT_EMAIL": "me@example.com"})
    def test_email_instruction_authorizes_send(self):
        r = Responsibility(id=1, name="Daily digest", report_type=ResponsibilityReportType.EMAIL)
        instruction = ResponsibilityService._report_instruction(r)
        self.assertIn("me@example.com", instruction)
        self.assertIn("send_email", instruction)
        self.assertIn("without asking for confirmation", instruction)
        self.assertIn("Daily digest", instruction)

    @mock.patch.dict("os.environ", {}, clear=True)
    def test_email_without_recipient_falls_back_to_reply(self):
        r = Responsibility(id=1, name="x", report_type=ResponsibilityReportType.EMAIL)
        instruction = ResponsibilityService._report_instruction(r)
        self.assertIn("no recipient is configured", instruction)

    def test_unsupported_report_type_is_not_attempted(self):
        for report_type in (
            ResponsibilityReportType.SMS,
            ResponsibilityReportType.CALL,
            ResponsibilityReportType.CHAT,
        ):
            with self.subTest(report_type=report_type):
                r = Responsibility(id=1, name="x", report_type=report_type)
                instruction = ResponsibilityService._report_instruction(r)
                self.assertIn("no tool for that exists yet", instruction)
                self.assertIn("Do not attempt it", instruction)


class PerformTests(unittest.TestCase):
    def setUp(self):
        self.responsibility = Responsibility(
            id=7, name="Check things", description="Look at the thing.", schedule=["morning"]
        )
        self.service = build_service([self.responsibility])

    def _patch_agent(self, result="done", side_effect=None):
        agent = mock.MagicMock()
        agent.run_agent.side_effect = side_effect
        if side_effect is None:
            agent.run_agent.return_value = result
        patcher = mock.patch(
            "src.harness.agent_loop.AgentLoop", return_value=agent
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        return agent

    def test_runs_through_run_agent_with_responsibility_id(self):
        agent = self._patch_agent(result="all done")

        result = self.service.preform_responsibility(7)

        self.assertEqual(result, "all done")
        self.assertEqual(agent.run_agent.call_args.kwargs["responsibility_id"], 7)

    def test_stamps_last_run(self):
        self._patch_agent()
        self.service.preform_responsibility(7)
        self.assertEqual(len(self.service.responsibility_dao.last_run_calls), 1)
        self.assertEqual(self.service.responsibility_dao.last_run_calls[0][0], 7)

    def test_last_run_stamped_even_when_agent_raises(self):
        self._patch_agent(side_effect=RuntimeError("boom"))

        with self.assertRaises(RuntimeError):
            self.service.preform_responsibility(7)

        self.assertEqual(len(self.service.responsibility_dao.last_run_calls), 1)

    def test_missing_responsibility_is_refused(self):
        with self.assertRaises(ValueError):
            self.service.preform_responsibility(999)


class CheckForResponsibilitiesTests(unittest.TestCase):
    def test_runs_only_due_responsibilities(self):
        due = Responsibility(id=1, name="due", schedule=["morning"], last_run=None)
        not_due = Responsibility(id=2, name="later", schedule=["evening"], last_run=None)
        service = build_service([due, not_due])

        ran = []
        service.preform_responsibility = lambda rid: ran.append(rid)

        summary = service.check_for_responsibilities(now=at(8))

        self.assertEqual(ran, [1])
        self.assertEqual(summary["due"], 1)
        self.assertEqual(summary["ran"], 1)
        self.assertEqual(summary["failed"], 0)

    def test_one_failure_does_not_stop_the_rest(self):
        first = Responsibility(id=1, name="a", schedule=["morning"], last_run=None)
        second = Responsibility(id=2, name="b", schedule=["morning"], last_run=None)
        service = build_service([first, second])

        ran = []

        def flaky(rid):
            if rid == 1:
                raise RuntimeError("boom")
            ran.append(rid)

        service.preform_responsibility = flaky

        summary = service.check_for_responsibilities(now=at(8))

        self.assertEqual(ran, [2])
        self.assertEqual(summary["ran"], 1)
        self.assertEqual(summary["failed"], 1)


if __name__ == "__main__":
    unittest.main()


class CrudTests(unittest.TestCase):
    def setUp(self):
        self.service = build_service()

    def test_create_and_get(self):
        created = self.service.create_responsibility(
            name="Morning triage",
            description="Review overnight email and summarize what needs a reply.",
            schedule=["morning"],
        )
        self.assertEqual(created["name"], "Morning triage")
        self.assertEqual(created["schedule"], ["morning"])

        fetched = self.service.get_responsibility(created["id"])
        self.assertEqual(fetched["id"], created["id"])

    def test_create_requires_name_and_description(self):
        with self.assertRaises(ValueError):
            self.service.create_responsibility(name="  ", description="something")
        with self.assertRaises(ValueError):
            self.service.create_responsibility(name="Thing", description="   ")

    def test_schedule_is_normalized_and_deduped(self):
        created = self.service.create_responsibility(
            name="R",
            description="d",
            schedule=["Morning", "morning", "EVENING"],
        )
        self.assertEqual(created["schedule"], ["morning", "evening"])

    def test_bad_schedule_window_is_refused(self):
        with self.assertRaises(ValueError) as ctx:
            self.service.create_responsibility(
                name="R", description="d", schedule=["lunchtime"]
            )
        self.assertIn("lunchtime", str(ctx.exception))

    def test_unknown_project_is_refused(self):
        with self.assertRaises(ValueError):
            self.service.create_responsibility(
                name="R", description="d", project_id=999
            )

    def test_unknown_report_type_is_refused(self):
        with self.assertRaises(ValueError):
            self.service.create_responsibility(
                name="R", description="d", report_type="carrier_pigeon"
            )

    def test_undeliverable_report_type_warns_but_creates(self):
        created = self.service.create_responsibility(
            name="R", description="d", report_type="sms"
        )
        self.assertEqual(created["report_type"], "sms")
        self.assertFalse(created["report_deliverable"])
        self.assertIn("not deliverable", created["warning"])

    def test_email_report_type_has_no_warning(self):
        created = self.service.create_responsibility(
            name="R", description="d", report_type="email"
        )
        self.assertTrue(created["report_deliverable"])
        self.assertNotIn("warning", created)

    def test_update_only_changes_given_fields(self):
        created = self.service.create_responsibility(
            name="Original", description="Original brief", schedule=["night"]
        )
        updated = self.service.update_responsibility(
            created["id"], name="Renamed"
        )
        self.assertEqual(updated["name"], "Renamed")
        self.assertEqual(updated["description"], "Original brief")
        self.assertEqual(updated["schedule"], ["night"])

    def test_update_validates_schedule(self):
        created = self.service.create_responsibility(name="R", description="d")
        with self.assertRaises(ValueError):
            self.service.update_responsibility(created["id"], schedule=["whenever"])

    def test_update_missing_responsibility_is_refused(self):
        with self.assertRaises(ValueError):
            self.service.update_responsibility(999, name="x")

    def test_list_returns_all(self):
        self.service.create_responsibility(name="A", description="a")
        self.service.create_responsibility(name="B", description="b")
        self.assertEqual(len(self.service.get_all_responsibilities()), 2)

    def test_delete_removes_it(self):
        created = self.service.create_responsibility(name="R", description="d")
        result = self.service.delete_responsibility(created["id"])

        self.assertEqual(result["status"], "deleted")
        self.assertEqual(self.service.get_all_responsibilities(), [])
        with self.assertRaises(ValueError):
            self.service.get_responsibility(created["id"])

    def test_delete_missing_responsibility_is_refused(self):
        with self.assertRaises(ValueError):
            self.service.delete_responsibility(999)
