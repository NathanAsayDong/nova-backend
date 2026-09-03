import json
import unittest
from types import SimpleNamespace
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from prompting.prompt_source_prompt import PromptSourceEnum
from src.harness.agent_loop import AgentLoop
from src.service.claude_service import TurnStream
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
            return TurnStream.completed(FakeMessage(content=blocks))

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
            return TurnStream.completed(
                FakeMessage(content=[search_result_block, cited_text_block])
            )

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
            return TurnStream.completed(message)

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
            return TurnStream.completed(
                FakeMessage(content=[FakeTextBlock(text="Short answer.")])
            )

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

    def test_speech_appends_split_reply_steer_after_persona(self):
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
        self.assertIn("<speak></speak>", blocks[1]["text"])
        self.assertIn("two sentences", blocks[1]["text"])
        # The steer varies per medium, so it must sit AFTER the cache
        # breakpoint — a cached steer would invalidate the prefix whenever
        # the user switches between chat and voice.
        self.assertNotIn("cache_control", blocks[1])

    def test_voice_wrapper_defaults_to_speech(self):
        systems = self._capture_systems()

        list(self.agent_loop.conversation_loop_stream("hi", self.conversation_id))

        self.assertIn("<speak></speak>", systems[0][-1]["text"])

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
        self.assertNotIn("<speak></speak>", serialized)
        self.assertNotIn("read aloud", serialized)


class SpokenTrackTests(unittest.TestCase):
    """
    The event stream carries two tracks, and a turn is only correct when they
    disagree in the right direction: short in the ear, complete on screen.
    """

    LONG_REPLY = (
        "<speak>Both checks passed.</speak>\n\n"
        "## Results\n\n"
        "The unit suite passed in 4.2 seconds. The integration suite passed in "
        "31 seconds. Coverage held at 87 percent. Nothing regressed against "
        "the previous run, and the flaky socket test stayed green this time.\n\n"
        "```bash\npytest -q\n```\n"
    )

    def setUp(self):
        self.agent_loop = AgentLoop()
        self.agent_loop.memory_retrieval_enabled = False
        self.conversation_id = uuid4()
        tool_service = ToolService.__new__(ToolService)
        tool_service.tool_dao = FakeToolDao()
        self.agent_loop.tool_service = tool_service
        self.conversation_service = FakeConversationService()
        self.agent_loop.conversation_service = self.conversation_service

    def _set_stream(self, text: str):
        def fake_stream(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            return TurnStream.completed(FakeMessage(content=[FakeTextBlock(text=text)]))

        self.agent_loop.claude_service.stream_response = fake_stream

    def _run(self, prompt_source):
        return list(
            self.agent_loop.conversation_loop_events(
                "how did the tests go",
                self.conversation_id,
                prompt_source=prompt_source,
            )
        )

    def test_speech_turn_speaks_the_short_line_and_shows_the_long_one(self):
        self._set_stream(self.LONG_REPLY)

        events = self._run(PromptSourceEnum.SPEECH_PROMPT)

        spoken = [event for event in events if event["type"] == "speech_text"]
        self.assertEqual(len(spoken), 1)
        self.assertEqual(spoken[0]["text"], "Both checks passed.")
        self.assertEqual(spoken[0]["role"], "final")

        final = next(event for event in events if event["type"] == "text_final")
        self.assertIn("Coverage held at 87 percent", final["text"])
        self.assertIn("```bash", final["text"])

    def test_the_spoken_line_arrives_before_the_prose(self):
        """
        TTS is the only part of a turn the user waits on in real time, so the
        line that feeds it has to reach the transport first.
        """
        self._set_stream(self.LONG_REPLY)

        types = [event["type"] for event in self._run(PromptSourceEnum.SPEECH_PROMPT)]

        self.assertEqual(types[0], "speech_text")
        self.assertIn("text", types)

    def test_written_answer_is_what_gets_persisted(self):
        self._set_stream(self.LONG_REPLY)

        self._run(PromptSourceEnum.SPEECH_PROMPT)

        nova_rows = [
            content
            for _uuid, role, content in self.conversation_service.recorded
            if role is MessageRole.NOVA
        ]
        self.assertEqual(len(nova_rows), 1)
        self.assertIn("Coverage held at 87 percent", nova_rows[0])
        self.assertNotIn("<speak>", nova_rows[0])

    def test_no_speak_block_falls_back_to_the_opening_sentences(self):
        """
        The ceiling cannot depend on the model remembering the format, so a
        reply that ignores it is summarized rather than read out whole.
        """
        self._set_stream(
            "The migration finished. It touched 12 tables. "
            "Nothing needs your attention. Here is the full log."
        )

        events = self._run(PromptSourceEnum.SPEECH_PROMPT)

        spoken = next(event for event in events if event["type"] == "speech_text")
        self.assertEqual(
            spoken["text"], "The migration finished. It touched 12 tables."
        )
        final = next(event for event in events if event["type"] == "text_final")
        self.assertIn("Here is the full log.", final["text"])

    def test_chat_turn_has_no_spoken_track_at_all(self):
        self._set_stream("A perfectly ordinary markdown answer.\n\n- one\n- two")

        events = self._run(PromptSourceEnum.CHAT_PROMPT)

        self.assertEqual([e for e in events if e["type"] == "speech_text"], [])
        final = next(event for event in events if event["type"] == "text_final")
        self.assertIn("- one\n- two", final["text"])

    def test_call_turn_has_no_spoken_track_because_it_has_no_screen(self):
        """
        A phone call speaks its `text` events directly. Emitting a second
        track there would say everything twice.
        """
        self._set_stream("Two checks passed.")

        events = self._run(PromptSourceEnum.CALL_PROMPT)

        self.assertEqual([e for e in events if e["type"] == "speech_text"], [])

    def test_tool_round_speaks_a_clamped_acknowledgment(self):
        replies = [
            FakeMessage(
                content=[
                    FakeTextBlock(
                        text=(
                            "Let me pull that up. I will check the runner. "
                            "Then the logs, then the coverage report."
                        )
                    ),
                    FakeToolUseBlock(id="t1", name="missing_tool", input={}),
                ]
            ),
            FakeMessage(content=[FakeTextBlock(text="<speak>All clear.</speak>Details.")]),
        ]

        def fake_stream(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            return TurnStream.completed(replies.pop(0))

        self.agent_loop.claude_service.stream_response = fake_stream

        events = self._run(PromptSourceEnum.SPEECH_PROMPT)

        status = next(event for event in events if event["type"] == "status_text")
        # The screen gets the whole acknowledgment...
        self.assertIn("coverage report", status["text"])
        # ...the speaker gets two sentences of it.
        ack = next(
            event
            for event in events
            if event["type"] == "speech_text" and event["role"] == "status"
        )
        self.assertEqual(
            ack["text"], "Let me pull that up. I will check the runner."
        )


class ScriptedTurnStream:
    """
    A turn whose deltas arrive one at a time, on demand.

    Records what has actually been pulled, which is what lets a test ask the
    question that matters here: had the model finished writing when Nova
    started speaking?
    """

    def __init__(self, deltas: list[str], message=None):
        self.deltas = list(deltas)
        self.consumed: list[str] = []
        self._message = message or FakeMessage(
            content=[FakeTextBlock(text="".join(deltas))]
        )

    def __iter__(self):
        for delta in self.deltas:
            self.consumed.append(delta)
            yield delta

    @property
    def message(self):
        return self._message

    @property
    def finished(self) -> bool:
        return len(self.consumed) == len(self.deltas)


class StreamedSpeechTests(unittest.TestCase):
    """
    The spoken line has to leave before the written answer is finished.

    That is the whole point of putting `<speak>` first: two sentences are done
    in a fraction of the time a markdown answer takes, and a voice turn should
    not pay for the difference.
    """

    # Split the way a real stream splits — mid-word, mid-tag.
    DELTAS = [
        "<spe", "ak>Both checks", " passed.</spe", "ak>",
        "\n\n## Results\n\nThe unit suite passed in 4.2 seconds. ",
        "The integration suite passed in 31 seconds. ",
        "Coverage held at 87 percent.",
    ]

    def setUp(self):
        self.agent_loop = AgentLoop()
        self.agent_loop.memory_retrieval_enabled = False
        self.conversation_id = uuid4()
        tool_service = ToolService.__new__(ToolService)
        tool_service.tool_dao = FakeToolDao()
        self.agent_loop.tool_service = tool_service
        self.agent_loop.conversation_service = FakeConversationService()

    def _script(self, deltas, message=None) -> ScriptedTurnStream:
        stream = ScriptedTurnStream(deltas, message)

        def fake_stream(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            return stream

        self.agent_loop.claude_service.stream_response = fake_stream
        return stream

    def _events(self, prompt_source=PromptSourceEnum.SPEECH_PROMPT):
        return self.agent_loop.conversation_loop_events(
            "how did the tests go", self.conversation_id, prompt_source=prompt_source
        )

    def test_speech_goes_out_before_the_model_stops_writing(self):
        stream = self._script(self.DELTAS)
        events = self._events()

        first = next(events)

        self.assertEqual(first["type"], "speech_text")
        self.assertEqual(first["text"], "Both checks passed.")
        # The assertion that matters: deltas are still unread. Under the old
        # code this event could not exist until the last one had arrived.
        self.assertFalse(stream.finished)
        self.assertEqual(stream.consumed, self.DELTAS[:4])

        list(events)  # drain, so the turn finishes cleanly

    def test_the_written_answer_still_arrives_whole(self):
        self._script(self.DELTAS)

        events = list(self._events())

        final = next(event for event in events if event["type"] == "text_final")
        self.assertIn("## Results", final["text"])
        self.assertIn("Coverage held at 87 percent", final["text"])
        self.assertNotIn("<speak>", final["text"])

    def test_a_line_spoken_early_is_not_spoken_again_at_the_end(self):
        self._script(self.DELTAS)

        events = list(self._events())

        spoken = [event for event in events if event["type"] == "speech_text"]
        self.assertEqual(len(spoken), 1)

    def test_a_chat_turn_never_watches_the_stream(self):
        self._script(self.DELTAS)

        events = list(self._events(PromptSourceEnum.CHAT_PROMPT))

        self.assertEqual([e for e in events if e["type"] == "speech_text"], [])

    def test_an_unclosed_block_falls_back_to_the_end_of_turn_path(self):
        """
        Nothing fires mid-stream, but the turn still says something: the
        end-of-turn split handles the unclosed tag.
        """
        self._script(["<speak>Still ", "talking and never closing"])

        events = list(self._events())

        spoken = [event for event in events if event["type"] == "speech_text"]
        self.assertEqual(len(spoken), 1)
        self.assertEqual(spoken[0]["text"], "Still talking and never closing")

    def test_a_reply_with_no_block_still_speaks_from_the_end(self):
        self._script(["The migration finished. ", "It touched 12 tables. ", "Details below."])

        events = list(self._events())

        spoken = [event for event in events if event["type"] == "speech_text"]
        self.assertEqual(len(spoken), 1)
        self.assertEqual(
            spoken[0]["text"], "The migration finished. It touched 12 tables."
        )


class FailureSpeechTests(unittest.TestCase):
    """
    Now that only `speech_text` reaches TTS, the loop's own failure messages
    have to travel on it too — otherwise a voice turn that gives up gives up
    silently, and the user is left waiting for an answer that already stopped.
    """

    def setUp(self):
        self.agent_loop = AgentLoop()
        self.agent_loop.memory_retrieval_enabled = False
        self.conversation_id = uuid4()
        tool_service = ToolService.__new__(ToolService)
        tool_service.tool_dao = FakeToolDao()
        self.agent_loop.tool_service = tool_service
        self.agent_loop.conversation_service = FakeConversationService()

    def _explode(self, error: Exception):
        def fake_stream(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            raise error

        self.agent_loop.claude_service.stream_response = fake_stream

    def _events(self, prompt_source):
        return list(
            self.agent_loop.conversation_loop_events(
                "hi", self.conversation_id, prompt_source=prompt_source
            )
        )

    def test_a_backend_timeout_is_said_out_loud(self):
        self._explode(TimeoutError())

        events = self._events(PromptSourceEnum.SPEECH_PROMPT)

        spoken = next(event for event in events if event["type"] == "speech_text")
        self.assertIn("timeout", spoken["text"])
        # And still shown, so the transcript records what happened.
        self.assertTrue(any(event["type"] == "text" for event in events))

    def test_a_crash_is_said_out_loud(self):
        self._explode(RuntimeError("claude exploded"))

        events = self._events(PromptSourceEnum.SPEECH_PROMPT)

        spoken = next(event for event in events if event["type"] == "speech_text")
        self.assertIn("claude exploded", spoken["text"])

    def test_a_chat_failure_stays_silent(self):
        self._explode(RuntimeError("claude exploded"))

        events = self._events(PromptSourceEnum.CHAT_PROMPT)

        self.assertEqual([e for e in events if e["type"] == "speech_text"], [])
        self.assertTrue(any(event["type"] == "text" for event in events))

    def test_a_turn_that_already_spoke_does_not_announce_its_own_failure(self):
        """
        The stream got far enough to say "here you go" and then died. Saying
        "I had to stop" after it would be a second, contradictory answer —
        the failure belongs on screen only.
        """
        class DyingStream:
            def __iter__(self):
                yield "<speak>Here you go.</speak>"
                raise RuntimeError("connection reset")

            @property
            def message(self):
                raise AssertionError("never reached")

        def fake_stream(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            return DyingStream()

        self.agent_loop.claude_service.stream_response = fake_stream

        events = self._events(PromptSourceEnum.SPEECH_PROMPT)

        spoken = [event for event in events if event["type"] == "speech_text"]
        self.assertEqual(len(spoken), 1)
        self.assertEqual(spoken[0]["text"], "Here you go.")
        self.assertTrue(
            any("connection reset" in event.get("text", "") for event in events)
        )


class TurnStreamTests(unittest.TestCase):
    def test_a_completed_turn_replays_its_text(self):
        stream = TurnStream.completed(
            FakeMessage(content=[FakeTextBlock(text="all of it")])
        )

        self.assertEqual(list(stream), ["all of it"])
        self.assertEqual(stream.message.content[0].text, "all of it")

    def test_a_completed_turn_with_no_text_yields_nothing(self):
        stream = TurnStream.completed(FakeMessage(content=[]))

        self.assertEqual(list(stream), [])

    def test_a_live_turn_has_no_message_until_it_is_drained(self):
        stream = TurnStream(open_stream=lambda: None)

        with self.assertRaises(RuntimeError):
            stream.message

    def test_a_live_turn_reads_deltas_then_exposes_the_message(self):
        """
        Shaped like the Anthropic SDK's stream: a context manager yielding an
        object with `text_stream` and `get_final_message()`.

        Pinned here because `text_stream` is an instance attribute the SDK
        assigns in __init__ and only annotates on the class — it does not
        exist on the class object, so nothing short of an actual call would
        notice it going away.
        """
        message = FakeMessage(content=[FakeTextBlock(text="ab")])
        closed = {"count": 0}

        class FakeSdkStream:
            def __init__(self):
                self.text_stream = iter(["a", "", "b"])

            def get_final_message(self):
                return message

        class FakeManager:
            def __enter__(inner):
                return sdk_stream

            def __exit__(inner, *exc):
                closed["count"] += 1
                return False

        sdk_stream = FakeSdkStream()
        stream = TurnStream(open_stream=FakeManager)

        # Empty deltas are dropped; the connection is released on the way out.
        self.assertEqual(list(stream), ["a", "b"])
        self.assertIs(stream.message, message)
        self.assertEqual(closed["count"], 1)

    def test_a_live_turn_refuses_a_second_read(self):
        class FakeManager:
            def __enter__(inner):
                return SimpleNamespace(
                    text_stream=iter(["x"]),
                    get_final_message=lambda: FakeMessage(content=[]),
                )

            def __exit__(inner, *exc):
                return False

        stream = TurnStream(open_stream=FakeManager)
        list(stream)

        with self.assertRaises(RuntimeError):
            list(stream)


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
            return TurnStream.completed(queue.pop(0))

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
