"""
Coverage for memory that arrives without the model asking for it: the
relevance gate on retrieval, and how the block reaches the prompt.
"""

import unittest
from dataclasses import dataclass, field
from uuid import uuid4

from prompting.prompt_source_prompt import PromptSourceEnum
from src.harness.agent_loop import AgentLoop
from src.model.conversation import Conversation
from src.model.memory_chunk import MemoryChunk, MemoryMatch
from src.model.message import MessageRole
from src.service.memory_chunk_service import MemoryChunkService
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


@dataclass
class FakeConversationService:
    project_id: int | None = None
    conversations: dict = field(default_factory=dict)
    recorded: list = field(default_factory=list)

    def ensure_open_conversation(self, conversation_uuid):
        return self.conversations.setdefault(
            conversation_uuid,
            Conversation(id=1, uuid=conversation_uuid, project_id=self.project_id),
        )

    def load_history(self, conversation):
        return []

    def record_message(self, conversation, role, content):
        self.recorded.append((conversation.uuid, role, content))


@dataclass
class FakeEmbeddingService:
    calls: list = field(default_factory=list)

    def embed_text(self, text):
        self.calls.append(text)
        return [0.1, 0.2, 0.3]


@dataclass
class FakeMemoryChunkDao:
    matches: list = field(default_factory=list)
    calls: list = field(default_factory=list)

    def match_memory_chunks(self, embedding, project_id=None, limit=5):
        self.calls.append({"project_id": project_id, "limit": limit})
        return self.matches


def match(content, similarity):
    return MemoryMatch(chunk=MemoryChunk(id=1, content=content), similarity=similarity)


def build_memory_service(matches=()) -> MemoryChunkService:
    service = MemoryChunkService.__new__(MemoryChunkService)
    service.memory_chunk_dao = FakeMemoryChunkDao(matches=list(matches))
    service.embedding_service = FakeEmbeddingService()
    service.conversation_service = FakeConversationService()
    return service


class RetrievableQueryTests(unittest.TestCase):
    def test_content_bearing_turns_are_retrievable(self):
        for query in (
            "what did we decide about the migration",
            "email Sophie the notes",
            "remind me about the deploy",
        ):
            self.assertTrue(MemoryChunkService.is_retrievable_query(query), query)

    def test_acknowledgments_are_not(self):
        # Embedding "thanks" returns whatever sits nearest a content-free
        # phrase, which is noise by construction.
        for query in ("yes", "thanks", "ok cool", "stop", "yeah sure", "hey nova"):
            self.assertFalse(MemoryChunkService.is_retrievable_query(query), query)

    def test_empty_is_not(self):
        self.assertFalse(MemoryChunkService.is_retrievable_query(""))
        self.assertFalse(MemoryChunkService.is_retrievable_query("   "))
        self.assertFalse(MemoryChunkService.is_retrievable_query("..."))


class RetrieveContextTests(unittest.TestCase):
    def test_returns_only_matches_above_the_gate(self):
        service = build_memory_service(
            [
                match("Nate deploys on Fridays.", 0.71),
                match("Nate's wife is Sophie.", 0.44),
                match("Unrelated trivia about lemons.", 0.21),
            ]
        )
        block = service.retrieve_context("when does Nate deploy")
        self.assertIn("Nate deploys on Fridays.", block)
        self.assertIn("Nate's wife is Sophie.", block)
        self.assertNotIn("lemons", block)

    def test_returns_none_when_nothing_clears_the_gate(self):
        # The whole point of the gate: five weak neighbours is worse than
        # nothing, because irrelevant context misleads.
        service = build_memory_service([match("Unrelated trivia.", 0.18)])
        self.assertIsNone(service.retrieve_context("when does Nate deploy"))

    def test_returns_none_when_memory_is_empty(self):
        service = build_memory_service([])
        self.assertIsNone(service.retrieve_context("when does Nate deploy"))

    def test_skips_the_lookup_entirely_for_acknowledgments(self):
        service = build_memory_service([match("Nate deploys on Fridays.", 0.9)])
        self.assertIsNone(service.retrieve_context("thanks"))
        self.assertEqual(service.embedding_service.calls, [])

    def test_block_tells_the_model_what_it_is_looking_at(self):
        service = build_memory_service([match("Nate deploys on Fridays.", 0.9)])
        block = service.retrieve_context("deploy schedule")
        self.assertIn("long-term memory", block)
        self.assertIn("fetch_memory", block)

    def test_scopes_the_search_by_project(self):
        service = build_memory_service([match("Project fact.", 0.9)])
        service.retrieve_context("deploy schedule", project_id=7)
        self.assertEqual(service.memory_chunk_dao.calls[0]["project_id"], 7)

    def test_long_chunks_are_truncated(self):
        service = build_memory_service([match("x" * 2000, 0.9)])
        block = service.retrieve_context("deploy schedule")
        self.assertLess(len(block), 800)
        self.assertIn("…", block)

    def test_respects_an_explicit_threshold(self):
        service = build_memory_service([match("Borderline.", 0.35)])
        self.assertIsNone(service.retrieve_context("q", min_similarity=0.4))
        self.assertIsNotNone(service.retrieve_context("q", min_similarity=0.3))


class MemoryInjectionTests(unittest.TestCase):
    def setUp(self):
        self.agent_loop = AgentLoop()
        self.conversation_id = uuid4()
        tool_service = ToolService.__new__(ToolService)
        tool_service.tool_dao = FakeToolDao()
        self.agent_loop.tool_service = tool_service
        self.conversation_service = FakeConversationService()
        self.agent_loop.conversation_service = self.conversation_service
        self.agent_loop.mcp_server_service = None
        self.agent_loop._load_mcp_servers = lambda: []
        self.sent_messages = []

        def fake_stream(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            self.sent_messages.append(list(context or []))
            return FakeMessage(content=[FakeTextBlock(text="Friday, as always.")])

        self.agent_loop.claude_service.stream_response = fake_stream

    def use_memory(self, block):
        self.agent_loop.memory_retrieval_enabled = True
        self.agent_loop.memory_chunk_service = object()  # never reached
        self.agent_loop._retrieve_memory = lambda prompt, project_id: block

    def run_turn(self, prompt="when do I deploy"):
        return list(
            self.agent_loop.conversation_loop_events(
                prompt,
                self.conversation_id,
                prompt_source=PromptSourceEnum.CHAT_PROMPT,
            )
        )

    def first_user_message(self):
        return self.sent_messages[0][0]["content"]

    def test_memory_rides_on_the_user_message(self):
        # Not a system block: system renders before messages, so a block that
        # changes every turn would invalidate the cached history behind it.
        self.use_memory("- Nate deploys on Fridays.")
        self.run_turn()
        content = self.first_user_message()
        self.assertIn("<recalled_memory>", content)
        self.assertIn("Nate deploys on Fridays.", content)
        self.assertTrue(content.endswith("when do I deploy"))

    def test_only_the_users_own_words_are_persisted(self):
        self.use_memory("- Nate deploys on Fridays.")
        self.run_turn()
        user_rows = [
            content
            for _, role, content in self.conversation_service.recorded
            if role == MessageRole.USER
        ]
        self.assertEqual(user_rows, ["when do I deploy"])

    def test_history_keeps_the_augmented_form(self):
        # The next turn's cached prefix has to be byte-identical to what this
        # turn sent, so history holds what the model saw.
        self.use_memory("- Nate deploys on Fridays.")
        self.run_turn()
        history = self.agent_loop.conversations[self.conversation_id]
        self.assertIn("<recalled_memory>", history[0]["content"])

    def test_nothing_is_injected_when_retrieval_finds_nothing(self):
        self.use_memory(None)
        self.run_turn()
        content = self.first_user_message()
        self.assertNotIn("<recalled_memory>", content)
        self.assertEqual(content, "when do I deploy")

    def test_a_failing_retrieval_does_not_take_the_turn_down(self):
        def boom(prompt, project_id):
            raise RuntimeError("vector store down")

        self.agent_loop.memory_retrieval_enabled = True
        self.agent_loop._retrieve_memory = boom
        events = self.run_turn()
        self.assertEqual(self.first_user_message(), "when do I deploy")
        self.assertTrue(any(event["type"] == "text" for event in events))

    def test_retrieval_is_scoped_to_the_conversations_project(self):
        self.conversation_service.project_id = 12
        seen = {}
        self.agent_loop.memory_retrieval_enabled = True
        self.agent_loop._retrieve_memory = lambda prompt, project_id: seen.setdefault(
            "project_id", project_id
        )
        self.run_turn()
        self.assertEqual(seen["project_id"], 12)

    def test_disabled_retrieval_never_runs(self):
        calls = []
        self.agent_loop.memory_retrieval_enabled = False
        self.agent_loop._retrieve_memory = lambda prompt, project_id: calls.append(prompt)
        self.run_turn()
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
