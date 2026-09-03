"""
Coverage for the wiring that ToolService's construction model breaks.

ToolService resolves a tool by importing the class and calling
`service_class()` — a brand-new instance per call. Anything the controller
wires onto its own instance is therefore invisible to the instance a tool
actually runs on, and the failure is silent until a real tool call raises at
runtime with the socket sitting there connected.
"""

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
