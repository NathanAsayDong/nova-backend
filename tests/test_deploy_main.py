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
            deploy_main.subprocess, "Popen"
        ) as popen, mock.patch.object(deploy_main.os, "kill") as kill, mock.patch.object(
            deploy_main.time, "sleep"
        ):
            runner.restart_services()

        run.assert_not_called()
        kill.assert_not_called()
        # This script's own pid is never a "stale ancestor" to hand off —
        # only genuine ancestors are, so no helper should be spawned either.
        popen.assert_not_called()


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


class SweepHandsOffStaleAncestorsTests(unittest.TestCase):
    """
    `_sweep_leftovers` must not just log-and-abandon a leftover pid that is
    protected because it's an ancestor of this script (the 2026-11-16 prod
    bug: a stale old API stayed on port 8000 next to the new one). It should
    still kill every non-ancestor leftover itself, and hand the ancestor
    pid(s) off to the detached helper exactly once.
    """

    def test_ancestor_leftover_is_handed_to_helper_not_silently_dropped(self):
        runner = _runner()
        ancestor_pid = 999
        own_pid = deploy_main.os.getpid()
        spawn = mock.Mock()

        with mock.patch.object(
            deploy_main, "_protected_pids", return_value={own_pid, ancestor_pid}
        ), mock.patch.object(
            deploy_main, "find_all_pids_on_port", return_value=[ancestor_pid]
        ), mock.patch.object(
            deploy_main, "find_all_worker_pids", return_value=[]
        ), mock.patch.object(deploy_main, "stop_pid") as stop_pid, mock.patch.object(
            runner, "_spawn_stale_ancestor_helper", spawn
        ), mock.patch.object(deploy_main.time, "sleep"):
            runner._sweep_leftovers(8000)

        # The ancestor pid must never be passed to stop_pid directly from the
        # sweep loop (stop_pid would just silently refuse it anyway, but the
        # point is the sweep doesn't treat this as "handled").
        stop_pid.assert_not_called()
        spawn.assert_called_once_with([ancestor_pid])

    def test_mixed_leftovers_kills_killable_and_hands_off_ancestor(self):
        runner = _runner()
        ancestor_pid = 999
        killable_pid = 111
        own_pid = deploy_main.os.getpid()
        spawn = mock.Mock()

        with mock.patch.object(
            deploy_main, "_protected_pids", return_value={own_pid, ancestor_pid}
        ), mock.patch.object(
            deploy_main,
            "find_all_pids_on_port",
            side_effect=[[ancestor_pid, killable_pid], [ancestor_pid]],
        ), mock.patch.object(
            deploy_main, "find_all_worker_pids", return_value=[]
        ), mock.patch.object(deploy_main, "stop_pid") as stop_pid, mock.patch.object(
            runner, "_spawn_stale_ancestor_helper", spawn
        ), mock.patch.object(deploy_main.time, "sleep"):
            runner._sweep_leftovers(8000)

        stop_pid.assert_called_once_with(killable_pid)
        spawn.assert_called_once_with([ancestor_pid])

    def test_no_ancestor_leftovers_never_spawns_helper(self):
        runner = _runner()
        spawn = mock.Mock()

        with mock.patch.object(
            deploy_main, "_protected_pids", return_value={deploy_main.os.getpid()}
        ), mock.patch.object(
            deploy_main, "find_all_pids_on_port", side_effect=[[111], []]
        ), mock.patch.object(
            deploy_main, "find_all_worker_pids", return_value=[]
        ), mock.patch.object(deploy_main, "stop_pid") as stop_pid, mock.patch.object(
            runner, "_spawn_stale_ancestor_helper", spawn
        ), mock.patch.object(deploy_main.time, "sleep"):
            runner._sweep_leftovers(8000)

        stop_pid.assert_called_once_with(111)
        spawn.assert_not_called()

    def test_ancestor_worker_pid_is_also_handed_off(self):
        """Ancestor protection applies to worker.py pids too, not just port listeners."""
        runner = _runner()
        ancestor_pid = 777
        own_pid = deploy_main.os.getpid()
        spawn = mock.Mock()

        with mock.patch.object(
            deploy_main, "_protected_pids", return_value={own_pid, ancestor_pid}
        ), mock.patch.object(
            deploy_main, "find_all_pids_on_port", return_value=[]
        ), mock.patch.object(
            deploy_main, "find_all_worker_pids", return_value=[ancestor_pid]
        ), mock.patch.object(deploy_main, "stop_pid") as stop_pid, mock.patch.object(
            runner, "_spawn_stale_ancestor_helper", spawn
        ), mock.patch.object(deploy_main.time, "sleep"):
            runner._sweep_leftovers(8000)

        stop_pid.assert_not_called()
        spawn.assert_called_once_with([ancestor_pid])

    def test_restart_services_does_not_raise_when_ancestor_found(self):
        """
        The overarching requirement: a stale protected ancestor must never
        fail the deploy. restart_services (and therefore run()) must sail
        through even though the port never fully clears on its own.
        """
        runner = _runner()
        ancestor_pid = 999
        own_pid = deploy_main.os.getpid()

        with mock.patch.object(
            deploy_main, "_protected_pids", return_value={own_pid, ancestor_pid}
        ), mock.patch.object(deploy_main, "find_pid_on_port", return_value=None), mock.patch.object(
            deploy_main, "find_worker_pid", return_value=None
        ), mock.patch.object(
            deploy_main, "find_all_pids_on_port", return_value=[ancestor_pid]
        ), mock.patch.object(
            deploy_main, "find_all_worker_pids", return_value=[]
        ), mock.patch.object(deploy_main, "stop_pid"), mock.patch.object(
            deploy_main, "spawn_stale_ancestor_helper"
        ) as spawn, mock.patch.object(
            deploy_main, "start_api", return_value={}
        ), mock.patch.object(deploy_main, "start_worker", return_value={}), mock.patch.object(
            deploy_main.time, "sleep"
        ):
            runner.restart_services()  # must not raise

        spawn.assert_called_once()
        self.assertEqual(spawn.call_args.kwargs["ancestor_pids"], [ancestor_pid])


class SpawnStaleAncestorHelperTests(unittest.TestCase):
    """
    `spawn_stale_ancestor_helper` must re-invoke this script detached: no
    inherited stdio, its own session/process group on POSIX, and
    DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP with no inherited handles on
    Windows — specifically so the helper is not a descendant of the
    ancestor tree it is about to kill, and survives this script exiting.
    """

    def test_posix_uses_new_session_and_no_inherited_stdio(self):
        with mock.patch.object(deploy_main.supervisor, "IS_WINDOWS", False), mock.patch.object(
            deploy_main.subprocess, "Popen"
        ) as popen:
            deploy_main.spawn_stale_ancestor_helper(
                ancestor_pids=[999],
                deploy_pid=12345,
                port=8000,
                health_url="http://127.0.0.1:8000/health",
                repo_root=Path("/repo"),
                max_wait_seconds=300,
            )

        popen.assert_called_once()
        args, kwargs = popen.call_args
        argv = args[0]
        self.assertIn("--helper-mode", argv)
        self.assertIn("--deploy-pid", argv)
        self.assertIn("12345", argv)
        self.assertIn("--ancestor-pids", argv)
        self.assertIn("999", argv)
        self.assertTrue(kwargs.get("start_new_session"))
        self.assertEqual(kwargs.get("stdin"), deploy_main.subprocess.DEVNULL)
        self.assertEqual(kwargs.get("stdout"), deploy_main.subprocess.DEVNULL)
        self.assertEqual(kwargs.get("stderr"), deploy_main.subprocess.DEVNULL)
        self.assertTrue(kwargs.get("close_fds"))
        self.assertNotIn("creationflags", kwargs)

    def test_windows_uses_detached_process_and_new_process_group(self):
        with mock.patch.object(deploy_main.supervisor, "IS_WINDOWS", True), mock.patch.object(
            deploy_main.subprocess, "Popen"
        ) as popen:
            deploy_main.spawn_stale_ancestor_helper(
                ancestor_pids=[999, 1000],
                deploy_pid=12345,
                port=8000,
                health_url="http://127.0.0.1:8000/health",
                repo_root=Path("/repo"),
                max_wait_seconds=300,
            )

        popen.assert_called_once()
        _, kwargs = popen.call_args
        self.assertNotIn("start_new_session", kwargs)
        self.assertIn("creationflags", kwargs)
        expected = getattr(deploy_main.subprocess, "DETACHED_PROCESS", 0x00000008) | getattr(
            deploy_main.subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200
        )
        self.assertEqual(kwargs["creationflags"], expected)

    def test_multiple_ancestor_pids_joined_in_argv(self):
        with mock.patch.object(deploy_main.supervisor, "IS_WINDOWS", False), mock.patch.object(
            deploy_main.subprocess, "Popen"
        ) as popen:
            deploy_main.spawn_stale_ancestor_helper(
                ancestor_pids=[111, 222],
                deploy_pid=1,
                port=8000,
                health_url="http://127.0.0.1:8000/health",
                repo_root=Path("/repo"),
                max_wait_seconds=300,
            )

        argv = popen.call_args.args[0]
        idx = argv.index("--ancestor-pids")
        self.assertEqual(argv[idx + 1], "111,222")


class SpawnStaleAncestorHelperTimingTests(unittest.TestCase):
    """_spawn_stale_ancestor_helper (the DeployRunner method) scales its wait
    floor off --health-timeout so a rollback's extra restart+health cycle
    doesn't get raced, but never drops below the documented minimum."""

    def test_wait_floor_is_the_module_minimum_for_default_health_timeout(self):
        runner = _runner()
        with mock.patch.object(deploy_main, "spawn_stale_ancestor_helper") as spawn:
            runner._spawn_stale_ancestor_helper([999])

        spawn.assert_called_once()
        self.assertEqual(
            spawn.call_args.kwargs["max_wait_seconds"],
            deploy_main.STALE_ANCESTOR_HELPER_MIN_WAIT_SECONDS,
        )

    def test_wait_floor_scales_with_a_long_health_timeout(self):
        runner = _runner(config={"health_timeout": 200})
        with mock.patch.object(deploy_main, "spawn_stale_ancestor_helper") as spawn:
            runner._spawn_stale_ancestor_helper([999])

        spawn.assert_called_once()
        self.assertEqual(
            spawn.call_args.kwargs["max_wait_seconds"],
            200 * deploy_main.STALE_ANCESTOR_HELPER_WAIT_MULTIPLIER,
        )

    def test_spawn_failure_is_logged_and_never_raises(self):
        """Spawning the helper must never fail the deploy itself."""
        runner = _runner()
        with mock.patch.object(
            deploy_main, "spawn_stale_ancestor_helper", side_effect=OSError("boom")
        ):
            runner._spawn_stale_ancestor_helper([999])  # must not raise


class WaitForPidExitTests(unittest.TestCase):
    def test_returns_true_once_pid_is_gone(self):
        calls = {"n": 0}

        def fake_alive(pid):
            calls["n"] += 1
            return calls["n"] < 3

        with mock.patch.object(
            deploy_main.supervisor, "pid_alive", side_effect=fake_alive
        ), mock.patch.object(deploy_main.time, "sleep"):
            result = deploy_main._wait_for_pid_exit(4242, timeout_seconds=10, poll_interval=0.01)

        self.assertTrue(result)
        self.assertGreaterEqual(calls["n"], 3)

    def test_returns_false_on_timeout_while_pid_still_alive(self):
        with mock.patch.object(
            deploy_main.supervisor, "pid_alive", return_value=True
        ), mock.patch.object(deploy_main.time, "monotonic", side_effect=[0, 0, 100]):
            result = deploy_main._wait_for_pid_exit(4242, timeout_seconds=5, poll_interval=0.01)

        self.assertFalse(result)


class EnsureSingleHealthyApiTests(unittest.TestCase):
    def test_already_exactly_one_healthy_pid_is_a_no_op(self):
        logger = _silent_logger()
        with mock.patch.object(
            deploy_main, "find_all_pids_on_port", return_value=[555]
        ), mock.patch.object(
            deploy_main, "check_health_once", return_value=True
        ), mock.patch.object(deploy_main, "start_api") as start_api, mock.patch.object(
            deploy_main, "stop_pid"
        ) as stop_pid, mock.patch.object(deploy_main.time, "sleep"):
            result = deploy_main._ensure_single_healthy_api(
                8000, "http://127.0.0.1:8000/health", Path("/repo"), logger
            )

        self.assertTrue(result)
        start_api.assert_not_called()
        stop_pid.assert_not_called()

    def test_restarts_when_nothing_is_listening(self):
        """
        Nothing is on the port on the first pass (len != 1, so the health
        check is never consulted that pass — short-circuited); a fresh API
        starts, and by the second pass it's up and healthy.
        """
        logger = _silent_logger()
        with mock.patch.object(
            deploy_main, "find_all_pids_on_port", side_effect=[[], [777]]
        ), mock.patch.object(
            deploy_main, "check_health_once", side_effect=[True]
        ), mock.patch.object(deploy_main, "start_api", return_value={}) as start_api, mock.patch.object(
            deploy_main, "stop_pid"
        ) as stop_pid, mock.patch.object(deploy_main.time, "sleep"):
            result = deploy_main._ensure_single_healthy_api(
                8000, "http://127.0.0.1:8000/health", Path("/repo"), logger
            )

        self.assertTrue(result)
        start_api.assert_called_once_with(Path("/repo"), 8000)
        stop_pid.assert_not_called()

    def test_stops_duplicates_and_restarts_fresh(self):
        """
        Two pids on the port (len != 1, health check short-circuited this
        pass) get stopped and a fresh API started; by the next pass there's
        exactly one healthy pid.
        """
        logger = _silent_logger()
        stopped: list[int] = []
        with mock.patch.object(
            deploy_main,
            "find_all_pids_on_port",
            side_effect=[[111, 222], [333]],
        ), mock.patch.object(
            deploy_main, "check_health_once", side_effect=[True]
        ), mock.patch.object(
            deploy_main, "stop_pid", side_effect=lambda pid, **_: stopped.append(pid)
        ), mock.patch.object(deploy_main, "start_api", return_value={}) as start_api, mock.patch.object(
            deploy_main.time, "sleep"
        ):
            result = deploy_main._ensure_single_healthy_api(
                8000, "http://127.0.0.1:8000/health", Path("/repo"), logger
            )

        self.assertTrue(result)
        self.assertEqual(sorted(stopped), [111, 222])
        start_api.assert_called_once()

    def test_never_calls_stop_pid_on_empty_port(self):
        """When nothing is listening there is nothing to stop — only to start."""
        logger = _silent_logger()
        with mock.patch.object(
            deploy_main, "find_all_pids_on_port", return_value=[]
        ), mock.patch.object(
            deploy_main, "check_health_once", return_value=False
        ), mock.patch.object(deploy_main, "start_api", return_value={}), mock.patch.object(
            deploy_main, "stop_pid"
        ) as stop_pid, mock.patch.object(deploy_main.time, "sleep"):
            deploy_main._ensure_single_healthy_api(
                8000, "http://127.0.0.1:8000/health", Path("/repo"), logger, attempts=2
            )

        stop_pid.assert_not_called()

    def test_gives_up_after_exhausting_attempts(self):
        logger = _silent_logger()
        with mock.patch.object(
            deploy_main, "find_all_pids_on_port", return_value=[111, 222]
        ), mock.patch.object(
            deploy_main, "check_health_once", return_value=False
        ), mock.patch.object(deploy_main, "start_api", return_value={}), mock.patch.object(
            deploy_main, "stop_pid"
        ), mock.patch.object(deploy_main.time, "sleep"):
            result = deploy_main._ensure_single_healthy_api(
                8000, "http://127.0.0.1:8000/health", Path("/repo"), logger, attempts=2
            )

        self.assertFalse(result)


class RunStaleAncestorHelperTests(unittest.TestCase):
    """
    End-to-end (but fully mocked) coverage of the detached helper's own
    entry point: wait for the deploy script to exit, then and only then
    tree-kill the ancestor pid(s), then confirm a single healthy API.
    """

    def test_full_success_path_kills_ancestors_after_deploy_exits(self):
        logger = _silent_logger()
        killed: list[int] = []

        with mock.patch.object(
            deploy_main, "_wait_for_pid_exit", return_value=True
        ) as wait_exit, mock.patch.object(
            deploy_main, "stop_pid", side_effect=lambda pid, **_: killed.append(pid)
        ), mock.patch.object(
            deploy_main, "_ensure_single_healthy_api", return_value=True
        ) as ensure, mock.patch.object(deploy_main.time, "sleep"):
            code = deploy_main.run_stale_ancestor_helper(
                deploy_pid=12345,
                ancestor_pids=[999, 1000],
                port=8000,
                health_url="http://127.0.0.1:8000/health",
                repo_root=Path("/repo"),
                max_wait_seconds=300,
                logger=logger,
            )

        self.assertEqual(code, 0)
        wait_exit.assert_called_once_with(12345, 300)
        self.assertEqual(sorted(killed), [999, 1000])
        ensure.assert_called_once()

    def test_never_kills_ancestors_if_deploy_script_never_exits(self):
        """
        The core safety property: if the deploy script is still alive (still
        possibly a descendant of the ancestor), the helper must not touch
        the ancestor tree at all.
        """
        logger = _silent_logger()

        with mock.patch.object(
            deploy_main, "_wait_for_pid_exit", return_value=False
        ), mock.patch.object(deploy_main, "stop_pid") as stop_pid, mock.patch.object(
            deploy_main, "_ensure_single_healthy_api"
        ) as ensure:
            code = deploy_main.run_stale_ancestor_helper(
                deploy_pid=12345,
                ancestor_pids=[999],
                port=8000,
                health_url="http://127.0.0.1:8000/health",
                repo_root=Path("/repo"),
                max_wait_seconds=300,
                logger=logger,
            )

        self.assertEqual(code, 1)
        stop_pid.assert_not_called()
        ensure.assert_not_called()

    def test_returns_one_when_final_health_check_fails(self):
        logger = _silent_logger()

        with mock.patch.object(
            deploy_main, "_wait_for_pid_exit", return_value=True
        ), mock.patch.object(deploy_main, "stop_pid"), mock.patch.object(
            deploy_main, "_ensure_single_healthy_api", return_value=False
        ), mock.patch.object(deploy_main.time, "sleep"):
            code = deploy_main.run_stale_ancestor_helper(
                deploy_pid=12345,
                ancestor_pids=[999],
                port=8000,
                health_url="http://127.0.0.1:8000/health",
                repo_root=Path("/repo"),
                max_wait_seconds=300,
                logger=logger,
            )

        self.assertEqual(code, 1)

    def test_helper_never_targets_its_own_pid(self):
        """
        Belt-and-suspenders regression: stop_pid re-derives the *current*
        process's protected set every call, so even if an ancestor pid list
        somehow included this helper's own pid, stop_pid must refuse it.
        """
        logger = _silent_logger()
        own_pid = deploy_main.os.getpid()

        with mock.patch.object(
            deploy_main, "_wait_for_pid_exit", return_value=True
        ), mock.patch.object(deploy_main.subprocess, "run") as run, mock.patch.object(
            deploy_main.supervisor, "kill_tree"
        ) as kill_tree, mock.patch.object(
            deploy_main, "_protected_pids", return_value={own_pid}
        ), mock.patch.object(
            deploy_main, "_ensure_single_healthy_api", return_value=True
        ), mock.patch.object(deploy_main.time, "sleep"):
            deploy_main.run_stale_ancestor_helper(
                deploy_pid=12345,
                ancestor_pids=[own_pid],
                port=8000,
                health_url="http://127.0.0.1:8000/health",
                repo_root=Path("/repo"),
                max_wait_seconds=300,
                logger=logger,
            )

        run.assert_not_called()
        kill_tree.assert_not_called()


class HelperModeCliTests(unittest.TestCase):
    """main() must dispatch --helper-mode to run_stale_ancestor_helper with
    the parsed args, write its own log file, and never touch last_deploy.json
    or the normal DeployRunner path."""

    def test_helper_mode_dispatches_with_parsed_args(self):
        with mock.patch.object(
            deploy_main, "run_stale_ancestor_helper", return_value=0
        ) as run_helper, mock.patch.object(deploy_main, "build_logger", return_value=_silent_logger()):
            code = deploy_main.main(
                [
                    "--helper-mode",
                    "--deploy-pid",
                    "4242",
                    "--ancestor-pids",
                    "111,222",
                    "--port",
                    "9000",
                    "--health-url",
                    "http://127.0.0.1:9000/health",
                    "--repo-root",
                    "/repo",
                    "--max-wait-seconds",
                    "120",
                ]
            )

        self.assertEqual(code, 0)
        run_helper.assert_called_once()
        kwargs = run_helper.call_args.kwargs
        self.assertEqual(kwargs["deploy_pid"], 4242)
        self.assertEqual(kwargs["ancestor_pids"], [111, 222])
        self.assertEqual(kwargs["port"], 9000)
        self.assertEqual(kwargs["max_wait_seconds"], 120)

    def test_helper_mode_crash_is_caught_and_returns_two(self):
        with mock.patch.object(
            deploy_main, "run_stale_ancestor_helper", side_effect=RuntimeError("boom")
        ), mock.patch.object(deploy_main, "build_logger", return_value=_silent_logger()):
            code = deploy_main.main(
                ["--helper-mode", "--deploy-pid", "1", "--ancestor-pids", "999"]
            )

        self.assertEqual(code, 2)

    def test_helper_mode_empty_ancestor_pids_parses_to_empty_list(self):
        with mock.patch.object(
            deploy_main, "run_stale_ancestor_helper", return_value=0
        ) as run_helper, mock.patch.object(deploy_main, "build_logger", return_value=_silent_logger()):
            deploy_main.main(["--helper-mode", "--deploy-pid", "1", "--ancestor-pids", ""])

        self.assertEqual(run_helper.call_args.kwargs["ancestor_pids"], [])


if __name__ == "__main__":
    unittest.main()
