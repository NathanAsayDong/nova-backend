"""
Coverage for the wiring that ToolService's construction model breaks.

ToolService resolves a tool by importing the class and calling
`service_class()` — a brand-new instance per call. Anything the controller
wires onto its own instance is therefore invisible to the instance a tool
actually runs on, and the failure is silent until a real tool call raises at
runtime with the socket sitting there connected.
"""

import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from src.service.coding_service import CodingService


class FakeLink:
    connected = True


class AgentBindingTests(unittest.TestCase):
    def setUp(self):
        self._link, self._loop = CodingService.link, CodingService.loop
        CodingService.link = None
        CodingService.loop = None

    def tearDown(self):
        CodingService.link, CodingService.loop = self._link, self._loop

    @patch("src.service.coding_service.CodingSessionDao")
    def test_a_freshly_built_service_sees_the_bound_link(self, _dao):
        """The exact path ToolService takes: bind on one, construct another."""
        link = FakeLink()
        CodingService.bind_link(link)

        self.assertIs(CodingService().link, link)

    @patch("src.service.coding_service.CodingSessionDao")
    def test_a_freshly_built_service_sees_the_bound_loop(self, _dao):
        sentinel = object()
        CodingService.bind_loop(sentinel)

        self.assertIs(CodingService().loop, sentinel)

    @patch("src.service.coding_service.CodingSessionDao")
    def test_binding_on_one_instance_reaches_every_other(self, _dao):
        """Regression: per-instance wiring is what broke this the first time."""
        first = CodingService()
        link = FakeLink()
        type(first).bind_link(link)

        self.assertIs(CodingService().link, link)

    @patch("src.service.coding_service.CodingSessionDao")
    def test_an_unbound_loop_says_what_to_do(self, _dao):
        with self.assertRaises(RuntimeError) as caught:
            CodingService()._run(None)

        self.assertIn("Restart the API", str(caught.exception))


class TimestampShapeTests(unittest.TestCase):
    """
    Rows read back from Supabase carry ISO strings where the model claims
    datetimes -- SQLModel does not validate `table=True` models, so nothing
    coerces them. Both shapes reach _to_dict and both have to survive it.
    """

    def _session(self, created, updated):
        from src.model.coding_session import CodingSession

        return CodingSession(
            session_id=uuid4(),
            title="t",
            repo="nova-backend",
            instructions="do a thing",
            created_at=created,
            updated_at=updated,
        )

    def test_a_row_from_the_database_survives(self):
        """The shape that crashed: strings straight out of postgres."""
        row = self._session("2026-09-03T16:45:00+00:00", "2026-09-03T16:46:00+00:00")

        out = CodingService._to_dict(row)

        self.assertEqual(out["createdAt"], "2026-09-03T16:45:00+00:00")
        self.assertEqual(out["updatedAt"], "2026-09-03T16:46:00+00:00")

    def test_a_row_built_in_memory_survives(self):
        now = datetime(2026, 9, 3, 16, 45, tzinfo=timezone.utc)

        out = CodingService._to_dict(self._session(now, now))

        self.assertEqual(out["createdAt"], now.isoformat())

    def test_missing_timestamps_are_null_not_the_string_none(self):
        out = CodingService._to_dict(self._session(None, None))

        self.assertIsNone(out["createdAt"])
        self.assertIsNone(out["updatedAt"])


if __name__ == "__main__":
    unittest.main()


class WorkingTreeTests(unittest.TestCase):
    """
    Sessions run in the repo Nate actually has open, not a hidden worktree.

    The tool description is part of the behaviour here: it is the only thing
    telling Nova that a repo takes one task at a time and that continuing an
    existing thread is usually better than starting cold.
    """

    @classmethod
    def setUpClass(cls):
        # register_coding_tools calls load_dotenv() at import — a side effect
        # that leaks the real .env into os.environ for every test that runs
        # afterwards. test_cursor_service asserts on a MISSING CURSOR_API_KEY
        # and started failing the moment this file imported that script.
        # Snapshot the environment and put it back.
        cls._env = dict(os.environ)
        import scripts.register_coding_tools as reg

        cls.tools = reg.CODING_TOOLS

    @classmethod
    def tearDownClass(cls):
        os.environ.clear()
        os.environ.update(cls._env)

    def test_start_describes_the_real_working_tree(self):
        start = next(t for t in self.tools if t["name"] == "start_coding_task")

        self.assertIn("REAL working tree", start["description"])
        self.assertIn("never switches branches", start["description"])
        self.assertNotIn("nova/<slug>", start["description"])

    def test_the_history_tools_are_registered_and_wired(self):
        by_name = {t["name"]: t for t in self.tools}
        for name in ("list_claude_threads", "read_claude_thread", "continue_claude_thread"):
            self.assertIn(name, by_name)
            path = by_name[name]["config"]["callable_path"]
            method = path.rsplit(".", 1)[-1]
            self.assertTrue(
                hasattr(CodingService, method),
                f"{name} points at {path}, which does not exist",
            )

    def test_every_tool_points_at_a_real_method(self):
        """A typo'd callable_path fails only at runtime, on a live tool call."""
        for tool in self.tools:
            method = tool["config"]["callable_path"].rsplit(".", 1)[-1]
            self.assertTrue(
                callable(getattr(CodingService, method, None)),
                f"{tool['name']} -> {method} is not a method on CodingService",
            )


class MacShellTests(unittest.TestCase):
    """
    run_terminal_command routes to the Mac, not the tower.

    The collision here only fails on a live call: AgentLink.call's first
    positional is named `command`, so the shell string cannot also ride as
    `command=`. These pin the wire contract so a rename cannot bring it back.

    One asyncio loop runs on a background thread for the whole class -- that
    is what `_run` schedules onto -- and is torn down once at the end rather
    than per test, which is what made the first version try to close a loop
    while it was still running.
    """

    @classmethod
    def setUpClass(cls):
        import asyncio, threading

        cls._saved = (CodingService.link, CodingService.loop)
        cls._env = dict(os.environ)
        cls.loop = asyncio.new_event_loop()
        cls._thread = threading.Thread(target=cls.loop.run_forever, daemon=True)
        cls._thread.start()
        CodingService.bind_loop(cls.loop)

    @classmethod
    def tearDownClass(cls):
        cls.loop.call_soon_threadsafe(cls.loop.stop)
        cls._thread.join(timeout=2)
        cls.loop.close()
        CodingService.link, CodingService.loop = cls._saved
        os.environ.clear()
        os.environ.update(cls._env)

    class _FakeLink:
        connected = True
        def __init__(self):
            self.sent = None
        async def call(self, command, timeout=90.0, **fields):
            self.sent = {"name": command, "timeout": timeout, **fields}
            return {"host": "mac", "exit_code": 0, "stdout": "ok",
                    "stderr": "", "timed_out": False}

    def _service(self):
        link = self._FakeLink()
        CodingService.bind_link(link)
        with patch.object(CodingService, "__init__", lambda self: None):
            svc = CodingService()
        return svc, link

    def test_the_shell_string_is_not_passed_as_command(self):
        svc, link = self._service()
        result = svc.run_mac_command("pytest -q", None, 45, "c1")

        self.assertEqual(link.sent["name"], "exec")      # envelope command NAME
        self.assertEqual(link.sent["cmd"], "pytest -q")  # shell string as cmd
        self.assertNotIn("command", link.sent)           # the collision
        self.assertEqual(result["host"], "mac")

    def test_the_call_timeout_outlasts_the_command_timeout(self):
        """A 504 must not fire while the Mac is still legitimately working."""
        svc, link = self._service()
        svc.run_mac_command("sleep 100", None, 120, None)

        self.assertEqual(link.sent["timeout_seconds"], 120)
        self.assertGreater(link.sent["timeout"], 120)

    def test_run_mac_command_is_registered_and_wired(self):
        import scripts.register_coding_tools as reg

        tool = next(t for t in reg.CODING_TOOLS if t["name"] == "run_mac_command")
        path = tool["config"]["callable_path"]
        self.assertEqual(path, "src.service.coding_service.CodingService.run_mac_command")
        self.assertTrue(callable(getattr(CodingService, path.rsplit(".", 1)[-1], None)))

    def test_run_terminal_command_stayed_on_the_tower(self):
        """The sibling must not have moved: it still runs on the server."""
        import scripts.register_project_tools as reg

        tool = next(t for t in reg.PROJECT_TOOLS if t["name"] == "run_terminal_command")
        self.assertEqual(
            tool["config"]["callable_path"],
            "src.service.command_line_service.CommandLineService.run_terminal_command",
        )
