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


class StopPidTreeKillTests(unittest.TestCase):
    """
    stop_pid now kills the whole process tree by default — the API spawns
    multiprocessing.spawn children (some of which inherit the listening
    socket), and killing just the parent left those children running stale
    code after a deploy. The one thing it must never do is reach this
    script's own pid or an ancestor of it; see SelfKillHazardTests below.
    """

    def test_windows_stop_uses_taskkill_with_tree_flag(self):
        with mock.patch.object(deploy_main.supervisor, "IS_WINDOWS", True), mock.patch.object(
            deploy_main, "_protected_pids", return_value=set()
        ), mock.patch.object(deploy_main.subprocess, "run") as run:
            deploy_main.stop_pid(4242)

        run.assert_called_once()
        args = run.call_args.args[0]
        self.assertIn("/PID", args)
        self.assertIn("4242", args)
        self.assertIn("/T", args)
        self.assertIn("/F", args)

    def test_windows_stop_never_raises_when_process_already_gone(self):
        with mock.patch.object(deploy_main.supervisor, "IS_WINDOWS", True), mock.patch.object(
            deploy_main, "_protected_pids", return_value=set()
        ), mock.patch.object(
            deploy_main.subprocess,
            "run",
            return_value=mock.Mock(returncode=128, stdout=b"", stderr=b"not found"),
        ):
            deploy_main.stop_pid(4242)  # must not raise

    def test_posix_stop_uses_process_group_tree_kill(self):
        with mock.patch.object(deploy_main.supervisor, "IS_WINDOWS", False), mock.patch.object(
            deploy_main, "_protected_pids", return_value=set()
        ), mock.patch.object(deploy_main.supervisor, "kill_tree") as kill_tree:
            deploy_main.stop_pid(4242)

        kill_tree.assert_called_once_with(None, pid=4242)

    def test_posix_stop_falls_back_to_sigterm_if_tree_kill_errors(self):
        with mock.patch.object(deploy_main.supervisor, "IS_WINDOWS", False), mock.patch.object(
            deploy_main, "_protected_pids", return_value=set()
        ), mock.patch.object(
            deploy_main.supervisor, "kill_tree", side_effect=RuntimeError("boom")
        ), mock.patch.object(deploy_main.os, "kill") as kill:
            deploy_main.stop_pid(4242)  # must not raise

        kill.assert_called_once_with(4242, deploy_main.signal.SIGTERM)

    def test_none_pid_is_a_no_op(self):
        with mock.patch.object(deploy_main.subprocess, "run") as run, mock.patch.object(
            deploy_main.os, "kill"
        ) as kill:
            deploy_main.stop_pid(None)

        run.assert_not_called()
        kill.assert_not_called()


class SelfKillHazardTests(unittest.TestCase):
    """
    Regression coverage for the self-kill hazard: deploy_main.py can be a
    descendant of the API process it is told to stop, so a tree-kill must
    never reach this script's own pid or any pid upstream of it.
    """

    def test_stop_pid_refuses_to_kill_its_own_pid(self):
        own_pid = deploy_main.os.getpid()
        with mock.patch.object(
            deploy_main, "_protected_pids", return_value={own_pid}
        ), mock.patch.object(deploy_main.subprocess, "run") as run, mock.patch.object(
            deploy_main.supervisor, "kill_tree"
        ) as kill_tree:
            deploy_main.stop_pid(own_pid)

        run.assert_not_called()
        kill_tree.assert_not_called()

    def test_stop_pid_refuses_to_kill_an_ancestor_pid(self):
        ancestor_pid = 999
        with mock.patch.object(
            deploy_main, "_protected_pids", return_value={deploy_main.os.getpid(), ancestor_pid}
        ), mock.patch.object(deploy_main.supervisor, "IS_WINDOWS", True), mock.patch.object(
            deploy_main.subprocess, "run"
        ) as run:
            deploy_main.stop_pid(ancestor_pid)

        run.assert_not_called()

    def test_restart_services_never_targets_its_own_pid(self):
        """
        Even if the port/worker lookups (mocked here as broken) turn up this
        script's own pid, restart_services must never try to kill it.
        """
        own_pid = deploy_main.os.getpid()
        runner = _runner()

        with mock.patch.object(
            deploy_main, "_protected_pids", return_value={own_pid}
        ), mock.patch.object(
            deploy_main, "find_pid_on_port", side_effect=[own_pid, None]
        ), mock.patch.object(
            deploy_main, "find_all_pids_on_port", return_value=[own_pid]
        ), mock.patch.object(
            deploy_main, "find_worker_pid", return_value=own_pid
        ), mock.patch.object(
            deploy_main, "find_all_worker_pids", return_value=[own_pid]
        ), mock.patch.object(deploy_main, "start_api", return_value={}), mock.patch.object(
            deploy_main, "start_worker", return_value={}
        ), mock.patch.object(deploy_main.subprocess, "run") as run, mock.patch.object(
            deploy_main.os, "kill"
        ) as kill, mock.patch.object(deploy_main.time, "sleep"):
            runner.restart_services()

        run.assert_not_called()
        kill.assert_not_called()


class LeftoverSweepTests(unittest.TestCase):
    """
    restart_services must sweep for and stop *every* leftover pid still
    listening on the API port or still running worker.py — not just the
    first one `find_pid_on_port` / `find_worker_pid` happen to return — since
    `uv run` and multiprocessing.spawn can leave several behind.
    """

    def test_multiple_listeners_on_the_port_all_get_stopped(self):
        runner = _runner()
        stopped: list[int] = []

        with mock.patch.object(deploy_main, "find_pid_on_port", return_value=None), mock.patch.object(
            deploy_main, "find_worker_pid", return_value=None
        ), mock.patch.object(
            deploy_main,
            "find_all_pids_on_port",
            side_effect=[[111, 222, 333], []],
        ), mock.patch.object(
            deploy_main, "find_all_worker_pids", return_value=[]
        ), mock.patch.object(
            deploy_main, "stop_pid", side_effect=lambda pid, **_: stopped.append(pid)
        ), mock.patch.object(deploy_main, "start_api", return_value={}), mock.patch.object(
            deploy_main, "start_worker", return_value={}
        ), mock.patch.object(deploy_main.time, "sleep"):
            runner.restart_services()

        self.assertEqual(sorted(stopped), [111, 222, 333])

    def test_multiple_worker_pids_all_get_stopped(self):
        runner = _runner()
        stopped: list[int] = []

        with mock.patch.object(deploy_main, "find_pid_on_port", return_value=None), mock.patch.object(
            deploy_main, "find_worker_pid", return_value=None
        ), mock.patch.object(
            deploy_main, "find_all_pids_on_port", return_value=[]
        ), mock.patch.object(
            deploy_main,
            "find_all_worker_pids",
            side_effect=[[444, 555], []],
        ), mock.patch.object(
            deploy_main, "stop_pid", side_effect=lambda pid, **_: stopped.append(pid)
        ), mock.patch.object(deploy_main, "start_api", return_value={}), mock.patch.object(
            deploy_main, "start_worker", return_value={}
        ), mock.patch.object(deploy_main.time, "sleep"):
            runner.restart_services()

        self.assertEqual(sorted(stopped), [444, 555])

    def test_sweep_retries_until_the_port_is_free(self):
        runner = _runner()

        with mock.patch.object(deploy_main, "find_pid_on_port", return_value=None), mock.patch.object(
            deploy_main, "find_worker_pid", return_value=None
        ), mock.patch.object(
            deploy_main,
            "find_all_pids_on_port",
            side_effect=[[111], [111], []],
        ), mock.patch.object(
            deploy_main, "find_all_worker_pids", return_value=[]
        ), mock.patch.object(deploy_main, "stop_pid") as stop_pid, mock.patch.object(
            deploy_main, "start_api", return_value={}
        ), mock.patch.object(deploy_main, "start_worker", return_value={}), mock.patch.object(
            deploy_main.time, "sleep"
        ):
            runner.restart_services()

        self.assertEqual(stop_pid.call_count, 2)


if __name__ == "__main__":
    unittest.main()
