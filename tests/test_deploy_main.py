"""
Coverage for scripts/deploy_main.py's orchestration logic.

Every test here replaces DeployRunner's step methods with fakes rather than
shelling out to real git/subprocess/network calls — the thing worth testing
is the control flow (abort on failing tests, roll back on a failed restart or
a failed health check, exit codes), not whether git or uvicorn actually run.
"""

import logging
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import deploy_main  # noqa: E402


def _silent_logger() -> logging.Logger:
    logger = logging.getLogger("test.deploy_main")
    logger.handlers = [logging.NullHandler()]
    logger.propagate = False
    return logger


def _runner(**overrides) -> deploy_main.DeployRunner:
    config = deploy_main.DeployConfig()
    for key, value in overrides.pop("config", {}).items():
        setattr(config, key, value)
    runner = deploy_main.DeployRunner(config, _silent_logger())
    for name, value in overrides.items():
        setattr(runner, name, value)
    return runner


class HappyPathTests(unittest.TestCase):
    def test_successful_deploy_returns_zero_and_never_rolls_back(self):
        runner = _runner(
            get_current_commit=lambda: "abc123",
            pull_latest=lambda: "Already up to date.",
            run_tests=lambda: (True, "OK"),
            restart_services=lambda: None,
            wait_for_health=lambda: True,
            rollback=mock.Mock(),
        )

        self.assertEqual(runner.run(), 0)
        runner.rollback.assert_not_called()


class FailingTestsAbortTests(unittest.TestCase):
    def test_failing_test_suite_aborts_before_any_restart(self):
        restart = mock.Mock()
        runner = _runner(
            get_current_commit=lambda: "abc123",
            pull_latest=lambda: "",
            run_tests=lambda: (False, "FAILED (failures=1)"),
            restart_services=restart,
            wait_for_health=mock.Mock(),
            rollback=mock.Mock(),
        )

        self.assertEqual(runner.run(), 1)
        restart.assert_not_called()
        runner.wait_for_health.assert_not_called()
        runner.rollback.assert_not_called()

    def test_git_pull_failure_aborts_before_tests_or_restart(self):
        def _boom():
            raise deploy_main.DeployError("git pull failed: network unreachable")

        run_tests = mock.Mock()
        restart = mock.Mock()
        runner = _runner(
            get_current_commit=lambda: "abc123",
            pull_latest=_boom,
            run_tests=run_tests,
            restart_services=restart,
        )

        self.assertEqual(runner.run(), 1)
        run_tests.assert_not_called()
        restart.assert_not_called()


class RollbackPathTests(unittest.TestCase):
    def test_health_check_failure_triggers_rollback_and_exits_one(self):
        runner = _runner(
            get_current_commit=lambda: "abc123",
            pull_latest=lambda: "",
            run_tests=lambda: (True, "OK"),
            restart_services=lambda: None,
            wait_for_health=lambda: False,
            rollback=mock.Mock(return_value=True),
        )

        self.assertEqual(runner.run(), 1)
        runner.rollback.assert_called_once_with("abc123")

    def test_rollback_that_also_fails_health_exits_two(self):
        runner = _runner(
            get_current_commit=lambda: "abc123",
            pull_latest=lambda: "",
            run_tests=lambda: (True, "OK"),
            restart_services=lambda: None,
            wait_for_health=lambda: False,
            rollback=mock.Mock(return_value=False),
        )

        self.assertEqual(runner.run(), 2)

    def test_restart_exception_triggers_rollback(self):
        runner = _runner(
            get_current_commit=lambda: "abc123",
            pull_latest=lambda: "",
            run_tests=lambda: (True, "OK"),
            restart_services=mock.Mock(side_effect=RuntimeError("port never freed")),
            rollback=mock.Mock(return_value=True),
        )

        self.assertEqual(runner.run(), 1)
        runner.rollback.assert_called_once_with("abc123")

    def test_rollback_method_itself_restarts_and_rechecks_health(self):
        """rollback() is exercised directly: reset --hard, restart, re-check health."""
        config = deploy_main.DeployConfig()
        runner = deploy_main.DeployRunner(config, _silent_logger())

        with mock.patch.object(deploy_main, "git_reset_hard") as reset_hard, mock.patch.object(
            runner, "restart_services"
        ) as restart, mock.patch.object(runner, "wait_for_health", return_value=True) as health:
            result = runner.rollback("deadbeef")

        reset_hard.assert_called_once_with(config.repo_root, "deadbeef")
        restart.assert_called_once()
        health.assert_called_once()
        self.assertTrue(result)


class DryRunTests(unittest.TestCase):
    def test_dry_run_runs_tests_but_never_pulls_or_restarts(self):
        pull = mock.Mock()
        restart = mock.Mock()
        health = mock.Mock()
        runner = _runner(
            config={"dry_run": True},
            get_current_commit=lambda: "abc123",
            pull_latest=pull,
            run_tests=lambda: (True, "OK"),
            restart_services=restart,
            wait_for_health=health,
        )

        self.assertEqual(runner.run(), 0)
        pull.assert_not_called()
        restart.assert_not_called()
        health.assert_not_called()

    def test_dry_run_with_failing_tests_still_reports_failure(self):
        runner = _runner(
            config={"dry_run": True},
            get_current_commit=lambda: "abc123",
            run_tests=lambda: (False, "FAILED"),
        )

        self.assertEqual(runner.run(), 1)


class HealthTimeoutTests(unittest.TestCase):
    def test_wait_for_health_returns_false_after_timeout_when_never_healthy(self):
        with mock.patch.object(deploy_main, "check_health_once", return_value=False):
            healthy = deploy_main.wait_for_health(
                "http://127.0.0.1:8000/health", timeout_seconds=0.05, interval_seconds=0.01
            )
        self.assertFalse(healthy)

    def test_wait_for_health_returns_true_as_soon_as_healthy(self):
        calls = {"n": 0}

        def fake_check(url):
            calls["n"] += 1
            return calls["n"] >= 3

        with mock.patch.object(deploy_main, "check_health_once", side_effect=fake_check):
            healthy = deploy_main.wait_for_health(
                "http://127.0.0.1:8000/health", timeout_seconds=5, interval_seconds=0.01
            )
        self.assertTrue(healthy)
        self.assertGreaterEqual(calls["n"], 3)


class StopPidIsNeverATreeKillTests(unittest.TestCase):
    """
    Regression coverage for the self-kill hazard: deploy_main.py can be a
    descendant of the API process it is told to stop, so stopping that
    process must never be a tree-kill (which would walk down to this
    script's own pid).
    """

    def test_windows_stop_uses_taskkill_without_tree_flag(self):
        with mock.patch.object(deploy_main.supervisor, "IS_WINDOWS", True), mock.patch.object(
            deploy_main.subprocess, "run"
        ) as run:
            deploy_main.stop_pid(4242)

        run.assert_called_once()
        args = run.call_args.args[0]
        self.assertIn("/PID", args)
        self.assertIn("4242", args)
        self.assertNotIn("/T", args)

    def test_posix_stop_sends_sigterm_to_exact_pid_only(self):
        with mock.patch.object(deploy_main.supervisor, "IS_WINDOWS", False), mock.patch.object(
            deploy_main.os, "kill"
        ) as kill:
            deploy_main.stop_pid(4242)

        kill.assert_called_once_with(4242, deploy_main.signal.SIGTERM)

    def test_none_pid_is_a_no_op(self):
        with mock.patch.object(deploy_main.subprocess, "run") as run, mock.patch.object(
            deploy_main.os, "kill"
        ) as kill:
            deploy_main.stop_pid(None)

        run.assert_not_called()
        kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
