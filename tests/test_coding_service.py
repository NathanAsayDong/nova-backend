"""
Coverage for the wiring that ToolService's construction model breaks.

ToolService resolves a tool by importing the class and calling
`service_class()` — a brand-new instance per call. Anything the controller
wires onto its own instance is therefore invisible to the instance a tool
actually runs on, and the failure is silent until a real tool call raises at
runtime with the socket sitting there connected.
"""

import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
