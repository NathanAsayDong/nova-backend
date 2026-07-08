import unittest
from dataclasses import dataclass
from uuid import UUID, uuid4

from src.harness.agent_loop import AgentLoop, iter_sentence_chunks


@dataclass
class FakeTextBlock:
    text: str


@dataclass
class FakeMessage:
    content: list[FakeTextBlock]


class ConversationLoopTests(unittest.TestCase):
    def setUp(self):
        self.agent_loop = AgentLoop()
        self.conversation_id = uuid4()
        self.responses: list[str] = ["First reply", "Second reply"]
        self.prompts_seen: list[tuple[str, list | None]] = []

        def fake_get_response(prompt, role=None, context=None, tools=None):
            self.prompts_seen.append((prompt, list(context) if context is not None else None))
            text = self.responses.pop(0)
            return FakeMessage(content=[FakeTextBlock(text=text)])

        self.agent_loop.claude_service.get_response = fake_get_response

    def test_returns_model_text(self):
        result = self.agent_loop.conversation_loop("hello", self.conversation_id)
        self.assertEqual(result, "First reply")

    def test_history_grows_across_turns_with_same_uuid(self):
        first = self.agent_loop.conversation_loop("hello", self.conversation_id)
        second = self.agent_loop.conversation_loop("again", self.conversation_id)

        self.assertEqual(first, "First reply")
        self.assertEqual(second, "Second reply")
        self.assertEqual(len(self.prompts_seen), 2)
        self.assertEqual(self.prompts_seen[0][1], [])
        self.assertEqual(
            self.prompts_seen[1][1],
            [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "First reply"},
            ],
        )

    def test_different_uuids_have_isolated_history(self):
        other_id = uuid4()
        self.agent_loop.conversation_loop("hello", self.conversation_id)
        self.agent_loop.conversation_loop("other", other_id)

        history_a = self.agent_loop.conversations[self.conversation_id]
        history_b = self.agent_loop.conversations[other_id]

        self.assertEqual(len(history_a), 2)
        self.assertEqual(len(history_b), 2)
        self.assertEqual(history_a[0]["content"], "hello")
        self.assertEqual(history_b[0]["content"], "other")

    def test_new_conversation_id_returns_uuid(self):
        new_id = self.agent_loop.new_conversation_id()
        self.assertIsInstance(new_id, UUID)


class ConversationLoopStreamTests(unittest.TestCase):
    def setUp(self):
        self.agent_loop = AgentLoop()
        self.conversation_id = uuid4()

    def _set_stream(self, pieces: list[str]):
        def fake_stream(prompt, role=None, context=None, tools=None):
            yield from pieces

        self.agent_loop.claude_service.stream_response = fake_stream

    def test_yields_full_text_and_updates_history(self):
        self._set_stream(["Hello there. ", "How can I help you today?"])

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

    def test_empty_stream_leaves_history_untouched(self):
        self._set_stream([])

        chunks = list(
            self.agent_loop.conversation_loop_stream("hi", self.conversation_id)
        )

        self.assertEqual(chunks, [])
        self.assertEqual(self.agent_loop.conversations[self.conversation_id], [])

    def test_interrupted_stream_commits_partial_text(self):
        self._set_stream(
            ["This is the first full sentence right here. ", "Second sentence never finishes"]
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
        chunks = list(iter_sentence_chunks(iter(pieces), min_chars=5))
        self.assertEqual(chunks, ["Hello there.", "How are you today?", "Great."])

    def test_min_chars_merges_short_sentences(self):
        pieces = ["Hi. This is a longer sentence. And another one follows here."]
        chunks = list(iter_sentence_chunks(iter(pieces), min_chars=10))
        self.assertEqual(
            chunks,
            ["Hi. This is a longer sentence.", "And another one follows here."],
        )

    def test_trailing_text_without_punctuation_is_flushed(self):
        chunks = list(iter_sentence_chunks(iter(["no punctuation here"]), min_chars=5))
        self.assertEqual(chunks, ["no punctuation here"])


if __name__ == "__main__":
    unittest.main()
