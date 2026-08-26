import json
import unittest
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from prompting.prompt_source_prompt import PromptSourceEnum
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
    stop_reason: str = "end_turn"


@dataclass
class FakeToolUseBlock:
    id: str
    name: str
    input: dict
    type: str = "tool_use"


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
        # Memory injection is covered in its own suite; these tests
        # assert on prompts, so keep retrieval out of them.
        self.agent_loop.memory_retrieval_enabled = False
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
        def fake_stream(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
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
        # Assistant turns keep their content blocks so citations and server
        # tool results survive into follow-up requests.
        self.assertEqual(
            history,
            [
                {"role": "user", "content": "hi"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Hello there. How can I help you today?"}
                    ],
                },
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

    def test_server_tool_blocks_are_preserved_verbatim(self):
        """
        web_search_tool_result blocks carry encrypted_content that must go back
        to the API unchanged, so history keeps whatever the SDK handed us.
        """
        search_result_block = {
            "type": "web_search_tool_result",
            "tool_use_id": "srvtoolu_123",
            "content": [
                {
                    "type": "web_search_result",
                    "url": "https://example.com",
                    "title": "Example",
                    "encrypted_content": "ENCRYPTED_BLOB",
                }
            ],
        }
        cited_text_block = {
            "type": "text",
            "text": "The answer is 42.",
            "citations": [
                {
                    "type": "web_search_result_location",
                    "url": "https://example.com",
                    "title": "Example",
                    "encrypted_index": "ENCRYPTED_INDEX",
                    "cited_text": "42",
                }
            ],
        }

        def fake_stream(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            return FakeMessage(content=[search_result_block, cited_text_block])

        self.agent_loop.claude_service.stream_response = fake_stream

        list(self.agent_loop.conversation_loop_stream("q", self.conversation_id))

        blocks = self.agent_loop.conversations[self.conversation_id][1]["content"]
        self.assertEqual(blocks, [search_result_block, cited_text_block])

    def test_pause_turn_replays_assistant_message(self):
        """A paused server-side search continues by replaying the message."""
        responses = [
            FakeMessage(content=[{"type": "text", "text": "searching"}]),
            FakeMessage(content=[FakeTextBlock(text="All done now, here it is.")]),
        ]
        stop_reasons = ["pause_turn", "end_turn"]
        calls = {"n": 0}

        def fake_stream(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            index = calls["n"]
            calls["n"] += 1
            message = responses[index]
            message.stop_reason = stop_reasons[index]
            return message

        self.agent_loop.claude_service.stream_response = fake_stream

        chunks = list(self.agent_loop.conversation_loop_stream("q", self.conversation_id))

        self.assertEqual(calls["n"], 2)
        self.assertEqual(" ".join(chunks), "All done now, here it is.")

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
        self.assertTrue(
            history[1]["content"][0]["text"].startswith("This is the first full sentence")
        )


class PromptSourceTests(ConversationLoopStreamTests):
    """
    Every turn carries Nova's persona as the cached system prefix; the reply
    is additionally steered for the medium it will be delivered in.
    """

    def _capture_systems(self):
        systems: list = []

        def fake_stream(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            systems.append(system)
            return FakeMessage(content=[FakeTextBlock(text="Short answer.")])

        self.agent_loop.claude_service.stream_response = fake_stream
        return systems

    def test_chat_sends_persona_without_steer(self):
        systems = self._capture_systems()

        list(
            self.agent_loop.conversation_loop_events(
                "hi", self.conversation_id, prompt_source=PromptSourceEnum.CHAT_PROMPT
            )
        )

        # CHAT_PROMPT is empty, so only the persona block is sent.
        self.assertEqual(len(systems), 1)
        blocks = systems[0]
        self.assertEqual(len(blocks), 1)
        self.assertIn("Nova", blocks[0]["text"])
        # The stable persona carries the cache breakpoint.
        self.assertEqual(blocks[0]["cache_control"], {"type": "ephemeral"})

    def test_speech_appends_brevity_steer_after_persona(self):
        systems = self._capture_systems()

        list(
            self.agent_loop.conversation_loop_events(
                "hi", self.conversation_id, prompt_source=PromptSourceEnum.SPEECH_PROMPT
            )
        )

        self.assertEqual(len(systems), 1)
        blocks = systems[0]
        self.assertEqual(len(blocks), 2)
        self.assertIn("Nova", blocks[0]["text"])
        self.assertIn("voice mode", blocks[1]["text"])
        self.assertIn("brief", blocks[1]["text"])
        # The steer varies per medium, so it must sit AFTER the cache
        # breakpoint — a cached steer would invalidate the prefix whenever
        # the user switches between chat and voice.
        self.assertNotIn("cache_control", blocks[1])

    def test_voice_wrapper_defaults_to_speech(self):
        systems = self._capture_systems()

        list(self.agent_loop.conversation_loop_stream("hi", self.conversation_id))

        self.assertIn("brief", systems[0][-1]["text"])

    def test_chat_default_is_unsteered(self):
        systems = self._capture_systems()

        list(self.agent_loop.conversation_loop_events("hi", self.conversation_id))

        self.assertEqual(len(systems[0]), 1)

    def test_steer_never_enters_history(self):
        """
        Chat and speech share one conversation, so a spoken turn's brevity
        instruction must not linger and shorten later typed replies.
        """
        self._capture_systems()

        list(
            self.agent_loop.conversation_loop_events(
                "hi", self.conversation_id, prompt_source=PromptSourceEnum.SPEECH_PROMPT
            )
        )

        history = self.agent_loop.conversations[self.conversation_id]
        serialized = json.dumps(history)
        self.assertNotIn("voice mode", serialized)
        self.assertNotIn("brief", serialized)


class ArtifactTests(unittest.TestCase):
    def test_edit_produces_diff_artifact(self):
        artifact = AgentLoop._artifact_for_tool(
            "edit_project_file",
            {"path": "app.py", "command": "sed ..."},
            {"path": "app.py", "diff": "-a\n+b", "exit_code": 0},
        )
        self.assertEqual(artifact["kind"], "diff")
        self.assertEqual(artifact["title"], "app.py")
        self.assertEqual(artifact["content"], "-a\n+b")

    def test_edit_without_changes_has_no_artifact(self):
        self.assertIsNone(
            AgentLoop._artifact_for_tool(
                "edit_project_file", {"path": "app.py"}, {"diff": "", "exit_code": 1}
            )
        )

    def test_write_uses_argument_content_and_infers_language(self):
        artifact = AgentLoop._artifact_for_tool(
            "write_project_file",
            {"path": "src/main.ts", "content": "export const a = 1"},
            {"path": "src/main.ts", "status": "created"},
        )
        self.assertEqual(artifact["kind"], "file")
        self.assertEqual(artifact["language"], "typescript")
        self.assertEqual(artifact["content"], "export const a = 1")

    def test_read_uses_result_content(self):
        artifact = AgentLoop._artifact_for_tool(
            "read_project_file", {"path": "a.py"}, {"path": "a.py", "content": "x = 1"}
        )
        self.assertEqual(artifact["content"], "x = 1")
        self.assertEqual(artifact["language"], "python")

    def test_terminal_merges_streams_and_keeps_exit_code(self):
        artifact = AgentLoop._artifact_for_tool(
            "run_terminal_command",
            {"command": "ls"},
            {"stdout": "a.py\n", "stderr": "warn\n", "exit_code": 2},
        )
        self.assertEqual(artifact["kind"], "terminal")
        self.assertIn("a.py", artifact["content"])
        self.assertIn("warn", artifact["content"])
        self.assertEqual(artifact["exitCode"], 2)

    def test_silent_command_has_no_artifact(self):
        self.assertIsNone(
            AgentLoop._artifact_for_tool(
                "run_terminal_command", {"command": "true"}, {"stdout": "", "stderr": ""}
            )
        )

    def test_tool_without_visual_output_has_no_artifact(self):
        self.assertIsNone(
            AgentLoop._artifact_for_tool("list_projects", {}, [{"id": 1}])
        )


class EventStreamTests(ConversationLoopStreamTests):
    def test_events_carry_text_type(self):
        self._set_stream("Hello there. How can I help you today?")

        events = list(
            self.agent_loop.conversation_loop_events("hi", self.conversation_id)
        )

        chunks = [event for event in events if event["type"] == "text"]
        self.assertEqual(
            " ".join(event["text"] for event in chunks),
            "Hello there. How can I help you today?",
        )

    def test_text_final_carries_unstripped_text(self):
        """Sentence chunks lose newlines; text_final restores them for markdown."""
        markdown = (
            "Here is the summary of what happened today.\n"
            "\n"
            "- The first item is fairly long right here.\n"
            "- The second item is also long enough to split.\n"
        )
        self._set_stream(markdown)

        events = list(
            self.agent_loop.conversation_loop_events("hi", self.conversation_id)
        )

        finals = [event for event in events if event["type"] == "text_final"]
        self.assertEqual(len(finals), 1)
        self.assertEqual(finals[0]["text"], markdown)

        # Chunking really does flatten the list into one line, which is the
        # whole reason text_final exists.
        chunked = " ".join(e["text"] for e in events if e["type"] == "text")
        self.assertNotEqual(chunked, markdown)
        self.assertNotIn("\n- The second item", chunked)

    def test_text_wrapper_filters_non_text_events(self):
        """The voice path speaks text and status, never tool calls or artifacts."""
        events = [
            {"type": "status_text", "text": "Let me check."},
            {"type": "tool_call", "tool": "run_terminal_command", "input": {}},
            {"type": "text", "text": "Spoken."},
            {"type": "artifact", "kind": "diff", "content": "-a\n+b"},
        ]
        self.agent_loop.conversation_loop_events = lambda *_a, **_k: iter(events)

        spoken = list(
            self.agent_loop.conversation_loop_stream("hi", self.conversation_id)
        )

        self.assertEqual(spoken, ["Let me check.", "Spoken."])


class StatusTextTests(ConversationLoopStreamTests):
    """
    The text Claude writes before its first tool call is surfaced once as a
    status_text event (the spoken "on it" acknowledgment); text on later tool
    rounds is narration and must stay silent.
    """

    def _set_responses(self, responses: list[FakeMessage]):
        queue = list(responses)

        def fake_stream(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            return queue.pop(0)

        self.agent_loop.claude_service.stream_response = fake_stream

    @staticmethod
    def _tool_round(text: str | None, call_id: str) -> FakeMessage:
        blocks: list = []
        if text:
            blocks.append(FakeTextBlock(text=text))
        # The tool is unknown to ToolService, so the loop records an error
        # result and continues — enough to drive multi-round turns without
        # real tools.
        blocks.append(FakeToolUseBlock(id=call_id, name="missing_tool", input={}))
        return FakeMessage(content=blocks)

    def test_pre_tool_text_is_yielded_once_as_status(self):
        self._set_responses(
            [
                self._tool_round("Let me pull that up for you.", "t1"),
                FakeMessage(content=[FakeTextBlock(text="Here is your answer, sir.")]),
            ]
        )

        events = list(
            self.agent_loop.conversation_loop_events("do the thing", self.conversation_id)
        )

        statuses = [e for e in events if e["type"] == "status_text"]
        self.assertEqual(statuses, [
            {"type": "status_text", "text": "Let me pull that up for you."}
        ])
        # The acknowledgment precedes the final spoken text.
        types = [e["type"] for e in events]
        self.assertLess(types.index("status_text"), types.index("text"))

    def test_later_tool_rounds_stay_silent(self):
        self._set_responses(
            [
                self._tool_round("Checking that now.", "t1"),
                self._tool_round("Now cross-referencing the results.", "t2"),
                FakeMessage(content=[FakeTextBlock(text="All done, here it is.")]),
            ]
        )

        events = list(
            self.agent_loop.conversation_loop_events("do the thing", self.conversation_id)
        )

        statuses = [e["text"] for e in events if e["type"] == "status_text"]
        self.assertEqual(statuses, ["Checking that now."])

    def test_silent_first_round_can_speak_on_a_later_round(self):
        """One acknowledgment per turn — not necessarily from round one."""
        self._set_responses(
            [
                self._tool_round(None, "t1"),
                self._tool_round("Still digging into this one.", "t2"),
                FakeMessage(content=[FakeTextBlock(text="Found it, here you go.")]),
            ]
        )

        events = list(
            self.agent_loop.conversation_loop_events("do the thing", self.conversation_id)
        )

        statuses = [e["text"] for e in events if e["type"] == "status_text"]
        self.assertEqual(statuses, ["Still digging into this one."])

    def test_no_tools_means_no_status(self):
        self._set_responses(
            [FakeMessage(content=[FakeTextBlock(text="Doing great, thanks for asking.")])]
        )

        events = list(
            self.agent_loop.conversation_loop_events("hey how are you", self.conversation_id)
        )

        self.assertEqual([e for e in events if e["type"] == "status_text"], [])

    def test_status_text_stays_in_history_for_the_model(self):
        self._set_responses(
            [
                self._tool_round("Let me pull that up for you.", "t1"),
                FakeMessage(content=[FakeTextBlock(text="Here is your answer, sir.")]),
            ]
        )

        list(
            self.agent_loop.conversation_loop_events("do the thing", self.conversation_id)
        )

        history = self.agent_loop.conversations[self.conversation_id]
        first_assistant = next(m for m in history if m["role"] == "assistant")
        self.assertEqual(
            first_assistant["content"][0],
            {"type": "text", "text": "Let me pull that up for you."},
        )


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
