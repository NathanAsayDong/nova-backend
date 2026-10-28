import unittest
from dataclasses import dataclass, field
from unittest import mock
from uuid import uuid4

from src.model.conversation import Conversation
from src.model.memory_chunk import MemoryChunk
from src.model.message import Message, MessageRole
from src.service.memory_chunk_service import MemoryChunkService


@dataclass
class FakeTextBlock:
    text: str


@dataclass
class FakeClaudeResponse:
    content: list


class FakeClaudeService:
    def __init__(self, reply="[]"):
        # `reply` may be a single string (every call gets it) or a list of
        # strings (one per call, in order) for tests that need the
        # summarizer to behave differently across multiple pieces/attempts.
        self.reply = reply
        self.prompts: list[str] = []

    def get_response(self, prompt, role=None, context=None, tools=None):
        self.prompts.append(prompt)
        if isinstance(self.reply, list):
            text = self.reply[len(self.prompts) - 1]
        else:
            text = self.reply
        return FakeClaudeResponse(content=[FakeTextBlock(text=text)])


class FakeEmbeddingService:
    def embed_text(self, text):
        return [0.1, 0.2, 0.3]

    def embed_texts(self, texts):
        return [[float(i)] * 3 for i, _ in enumerate(texts)]


@dataclass
class FakeMemoryChunkDao:
    inserted: list = field(default_factory=list)
    search_results: list = field(default_factory=list)
    search_calls: list = field(default_factory=list)

    def insert_memory_chunks(self, chunks):
        self.inserted.extend(chunks)

    def get_memory_chunks(self, embedding, project_id=None, limit=5):
        self.search_calls.append({"project_id": project_id, "limit": limit})
        return self.search_results


@dataclass
class FakeConversationService:
    conversations: list = field(default_factory=list)
    messages: dict = field(default_factory=dict)
    processed: list = field(default_factory=list)

    def get_unprocessed_closed_conversations(self):
        return self.conversations

    def get_messages(self, conversation_uuid):
        return self.messages.get(conversation_uuid, [])

    def mark_processed(self, conversation_uuid):
        self.processed.append(conversation_uuid)

    def get_conversation(self, conversation_uuid):
        for conversation in self.conversations:
            if conversation.uuid == conversation_uuid:
                return conversation
        return None


def build_service(claude_reply='["fact one", "fact two"]') -> MemoryChunkService:
    service = MemoryChunkService.__new__(MemoryChunkService)
    service.memory_chunk_dao = FakeMemoryChunkDao()
    service.conversation_service = FakeConversationService()
    service.embedding_service = FakeEmbeddingService()
    service.claude_service = FakeClaudeService(claude_reply)
    return service


class ProcessConversationsTests(unittest.TestCase):
    def _add_conversation(self, service, project_id=None, with_messages=True):
        conversation = Conversation(id=1, uuid=uuid4(), project_id=project_id, is_closed=True)
        service.conversation_service.conversations.append(conversation)
        if with_messages:
            service.conversation_service.messages[conversation.uuid] = [
                Message(conversation_uuid=conversation.uuid, role=MessageRole.USER, content="hi"),
                Message(conversation_uuid=conversation.uuid, role=MessageRole.NOVA, content="hello"),
            ]
        return conversation

    def test_creates_chunks_with_project_fk_and_marks_processed(self):
        service = build_service()
        conversation = self._add_conversation(service, project_id=7)

        summary = service.process_conversations()

        self.assertEqual(summary["conversations_processed"], 1)
        self.assertEqual(summary["memory_chunks_created"], 2)
        self.assertEqual(summary["failures"], 0)
        inserted = service.memory_chunk_dao.inserted
        self.assertEqual([c.content for c in inserted], ["fact one", "fact two"])
        self.assertTrue(all(c.project_id == 7 for c in inserted))
        self.assertTrue(all(c.embedding is not None for c in inserted))
        self.assertEqual(service.conversation_service.processed, [conversation.uuid])

    def test_no_project_conversation_creates_general_chunks(self):
        service = build_service()
        self._add_conversation(service, project_id=None)

        service.process_conversations()

        self.assertTrue(
            all(c.project_id is None for c in service.memory_chunk_dao.inserted)
        )

    def test_empty_conversation_marked_processed_without_chunks(self):
        service = build_service()
        conversation = self._add_conversation(service, with_messages=False)

        summary = service.process_conversations()

        self.assertEqual(summary["memory_chunks_created"], 0)
        self.assertEqual(service.memory_chunk_dao.inserted, [])
        self.assertEqual(service.conversation_service.processed, [conversation.uuid])

    def test_nothing_worth_remembering_creates_no_chunks(self):
        service = build_service(claude_reply="[]")
        self._add_conversation(service)

        summary = service.process_conversations()

        self.assertEqual(summary["memory_chunks_created"], 0)
        self.assertEqual(summary["conversations_processed"], 1)

    def test_failure_leaves_conversation_unprocessed(self):
        service = build_service()
        self._add_conversation(service)

        def boom(chunks):
            raise RuntimeError("db down")

        service.memory_chunk_dao.insert_memory_chunks = boom

        summary = service.process_conversations()

        self.assertEqual(summary["failures"], 1)
        self.assertEqual(service.conversation_service.processed, [])


class ParseChunksTests(unittest.TestCase):
    def test_parses_json_array(self):
        self.assertEqual(
            MemoryChunkService._parse_chunks('["a", "b"]'),
            ["a", "b"],
        )

    def test_strips_markdown_fences(self):
        self.assertEqual(
            MemoryChunkService._parse_chunks('```json\n["a"]\n```'),
            ["a"],
        )

    def test_non_json_falls_back_to_single_chunk(self):
        self.assertEqual(
            MemoryChunkService._parse_chunks("just a plain summary"),
            ["just a plain summary"],
        )

    def test_drops_non_string_and_empty_items(self):
        self.assertEqual(
            MemoryChunkService._parse_chunks('["a", "", 3, "  "]'),
            ["a"],
        )


class FetchMemoryTests(unittest.TestCase):
    def test_formats_results(self):
        service = build_service()
        service.memory_chunk_dao.search_results = [
            MemoryChunk(id=1, content="user prefers uv"),
            MemoryChunk(id=2, content="project Nova uses FastAPI"),
        ]

        result = service.fetch_memory("tooling preferences", project_id=3)

        self.assertIn("1. user prefers uv", result)
        self.assertIn("2. project Nova uses FastAPI", result)
        self.assertEqual(
            service.memory_chunk_dao.search_calls,
            [{"project_id": 3, "limit": 5}],
        )

    def test_no_results_message(self):
        service = build_service()
        self.assertEqual(service.fetch_memory("anything"), "No relevant memories found.")

    def test_conversation_scoping_uses_project_id(self):
        service = build_service()
        conversation = Conversation(id=1, uuid=uuid4(), project_id=9)
        service.conversation_service.conversations.append(conversation)

        service.fetch_memory_for_conversation("query", str(conversation.uuid))

        self.assertEqual(
            service.memory_chunk_dao.search_calls[0]["project_id"], 9
        )

    def test_blank_prompt_rejected(self):
        service = build_service()
        with self.assertRaises(ValueError):
            service.fetch_memory("   ")


class SplitTranscriptTests(unittest.TestCase):
    def test_short_transcript_is_a_single_piece(self):
        transcript = "line one\nline two"
        self.assertEqual(
            MemoryChunkService._split_transcript(transcript), [transcript]
        )

    @mock.patch("src.service.memory_chunk_service._MAX_TRANSCRIPT_CHARS_PER_PIECE", 25)
    def test_splits_on_message_line_boundaries(self):
        lines = ["[user] 0123456789", "[nova] 0123456789", "[user] 0123456789"]
        transcript = "\n".join(lines)

        pieces = MemoryChunkService._split_transcript(transcript)

        # Every original line must survive intact in exactly one piece, and
        # no piece should ever be a line cut in half.
        self.assertEqual("\n".join(pieces), transcript)
        for piece in pieces:
            for piece_line in piece.split("\n"):
                self.assertIn(piece_line, lines)
        self.assertGreater(len(pieces), 1)

    @mock.patch("src.service.memory_chunk_service._MAX_TRANSCRIPT_CHARS_PER_PIECE", 10)
    def test_oversized_single_line_becomes_its_own_piece(self):
        transcript = "[user] " + ("x" * 50)
        pieces = MemoryChunkService._split_transcript(transcript)
        self.assertEqual(pieces, [transcript])


class SummarizeTranscriptLimitsTests(unittest.TestCase):
    @mock.patch("src.service.memory_chunk_service._MAX_TRANSCRIPT_CHARS_PER_PIECE", 20)
    @mock.patch("src.service.memory_chunk_service._MAX_CHUNKS_PER_CONVERSATION_CEILING", 36)
    def test_combines_chunks_from_each_piece(self):
        service = build_service()
        service.claude_service = FakeClaudeService(
            ['["a", "b"]', '["c", "d"]', '["e"]']
        )
        # 6 lines of 8 chars each pair up into exactly 3 pieces under a
        # 20-char cap (2 lines + newline = 17 chars per piece).
        lines = [f"msgline{i}" for i in range(6)]
        transcript = "\n".join(lines)
        self.assertEqual(len(MemoryChunkService._split_transcript(transcript)), 3)

        chunks = service._summarize_transcript(transcript)

        self.assertEqual(len(service.claude_service.prompts), 3)
        self.assertEqual(chunks, ["a", "b", "c", "d", "e"])

    @mock.patch("src.service.memory_chunk_service._MAX_TRANSCRIPT_CHARS_PER_PIECE", 10)
    @mock.patch("src.service.memory_chunk_service._MAX_CHUNKS_PER_CONVERSATION", 12)
    @mock.patch("src.service.memory_chunk_service._MAX_CHUNKS_PER_CONVERSATION_CEILING", 3)
    def test_overall_ceiling_caps_combined_total_even_with_many_pieces(self):
        service = build_service()
        # Every piece's summarizer call returns more than the ceiling alone.
        service.claude_service = FakeClaudeService('["a", "b", "c", "d"]')
        transcript = "\n".join([f"[user] msg {i}" for i in range(10)])

        chunks = service._summarize_transcript(transcript)

        self.assertLessEqual(len(chunks), 3)

    def test_single_piece_transcript_uses_normal_path(self):
        service = build_service(claude_reply='["only one"]')
        chunks = service._summarize_transcript("[user] hi")
        self.assertEqual(chunks, ["only one"])
        self.assertEqual(len(service.claude_service.prompts), 1)


class RetryCapTests(unittest.TestCase):
    def setUp(self):
        MemoryChunkService._failed_attempts.clear()

    def tearDown(self):
        MemoryChunkService._failed_attempts.clear()

    def _add_conversation(self, service):
        conversation = Conversation(id=1, uuid=uuid4(), is_closed=True)
        service.conversation_service.conversations.append(conversation)
        service.conversation_service.messages[conversation.uuid] = [
            Message(conversation_uuid=conversation.uuid, role=MessageRole.USER, content="hi"),
        ]
        return conversation

    @mock.patch("src.service.memory_chunk_service._MAX_PROCESS_ATTEMPTS", 3)
    def test_retries_under_cap_leave_conversation_unprocessed(self):
        service = build_service()
        conversation = self._add_conversation(service)

        def boom(chunks):
            raise RuntimeError("summarizer down")

        service.memory_chunk_dao.insert_memory_chunks = boom

        for _ in range(2):
            service.process_conversations()

        self.assertEqual(service.conversation_service.processed, [])
        self.assertEqual(MemoryChunkService._failed_attempts[conversation.uuid], 2)

    @mock.patch("src.service.memory_chunk_service._MAX_PROCESS_ATTEMPTS", 3)
    def test_exceeding_cap_marks_processed_and_stops_tracking(self):
        service = build_service()
        conversation = self._add_conversation(service)

        def boom(chunks):
            raise RuntimeError("summarizer down")

        service.memory_chunk_dao.insert_memory_chunks = boom

        for _ in range(3):
            service.process_conversations()

        self.assertEqual(service.conversation_service.processed, [conversation.uuid])
        self.assertNotIn(conversation.uuid, MemoryChunkService._failed_attempts)

    @mock.patch("src.service.memory_chunk_service._MAX_PROCESS_ATTEMPTS", 3)
    def test_success_after_failure_clears_the_counter(self):
        service = build_service()
        conversation = self._add_conversation(service)

        calls = {"n": 0}
        real_insert = service.memory_chunk_dao.insert_memory_chunks

        def flaky(chunks):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("transient")
            return real_insert(chunks)

        service.memory_chunk_dao.insert_memory_chunks = flaky

        service.process_conversations()
        self.assertEqual(MemoryChunkService._failed_attempts.get(conversation.uuid), 1)

        service.process_conversations()
        self.assertEqual(service.conversation_service.processed, [conversation.uuid])
        self.assertNotIn(conversation.uuid, MemoryChunkService._failed_attempts)

    @mock.patch("src.service.memory_chunk_service._MAX_PROCESS_ATTEMPTS", 3)
    def test_mark_processed_failure_is_also_tracked_and_logged(self):
        service = build_service()
        conversation = self._add_conversation(service)

        def boom(_uuid):
            raise RuntimeError("db down")

        service.conversation_service.mark_processed = boom

        service.process_conversations()

        self.assertEqual(MemoryChunkService._failed_attempts.get(conversation.uuid), 1)
        # Chunks were inserted even though marking processed failed.
        self.assertEqual(len(service.memory_chunk_dao.inserted), 2)


if __name__ == "__main__":
    unittest.main()
