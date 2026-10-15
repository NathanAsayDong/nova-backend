import unittest
from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest import mock
from uuid import UUID, uuid4

from src.harness.agent_loop import AgentLoop
from src.model.conversation import Conversation
from src.model.responsibility import Responsibility
from src.model.tool import Tool
from src.service.tool_service import ToolExecutionError, ToolService


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeMessage:
    content: list
    stop_reason: str = "end_turn"


class FakeToolDao:
    def __init__(self, tools=()):
        self.tools = list(tools)

    def get_all(self):
        return self.tools


def _schema_tool(name: str) -> Tool:
    return Tool(
        id=hash(name) % 10_000,
        name=name,
        description=f"{name} tool",
        config={"input_schema": {"type": "object", "properties": {}}},
    )


class FakeUpdateService:
    def __init__(self):
        self.created = []

    def create_update(
        self,
        update_message,
        project_id=None,
        conversation_uuid=None,
        report_type=None,
    ):
        record = {
            "update_message": update_message,
            "project_id": project_id,
            "conversation_uuid": conversation_uuid,
            "report_type": report_type,
        }
        self.created.append(record)
        return record


class FakeProjectDao:
    def get(self, id):
        return SimpleNamespace(id=int(id), name="Apollo", description="Moon stuff")


@dataclass
class FakeConversationService:
    conversation: Conversation | None = None
    project_dao: FakeProjectDao = field(default_factory=FakeProjectDao)

    def get_conversation(self, conversation_uuid: UUID):
        return self.conversation


class BackgroundAgentTests(unittest.TestCase):
    def setUp(self):
        self.agent_loop = AgentLoop()
        # Memory injection is covered in its own suite; these tests
        # assert on prompts, so keep retrieval out of them.
        self.agent_loop.memory_retrieval_enabled = False
        tool_service = ToolService.__new__(ToolService)
        tool_service.tool_dao = FakeToolDao()
        self.agent_loop.tool_service = tool_service
        self.update_service = FakeUpdateService()
        self.agent_loop.update_service = self.update_service

        self.conversation_uuid = uuid4()
        self.agent_loop.conversation_service = FakeConversationService(
            conversation=Conversation(
                id=7, uuid=self.conversation_uuid, project_id=3
            )
        )

        self.captured = []

        def fake_get_response(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            self.captured.append(
                {"context": list(context or []), "system": system, "tools": tools}
            )
            return FakeMessage(content=[FakeTextBlock("All done: two files fixed.")])

        self.agent_loop.claude_service.get_response = fake_get_response

    def _join_background(self):
        for thread in self.agent_loop.background_threads:
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())

    def test_foreground_returns_text_and_creates_no_update(self):
        result = self.agent_loop.run_agent(prompt="do the thing")
        self.assertEqual(result, "All done: two files fixed.")
        self.assertEqual(self.update_service.created, [])
        self.assertIsNone(self.captured[0]["system"])

    def test_background_returns_ack_and_records_linked_update(self):
        result = self.agent_loop.run_agent(
            prompt="do the thing",
            background=True,
            conversation_uuid=str(self.conversation_uuid),
        )
        self.assertIn("update", result)
        self._join_background()

        self.assertEqual(len(self.update_service.created), 1)
        update = self.update_service.created[0]
        self.assertEqual(update["update_message"], "All done: two files fixed.")
        self.assertEqual(update["conversation_uuid"], str(self.conversation_uuid))
        self.assertEqual(update["project_id"], 3)

    def test_background_uses_background_prompt_and_project_context(self):
        self.agent_loop.run_agent(
            prompt="do the thing",
            background=True,
            conversation_uuid=str(self.conversation_uuid),
        )
        self._join_background()

        self.assertIn("background agent", self.captured[0]["system"].lower())
        task = self.captured[0]["context"][0]["content"]
        self.assertIn("Apollo", task)
        self.assertIn("do the thing", task)

    def test_background_without_conversation_records_unlinked_update(self):
        self.agent_loop.conversation_service = FakeConversationService(conversation=None)
        self.agent_loop.run_agent(prompt="do the thing", background=True)
        self._join_background()

        update = self.update_service.created[0]
        self.assertIsNone(update["conversation_uuid"])
        self.assertIsNone(update["project_id"])

    def test_background_failure_still_records_update(self):
        def broken(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            raise RuntimeError("api down")

        self.agent_loop.claude_service.get_response = broken
        self.agent_loop.run_agent(prompt="do the thing", background=True)
        self._join_background()

        # The loop converts API errors into a reply rather than raising, so
        # the failure surfaces as the update message either way.
        self.assertEqual(len(self.update_service.created), 1)
        self.assertIn("fail", self.update_service.created[0]["update_message"].lower())

    def test_background_with_no_prompt_raises_before_spawning(self):
        with self.assertRaises(ValueError):
            self.agent_loop.run_agent(background=True)
        self.assertEqual(self.agent_loop.background_threads, [])


class ReportTypeTests(BackgroundAgentTests):
    """
    report_type is the delivery intent the caller picks at spawn time. It has
    to survive the run and land on the update, because by the time anything is
    delivered this agent has exited.
    """

    def test_report_type_is_stamped_on_the_update(self):
        self.agent_loop.run_agent(
            prompt="do the thing", background=True, report_type="call"
        )
        self._join_background()

        self.assertEqual(self.update_service.created[0]["report_type"], "call")

    def test_no_report_type_leaves_the_update_badge_only(self):
        self.agent_loop.run_agent(prompt="do the thing", background=True)
        self._join_background()

        self.assertIsNone(self.update_service.created[0]["report_type"])

    def test_call_brief_tells_the_agent_to_write_for_speech(self):
        self.agent_loop.run_agent(
            prompt="do the thing", background=True, report_type="call"
        )
        self._join_background()

        task = self.captured[0]["context"][0]["content"]
        self.assertIn("spoken", task)
        # Delivery is the system's job — the agent must not try to call anyone.
        self.assertIn("Do not try to place the call yourself", task)

    def test_email_brief_tells_the_agent_not_to_send_it(self):
        self.agent_loop.run_agent(
            prompt="do the thing", background=True, report_type="email"
        )
        self._join_background()

        task = self.captured[0]["context"][0]["content"]
        self.assertIn("Do not send any email yourself", task)

    def test_ack_tells_the_user_to_expect_a_call(self):
        result = self.agent_loop.run_agent(
            prompt="do the thing", background=True, report_type="call"
        )
        self._join_background()

        self.assertIn("phone the user", result)

    def test_unknown_report_type_is_rejected_before_spawning(self):
        with self.assertRaises(ToolExecutionError) as caught:
            self.agent_loop.run_agent(
                prompt="do the thing", background=True, report_type="carrier-pigeon"
            )

        self.assertTrue(caught.exception.recoverable)
        self.assertEqual(self.agent_loop.background_threads, [])
        self.assertEqual(self.update_service.created, [])

    def test_blank_report_type_is_treated_as_unset(self):
        self.agent_loop.run_agent(prompt="do the thing", background=True, report_type="")
        self._join_background()

        self.assertIsNone(self.update_service.created[0]["report_type"])

    def test_report_type_is_case_insensitive(self):
        self.agent_loop.run_agent(
            prompt="do the thing", background=True, report_type="CALL"
        )
        self._join_background()

        self.assertEqual(self.update_service.created[0]["report_type"], "call")


_RESTRICTED_TOOL_NAMES = {
    "create_responsibility",
    "create_scheduled_task",
    "update_responsibility",
    "delete_responsibility",
}


class ResponsibilityRunToolRestrictionTests(unittest.TestCase):
    """
    A run launched from a responsibility is unattended — nobody is there to
    notice it schedule more unattended work on itself. That's how ids ~41 and
    ~44 ended up as duplicate responsibilities spawned from a responsibility's
    own run instead of it just doing the job. Such runs must not see
    create_responsibility, create_scheduled_task, update_responsibility, or
    delete_responsibility in their tool list, and must be told in the prompt
    not to create or modify responsibilities/tasks.
    """

    def setUp(self):
        self.agent_loop = AgentLoop()
        self.agent_loop.memory_retrieval_enabled = False

        tools = [_schema_tool(name) for name in _RESTRICTED_TOOL_NAMES] + [
            _schema_tool("list_responsibilities"),
            _schema_tool("send_email"),
        ]
        tool_service = ToolService.__new__(ToolService)
        tool_service.tool_dao = FakeToolDao(tools)
        self.agent_loop.tool_service = tool_service
        # Fakes so a background=True run never touches the real DB-backed
        # services — only test_background_run_from_responsibility_is_also_restricted
        # exercises that path, but setting these up front keeps setUp simple.
        self.agent_loop.update_service = FakeUpdateService()
        self.agent_loop.conversation_service = FakeConversationService()

        self.responsibility = Responsibility(
            id=42,
            name="Text me at noon",
            description="Text the user at noon.",
            schedule=["afternoon"],
        )
        dao_patcher = mock.patch("src.harness.agent_loop.ResponsibilityDao")
        mock_dao_cls = dao_patcher.start()
        mock_dao_cls.return_value.get.return_value = self.responsibility
        self.addCleanup(dao_patcher.stop)

        self.captured = []

        def fake_get_response(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            self.captured.append(
                {"context": list(context or []), "system": system, "tools": tools}
            )
            return FakeMessage(content=[FakeTextBlock("Texted the user.")])

        self.agent_loop.claude_service.get_response = fake_get_response

    def test_restricted_tools_absent_from_responsibility_run(self):
        self.agent_loop.run_agent(responsibility_id=42)

        tool_names = {t["name"] for t in (self.captured[0]["tools"] or [])}
        self.assertFalse(tool_names & _RESTRICTED_TOOL_NAMES)
        self.assertIn("list_responsibilities", tool_names)
        self.assertIn("send_email", tool_names)

    def test_prompt_tells_agent_not_to_manage_responsibilities(self):
        self.agent_loop.run_agent(responsibility_id=42)

        task = self.captured[0]["context"][0]["content"]
        self.assertIn("do not create or modify responsibilities", task.lower())

    def test_ordinary_prompt_run_keeps_all_tools(self):
        """A plain prompt run (no responsibility_id) is unrestricted."""
        self.agent_loop.run_agent(prompt="do the thing")

        tool_names = {t["name"] for t in (self.captured[0]["tools"] or [])}
        self.assertTrue(_RESTRICTED_TOOL_NAMES.issubset(tool_names))

    def test_background_run_from_responsibility_is_also_restricted(self):
        """
        preform_responsibility never sets background=True today, but if a
        responsibility run is ever dispatched in the background, the
        restriction must still follow it onto that thread.
        """
        self.agent_loop.run_agent(responsibility_id=42, background=True)
        for thread in self.agent_loop.background_threads:
            thread.join(timeout=5)

        tool_names = {t["name"] for t in (self.captured[0]["tools"] or [])}
        self.assertFalse(tool_names & _RESTRICTED_TOOL_NAMES)


if __name__ == "__main__":
    unittest.main()
