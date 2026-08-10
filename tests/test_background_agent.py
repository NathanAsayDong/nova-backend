import unittest
from dataclasses import dataclass, field
from types import SimpleNamespace
from uuid import UUID, uuid4

from src.harness.agent_loop import AgentLoop
from src.model.conversation import Conversation
from src.service.tool_service import ToolService


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeMessage:
    content: list
    stop_reason: str = "end_turn"


class FakeToolDao:
    def get_all(self):
        return []


class FakeUpdateService:
    def __init__(self):
        self.created = []

    def create_update(self, update_message, project_id=None, conversation_id=None):
        record = {
            "update_message": update_message,
            "project_id": project_id,
            "conversation_id": conversation_id,
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

        def fake_get_response(prompt, role=None, context=None, tools=None, system=None):
            self.captured.append({"context": list(context or []), "system": system})
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
        self.assertEqual(update["conversation_id"], 7)
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
        self.assertIsNone(update["conversation_id"])
        self.assertIsNone(update["project_id"])

    def test_background_failure_still_records_update(self):
        def broken(prompt, role=None, context=None, tools=None, system=None):
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


if __name__ == "__main__":
    unittest.main()
