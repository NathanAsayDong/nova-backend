"""
Coverage for long-lived commands — the ones that never return.

Every test here is a regression test for the same original bug. Both shell
tools waited on output pipes, and a pipe closes when its LAST writer closes
it, so a command that spawned a dev server held the tool for its entire
timeout however hard the model tried to detach it. Then the timeout killed
the shell and not the process group, so the server survived: running, holding
its port, and invisible to Nova, which had just been told the command failed.

The assertions worth keeping honest are therefore about timing (the call
returns in well under its timeout), about the tree (nothing survives a kill),
and about truthfulness (a server that died on import is reported as a crash,
not as a healthy background process).
"""

import os
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

from src.service import process_supervisor as supervisor
from src.service.command_line_service import CommandLineService

# A port high enough to be unused, low enough to be memorable in a failure.
_PORT = 8791


class ClassificationTests(unittest.TestCase):
    """Which commands are recognised as never-ending, and which are not."""

    def test_the_command_that_prompted_all_of_this(self):
        """`cd <dir> && start uv run main.py`, exactly as Nova wrote it."""
        command = r"cd C:\Users\natha\nova-backend && start uv run main.py"
        mode, reason = supervisor.classify(command)

        self.assertEqual(mode, "background")
        self.assertIn("start", reason)
        # `start` sat after `&&`, not at the beginning: an anchored pattern
        # left it in the command, where it is a Windows builtin that opens a
        # console nobody ever reads and, on the Mac, is not a program at all.
        self.assertEqual(
            supervisor.strip_detach_syntax(command),
            r"cd C:\Users\natha\nova-backend && uv run main.py",
        )

    def test_hand_rolled_detach_syntax_is_recognised_and_removed(self):
        for command, expected in [
            ("start uv run main.py", "uv run main.py"),
            ("uvicorn main:app &", "uvicorn main:app"),
            ("cd /x && start npm run dev", "cd /x && npm run dev"),
        ]:
            with self.subTest(command=command):
                self.assertEqual(supervisor.classify(command)[0], "background")
                self.assertEqual(supervisor.strip_detach_syntax(command), expected)

    def test_servers_and_watchers_are_background(self):
        for command in [
            "uv run main.py",
            "python main.py",
            "uv run uvicorn main:app --reload",
            "npm run dev",
            "tail -f app.log",
            "docker compose up",
            "python3 -m http.server 8000",
        ]:
            with self.subTest(command=command):
                self.assertEqual(supervisor.classify(command)[0], "background")

    def test_commands_that_finish_are_left_alone(self):
        for command in [
            "pytest -q",
            "git status",
            "docker compose up -d",          # -d already returns
            "echo restart",                 # 'start' inside a word
            "ls | grep dev",
        ]:
            with self.subTest(command=command):
                self.assertEqual(supervisor.classify(command)[0], "foreground")

    def test_reading_a_file_is_not_running_it(self):
        """
        A program name is as likely to be an argument as a command.

        Without the inspector guard, `cat main.py` matched the rule meant for
        `uv run main.py` — and answering a file read with a process handle is
        its own kind of broken.
        """
        for command in ["cat main.py", "grep -n uvicorn main.py", "git log --oneline"]:
            with self.subTest(command=command):
                self.assertEqual(supervisor.classify(command)[0], "foreground")


class ForegroundTests(unittest.TestCase):
    """The ordinary path, which must keep its exact result shape."""

    def setUp(self):
        self.service = CommandLineService()

    def test_result_shape_is_unchanged(self):
        result = self.service.run_terminal_command("echo out; echo err >&2; exit 7")

        self.assertEqual(result["exit_code"], 7)
        self.assertEqual(result["stdout"], "out\n")
        self.assertEqual(result["stderr"], "err\n")
        self.assertFalse(result["timed_out"])

    def test_a_detached_child_no_longer_holds_the_call_open(self):
        """
        The original bug, at its smallest.

        `subprocess.run(..., capture_output=True)` on a command that leaves a
        child running blocked until the timeout, because the child inherited
        the pipe. Writing to files instead means the call returns when the
        command exits.
        """
        started = time.monotonic()
        result = self.service.run_terminal_command(
            "(sleep 30 &) ; echo done", timeout_seconds=10
        )
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 5, "the inherited output handle is blocking again")
        self.assertFalse(result["timed_out"])
        self.assertEqual(result["stdout"].strip(), "done")

    def test_a_timeout_returns_the_output_produced_so_far(self):
        """A killed command used to come back with empty streams and no clue."""
        result = self.service.run_terminal_command(
            "echo starting; sleep 40", timeout_seconds=3
        )

        self.assertTrue(result["timed_out"])
        self.assertEqual(result["stdout"].strip(), "starting")
        self.assertIn("start_background_command", result["note"])

    def test_a_timeout_kills_the_whole_tree(self):
        """
        Killing only the shell is how a leaked server keeps a port forever.

        The child's own pid is written out and probed with `kill -0` rather
        than matched with `pgrep -f`: a pattern wide enough to find the child
        also matches the shell running pgrep, which made this flaky.
        """
        with tempfile.TemporaryDirectory() as scratch:
            pid_file = os.path.join(scratch, "child.pid")
            self.service.run_terminal_command(
                f"sleep 40 & echo $! > {pid_file}; sleep 41", timeout_seconds=2
            )
            time.sleep(0.5)
            with open(pid_file) as handle:
                child_pid = handle.read().strip()

        self.assertTrue(child_pid.isdigit(), "the child never reported its pid")
        probe = self.service.run_terminal_command(
            f"kill -0 {child_pid} 2>/dev/null && echo alive || echo gone"
        )
        self.assertEqual(
            probe["stdout"].strip(), "gone", "the child outlived the kill"
        )


class BackgroundTests(unittest.TestCase):
    """Starting, reading and stopping something that never exits."""

    def setUp(self):
        self.service = CommandLineService()
        self.started: list[str] = []

    def tearDown(self):
        for process_id in self.started:
            try:
                self.service.stop_background_command(process_id)
            except Exception:
                pass

    def _start(self, command, **kwargs):
        result = self.service.start_background_command(command, **kwargs)
        if result.get("process_id"):
            self.started.append(result["process_id"])
        return result

    def test_a_server_starts_serves_and_stops(self):
        result = self._start(
            f"python3 -m http.server {_PORT}", wait_for_port=_PORT, wait_timeout_seconds=15
        )

        self.assertTrue(result["ready"], result["ready_reason"])
        self.assertTrue(result["running"])
        with urllib.request.urlopen(f"http://127.0.0.1:{_PORT}", timeout=2) as response:
            self.assertEqual(response.status, 200)

        checked = self.service.check_background_command(result["process_id"])
        self.assertTrue(checked["found"])
        self.assertTrue(checked["running"])

        stopped = self.service.stop_background_command(result["process_id"])
        self.assertTrue(stopped["stopped"])
        self.assertTrue(stopped["was_running"])
        self.assertFalse(supervisor.port_open(_PORT), "the port is still held")

    def test_a_long_lived_command_returns_promptly(self):
        """The whole point: no waiting out a timeout for a healthy server."""
        started = time.monotonic()
        result = self._start(f"python3 -m http.server {_PORT + 1}")
        elapsed = time.monotonic() - started

        self.assertTrue(result["running"])
        self.assertLess(elapsed, 5, "a start with no readiness check should not linger")

    def test_a_crash_on_startup_is_reported_as_a_crash(self):
        """
        The outcome that matters most, and the one a bare Popen cannot give.

        A server that dies on an import error must not come back as a healthy
        background process, or Nova announces success and the next request
        gets connection refused.
        """
        result = self._start(
            "python3 -c 'raise RuntimeError(\"DATABASE_URL is not set\")'",
            wait_for_port=_PORT + 2,
            wait_timeout_seconds=10,
        )

        self.assertFalse(result["ready"])
        self.assertTrue(result["exited"])
        self.assertEqual(result["exit_code"], 1)
        self.assertIn("DATABASE_URL", result["output"])

    def test_readiness_can_wait_on_a_log_line(self):
        result = self._start(
            "python3 -u -c 'import time; print(\"Uvicorn running\"); time.sleep(30)'",
            wait_for_log="Uvicorn running",
            wait_timeout_seconds=10,
        )

        self.assertTrue(result["ready"])
        self.assertIn("Uvicorn running", result["ready_reason"])

    def test_a_process_that_never_signals_is_not_called_ready(self):
        result = self._start("sleep 30", wait_for_port=_PORT + 3, wait_timeout_seconds=2)

        self.assertFalse(result["ready"])
        self.assertTrue(result["running"])
        self.assertIn("did not signal readiness", result["ready_reason"])

    def test_listing_finds_a_process_whose_id_was_never_written_down(self):
        result = self._start(f"python3 -m http.server {_PORT + 4}")

        listed = self.service.check_background_command()
        self.assertIn(result["process_id"], [p["process_id"] for p in listed["processes"]])

    def test_an_unknown_id_is_answered_not_raised(self):
        result = self.service.check_background_command("proc_doesnotexist")

        self.assertFalse(result["found"])
        self.assertIn("check_background_command", result["note"])

    def test_run_terminal_command_routes_a_server_to_the_background(self):
        """Nova does not have to pick the right tool for this to work."""
        result = self.service.run_terminal_command(f"python3 -m http.server {_PORT + 5}")
        if result.get("process_id"):
            self.started.append(result["process_id"])

        self.assertTrue(result.get("background"))
        self.assertTrue(result["running"])
        self.assertIn("background", result["note"])


class RegistrationTests(unittest.TestCase):
    """The tools have to exist and point at methods that exist."""

    def test_both_hosts_expose_the_same_three_tools(self):
        import scripts.register_coding_tools as coding
        import scripts.register_project_tools as project

        expected = {
            "src.service.command_line_service.CommandLineService": [
                "start_background_command",
                "check_background_command",
                "stop_background_command",
            ],
            "src.service.coding_service.CodingService": [
                "start_mac_background_command",
                "check_mac_background_command",
                "stop_mac_background_command",
            ],
        }
        by_name = {
            tool["name"]: tool
            for tool in list(project.PROJECT_TOOLS) + list(coding.CODING_TOOLS)
        }

        for base, names in expected.items():
            module_path, class_name = base.rsplit(".", 1)
            module = __import__(module_path, fromlist=[class_name])
            service = getattr(module, class_name)
            for name in names:
                with self.subTest(tool=name):
                    self.assertIn(name, by_name)
                    path = by_name[name]["config"]["callable_path"]
                    self.assertEqual(path, f"{base}.{name}")
                    self.assertTrue(callable(getattr(service, name, None)))

    def test_the_terminal_artifact_covers_every_shell_tool(self):
        """
        agent_loop keys the terminal artifact off the tool name, so a new
        shell tool renders nothing until it is listed there.
        """
        from src.harness.agent_loop import AgentLoop

        for name in (
            "run_terminal_command",
            "run_mac_command",
            "start_background_command",
            "start_mac_background_command",
        ):
            with self.subTest(tool=name):
                self.assertIn(name, AgentLoop._SHELL_TOOLS)

    def test_a_background_result_renders_as_terminal_output(self):
        from src.harness.agent_loop import AgentLoop

        artifact = AgentLoop._artifact_for_tool(
            "start_background_command",
            {"command": "uv run main.py"},
            {"output": "Uvicorn running on http://127.0.0.1:8000", "running": True},
        )

        self.assertIsNotNone(artifact)
        self.assertEqual(artifact["kind"], "terminal")
        self.assertEqual(artifact["title"], "uv run main.py")
        self.assertIn("Uvicorn running", artifact["content"])

    def test_check_and_stop_take_their_title_from_the_payload(self):
        """Those two are given a process_id, so the command comes back with the result."""
        from src.harness.agent_loop import AgentLoop

        artifact = AgentLoop._artifact_for_tool(
            "check_background_command",
            {"process_id": "proc_abc"},
            {"command": "npm run dev", "output": "ready in 431 ms"},
        )

        self.assertEqual(artifact["title"], "npm run dev")


class MirrorTests(unittest.TestCase):
    """
    The tower's supervisor and the Mac's copy have to agree.

    They are two files because mac_agent deploys on its own, with its own
    requirements and no access to src/ — which makes silent drift the standing
    risk, the same one shell.py's docstring warns about for the result shape.
    A disagreement here means Nova behaves differently depending on which
    machine it asked, which is the least debuggable kind of bug.
    """

    @classmethod
    def setUpClass(cls):
        mac_agent = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mac_agent"
        )
        if mac_agent not in sys.path:
            sys.path.insert(0, mac_agent)
        from novacode import processes

        cls.mac = processes

    def test_the_two_classifiers_agree(self):
        commands = [
            r"cd C:\Users\natha\nova-backend && start uv run main.py",
            "start uv run main.py",
            "uv run main.py",
            "uvicorn main:app --reload &",
            "npm run dev",
            "tail -f app.log",
            "docker compose up",
            "docker compose up -d",
            "pytest -q",
            "git status",
            "cat main.py",
            "grep -n uvicorn main.py",
            "echo restart",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(
                    supervisor.classify(command)[0],
                    self.mac.classify(command)[0],
                    "the two hosts disagree about this command",
                )
                self.assertEqual(
                    supervisor.strip_detach_syntax(command),
                    self.mac.strip_detach_syntax(command),
                )

    def test_the_limits_match(self):
        for name in ("MAX_OUTPUT_CHARS", "DEFAULT_READY_TIMEOUT",
                     "MAX_READY_TIMEOUT", "CRASH_GRACE_SECONDS"):
            with self.subTest(constant=name):
                self.assertEqual(getattr(supervisor, name), getattr(self.mac, name))

    def test_both_report_the_same_keys(self):
        """agent_loop reads one result shape, whichever host produced it."""
        import asyncio

        tower = supervisor.start("python3 -c 'print(1)'")
        mac = asyncio.run(self.mac.start("python3 -c 'print(1)'"))
        try:
            self.assertEqual(set(tower) - {"note"}, set(mac) - {"note"})
            self.assertEqual(tower["host"], "tower")
            self.assertEqual(mac["host"], "mac")
        finally:
            supervisor.stop(tower["process_id"])
            asyncio.run(self.mac.stop(mac["process_id"]))


if __name__ == "__main__":
    unittest.main()
