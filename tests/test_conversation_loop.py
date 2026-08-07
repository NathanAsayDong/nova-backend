import unittest
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from src.harness.agent_loop import AgentLoop
from src.model.conversation import Conversation
from src.model.message import MessageRole
from src.service.tool_service import ToolService


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeMessage:
    content: list


class FakeToolDao:
    def get_all(self):
        return []


@dataclass
class FakeConversationService:
    """In-memory stand-in for the persistence layer."""

    conversations: dict = field(default_factory=dict)
    recorded: list = field(default_factory=list)

    def ensure_open_conversation(self, conversation_uuid):
        return self.conversations.setdefault(
            conversation_uuid,
            Conversation(id=1, uuid=conversation_uuid),
        )

    def load_history(self, conversation):
        return []

    def record_message(self, conversation, role, content):
        self.recorded.append((conversation.uuid, role, content))


class ConversationLoopStreamTests(unittest.TestCase):
    def setUp(self):
        self.agent_loop = AgentLoop()
        self.conversation_id = uuid4()
        tool_service = ToolService.__new__(ToolService)
        tool_service.tool_dao = FakeToolDao()
        self.agent_loop.tool_service = tool_service
        self.conversation_service = FakeConversationService()
        self.agent_loop.conversation_service = self.conversation_service

    def test_new_conversation_id_returns_uuid(self):
        new_id = self.agent_loop.new_conversation_id()
        self.assertIsInstance(new_id, UUID)

    def _set_stream(self, text: str):
        def fake_stream(prompt, role=None, context=None, tools=None):
            blocks = [FakeTextBlock(text=text)] if text else []
            return FakeMessage(content=blocks)

        self.agent_loop.claude_service.stream_response = fake_stream

    def test_yields_full_text_and_updates_history(self):
        self._set_stream("Hello there. How can I help you today?")

        chunks = list(
            self.agent_loop.conversation_loop_stream("hi", self.conversation_id)
        )

        self.assertEqual(" ".join(chunks), "Hello there. How can I help you today?")
        history = self.agent_loop.conversations[self.conversation_id]
        self.assertEqual(
            history,
            [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "Hello there. How can I help you today?"},
            ],
        )

    def test_empty_stream_commits_user_and_empty_assistant(self):
        self._set_stream("")

        chunks = list(
            self.agent_loop.conversation_loop_stream("hi", self.conversation_id)
        )

        self.assertEqual(chunks, [])
        history = self.agent_loop.conversations[self.conversation_id]
        self.assertEqual(
            history,
            [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": ""},
            ],
        )

    def test_turn_persists_user_and_nova_messages(self):
        self._set_stream("Hello there. How can I help you today?")

        list(self.agent_loop.conversation_loop_stream("hi", self.conversation_id))

        self.assertEqual(
            self.conversation_service.recorded,
            [
                (self.conversation_id, MessageRole.USER, "hi"),
                (
                    self.conversation_id,
                    MessageRole.NOVA,
                    "Hello there. How can I help you today?",
                ),
            ],
        )

    def test_interrupted_stream_commits_assistant_text(self):
        self._set_stream(
            "This is the first full sentence right here. Second sentence never finishes"
        )

        stream = self.agent_loop.conversation_loop_stream("hi", self.conversation_id)
        first_chunk = next(stream)
        stream.close()

        self.assertEqual(first_chunk, "This is the first full sentence right here.")
        history = self.agent_loop.conversations[self.conversation_id]
        self.assertEqual(history[0], {"role": "user", "content": "hi"})
        self.assertEqual(history[1]["role"], "assistant")
        self.assertTrue(history[1]["content"].startswith("This is the first full sentence"))


class SentenceChunkTests(unittest.TestCase):
    def test_chunks_on_sentence_boundaries(self):
        pieces = ["Hello there. How are", " you today? Great."]
        chunks = list(AgentLoop.iter_sentence_chunks(iter(pieces), min_chars=5))
        self.assertEqual(chunks, ["Hello there.", "How are you today?", "Great."])

    def test_min_chars_merges_short_sentences(self):
        pieces = ["Hi. This is a longer sentence. And another one follows here."]
        chunks = list(AgentLoop.iter_sentence_chunks(iter(pieces), min_chars=10))
        self.assertEqual(
            chunks,
            ["Hi. This is a longer sentence.", "And another one follows here."],
        )

    def test_trailing_text_without_punctuation_is_flushed(self):
        chunks = list(AgentLoop.iter_sentence_chunks(iter(["no punctuation here"]), min_chars=5))
        self.assertEqual(chunks, ["no punctuation here"])


if __name__ == "__main__":
    unittest.main()
