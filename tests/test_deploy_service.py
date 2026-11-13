import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.service import deploy_service
from src.service.deploy_service import DeployService


class DeployMainTests(unittest.TestCase):
    """
    Every test patches STATE_PATH to a throwaway temp file so deploy_main()
    never writes into the real logs/ directory just by being tested.
    """

    def setUp(self):
        self.service = DeployService()
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        state_patch = mock.patch.object(
            deploy_service, "STATE_PATH", Path(self._tmp_dir.name) / "last_deploy_trigger.json"
        )
        state_patch.start()
        self.addCleanup(state_patch.stop)

    def test_deploy_main_starts_the_script_in_the_background_and_returns_an_id(self):
        with mock.patch.object(
            deploy_service.supervisor,
            "start",
            return_value={"process_id": "proc_abc123", "started_at": 1.0, "note": "started"},
        ) as start:
            result = self.service.deploy_main()

        start.assert_called_once()
        command = start.call_args.kwargs.get("command", start.call_args.args[0] if start.call_args.args else None)
        self.assertIn("deploy_main.py", command)
        self.assertNotIn("--dry-run", command)
        self.assertEqual(result["deploy_id"], "proc_abc123")
        self.assertFalse(result["dry_run"])

    def test_dry_run_flag_is_passed_through_to_the_script_command(self):
        with mock.patch.object(
            deploy_service.supervisor,
            "start",
            return_value={"process_id": "proc_xyz", "started_at": 1.0},
        ) as start:
            result = self.service.deploy_main(dry_run=True)

        command = start.call_args.kwargs.get("command", start.call_args.args[0] if start.call_args.args else None)
        self.assertIn("--dry-run", command)
        self.assertTrue(result["dry_run"])

    def test_health_timeout_override_is_passed_through(self):
        with mock.patch.object(
            deploy_service.supervisor,
            "start",
            return_value={"process_id": "proc_t", "started_at": 1.0},
        ) as start:
            self.service.deploy_main(health_timeout_seconds=120)

        command = start.call_args.kwargs.get("command", start.call_args.args[0] if start.call_args.args else None)
        self.assertIn("--health-timeout 120", command)

    def test_deploy_main_records_the_deploy_id_for_later_status_checks(self):
        with mock.patch.object(
            deploy_service.supervisor,
            "start",
            return_value={"process_id": "proc_recorded", "started_at": 1.0},
        ):
            self.service.deploy_main()

        payload = json.loads(deploy_service.STATE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["deploy_id"], "proc_recorded")


class CheckDeployStatusTests(unittest.TestCase):
    def setUp(self):
        self.service = DeployService()

    def test_explicit_deploy_id_is_passed_straight_through(self):
        with mock.patch.object(
            deploy_service.supervisor, "check", return_value={"found": True, "running": True}
        ) as check:
            result = self.service.check_deploy_status(deploy_id="proc_given")

        check.assert_called_once_with("proc_given")
        self.assertEqual(result["deploy_id"], "proc_given")
        self.assertTrue(result["running"])

    def test_no_deploy_id_falls_back_to_the_last_recorded_one(self):
        with mock.patch.object(
            self.service, "_last_deploy_id", return_value="proc_last"
        ), mock.patch.object(
            deploy_service.supervisor, "check", return_value={"found": True, "running": False}
        ) as check:
            result = self.service.check_deploy_status()

        check.assert_called_once_with("proc_last")
        self.assertEqual(result["deploy_id"], "proc_last")

    def test_no_deploy_ever_triggered_reports_not_found_without_calling_supervisor(self):
        with mock.patch.object(self.service, "_last_deploy_id", return_value=None), mock.patch.object(
            deploy_service.supervisor, "check"
        ) as check:
            result = self.service.check_deploy_status()

        check.assert_not_called()
        self.assertFalse(result["found"])


if __name__ == "__main__":
    unittest.main()
