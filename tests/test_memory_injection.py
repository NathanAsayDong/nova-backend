"""
Coverage for memory that arrives without the model asking for it: the
relevance gate on retrieval, and how the block reaches the prompt.
"""

import unittest
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from prompting.prompt_source_prompt import PromptSourceEnum
from src.harness.agent_loop import AgentLoop
from src.model.conversation import Conversation
from src.model.memory_chunk import MemoryChunk, MemoryMatch
from src.model.message import MessageRole
from src.service.claude_service import TurnStream
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


class FakeUpdateService:
    """
    Stands in for UpdateService in the notification-queue path of
    _conversation_turn: a fixed list of unviewed updates, and a record of
    which ones got marked delivered (mark_update_viewed).
    """

    def __init__(self, unviewed=()):
        self._unviewed = {entry["id"]: dict(entry) for entry in unviewed}
        self.marked_viewed: list[int] = []

    def get_unviewed_updates(self):
        return [
            entry
            for entry in self._unviewed.values()
            if entry["id"] not in self.marked_viewed
        ]

    def mark_update_viewed(self, update_id):
        self.marked_viewed.append(update_id)
        return self._unviewed.get(update_id)


def notification(
    id,
    kind="coding_task",
    status="success",
    message="PR opened.",
    link=None,
    conversation_uuid=None,
    project_id=None,
    created_at=None,
):
    return {
        "id": id,
        "kind": kind,
        "status": status,
        "update_message": message,
        "link": link,
        "conversation_uuid": str(conversation_uuid) if conversation_uuid else None,
        "project": {"id": project_id} if project_id is not None else None,
        "created_at": created_at.isoformat() if created_at else None,
    }


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
        # Empty by default: most of this file's tests are about memory, not
        # notifications, and must see an untouched prompt either way --
        # see PendingNotificationsInjectionTests below for "empty queue adds
        # nothing to context" and the rest of the notification coverage.
        self.update_service = FakeUpdateService()
        self.agent_loop.update_service = self.update_service
        self.sent_messages = []

        def fake_stream(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            self.sent_messages.append(list(context or []))
            return TurnStream.completed(
                FakeMessage(content=[FakeTextBlock(text="Friday, as always.")])
            )

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


class PendingNotificationsInjectionTests(MemoryInjectionTests):
    """
    The notification queue: finished background-agent / coding-task /
    scheduled-task work injected into the start of the next turn, in any
    conversation, then marked delivered so it is never repeated.

    Subclasses MemoryInjectionTests purely to reuse its setUp/run_turn/
    first_user_message plumbing — this is the same injection point
    (_conversation_turn -> _augment), just the other block.
    """

    def test_empty_queue_adds_nothing_to_context(self):
        # setUp's FakeUpdateService starts empty; this is the explicit case.
        self.run_turn()
        content = self.first_user_message()
        self.assertNotIn("<pending_notifications>", content)
        self.assertEqual(content, "when do I deploy")

    def test_undelivered_notification_is_injected_and_marked_delivered(self):
        self.update_service._unviewed[7] = notification(
            7, kind="coding_task", status="success", message="PR #42 merged."
        )

        self.run_turn()

        content = self.first_user_message()
        self.assertIn("<pending_notifications>", content)
        self.assertIn("PR #42 merged.", content)
        self.assertIn("succeeded", content)
        # Delivered means marked viewed, immediately -- not on some later
        # confirmation that the model actually said something about it.
        self.assertEqual(self.update_service.marked_viewed, [7])

    def test_failed_notification_is_worded_as_failed(self):
        self.update_service._unviewed[9] = notification(
            9, kind="scheduled_task", status="failed", message="Build check failed."
        )
        self.run_turn()
        content = self.first_user_message()
        self.assertIn("failed", content)
        self.assertIn("Build check failed.", content)

    def test_multiple_notifications_all_appear_once_each(self):
        self.update_service._unviewed[1] = notification(1, message="Agent run A done.")
        self.update_service._unviewed[2] = notification(2, message="Agent run B done.")

        self.run_turn()

        content = self.first_user_message()
        self.assertIn("Agent run A done.", content)
        self.assertIn("Agent run B done.", content)
        self.assertEqual(sorted(self.update_service.marked_viewed), [1, 2])

    def test_a_second_turn_does_not_repeat_an_already_delivered_notification(self):
        self.update_service._unviewed[7] = notification(7, message="PR #42 merged.")

        self.run_turn()
        first_content = self.first_user_message()
        self.sent_messages.clear()
        self.run_turn(prompt="anything else going on?")
        # History keeps growing across turns on the same agent_loop/
        # conversation, so the second call's context carries both turns --
        # its OWN new message is the last one, not the first.
        second_content = self.sent_messages[0][-1]["content"]

        self.assertIn("PR #42 merged.", first_content)
        self.assertNotIn("<pending_notifications>", second_content)
        self.assertNotIn("PR #42 merged.", second_content)

    def test_updates_with_no_kind_are_not_treated_as_notifications(self):
        """A plain badge-only update (no kind) is UpdateService's existing
        territory -- get_unviewed_updates/mark_all_updates_viewed, read on
        request. It must not be swept into the turn-injection path."""
        self.update_service._unviewed[3] = {
            "id": 3,
            "kind": None,
            "status": None,
            "update_message": "Unrelated badge-only update.",
            "link": None,
        }
        self.run_turn()
        content = self.first_user_message()
        self.assertNotIn("<pending_notifications>", content)
        self.assertNotIn("Unrelated badge-only update.", content)
        self.assertEqual(self.update_service.marked_viewed, [])

    def test_a_failing_notification_check_does_not_take_the_turn_down(self):
        def boom():
            raise RuntimeError("db down")

        self.agent_loop.update_service.get_unviewed_updates = boom
        events = self.run_turn()
        self.assertEqual(self.first_user_message(), "when do I deploy")
        self.assertTrue(any(event["type"] == "text" for event in events))

    def test_link_is_included_when_present(self):
        self.update_service._unviewed[7] = notification(
            7, message="PR opened.", link="https://example.com/pr/42"
        )
        self.run_turn()
        self.assertIn("https://example.com/pr/42", self.first_user_message())

    def test_notifications_come_before_memory_in_the_prompt(self):
        self.update_service._unviewed[7] = notification(7, message="PR #42 merged.")
        self.use_memory("- Nate deploys on Fridays.")

        self.run_turn()

        content = self.first_user_message()
        self.assertLess(
            content.index("<pending_notifications>"), content.index("<recalled_memory>")
        )

    def test_injection_requires_no_explicit_trigger(self):
        """
        There is no flag, header, or special first word that turns this
        check on -- every call to run_turn here uses a plain prompt with no
        trigger of any kind, and the notification still surfaces. This test
        exists to make that property explicit rather than merely implicit
        in every other test in this class.
        """
        self.update_service._unviewed[7] = notification(7, message="PR #42 merged.")
        self.run_turn(prompt="hey")
        self.assertIn("<pending_notifications>", self.first_user_message())


class NotificationScopingTests(PendingNotificationsInjectionTests):
    """
    An update is relevant to this turn's conversation when it matches this
    conversation_uuid, matches this conversation's project, or carries no
    scope at all -- and irrelevant (held for whatever turn it belongs to)
    otherwise. See AgentLoop._notification_scope_matches.
    """

    def test_matching_conversation_uuid_is_included(self):
        self.update_service._unviewed[1] = notification(
            1, message="Spawned from here.", conversation_uuid=self.conversation_id
        )
        self.run_turn()
        self.assertIn("Spawned from here.", self.first_user_message())

    def test_matching_project_is_included(self):
        self.conversation_service.project_id = 9
        self.update_service._unviewed[2] = notification(
            2, message="Same project coding task.", project_id=9
        )
        self.run_turn()
        self.assertIn("Same project coding task.", self.first_user_message())

    def test_scope_less_update_is_included(self):
        self.update_service._unviewed[3] = notification(
            3, message="Global responsibility follow-up."
        )
        self.run_turn()
        self.assertIn("Global responsibility follow-up.", self.first_user_message())

    def test_other_conversation_and_other_project_is_excluded(self):
        self.conversation_service.project_id = 9
        self.update_service._unviewed[4] = notification(
            4,
            message="Someone else's thread.",
            conversation_uuid=uuid4(),
            project_id=123,
        )
        self.run_turn()
        content = self.first_user_message()
        self.assertNotIn("Someone else's thread.", content)
        self.assertNotIn("<pending_notifications>", content)
        # Left unviewed for whichever turn it actually belongs to.
        self.assertEqual(self.update_service.marked_viewed, [])

    def test_different_users_update_is_excluded_via_scope(self):
        # This fixture has no per-user id on Update (Nova is single-tenant
        # today), so "a different user's update" is modeled the same way as
        # any other out-of-scope row: a conversation_uuid and project that
        # belong to someone else's thread. Scoping excludes it exactly like
        # the cross-conversation/cross-project case above.
        self.update_service._unviewed[5] = notification(
            5,
            message="Not for this conversation.",
            conversation_uuid=uuid4(),
            project_id=999,
        )
        self.run_turn()
        self.assertNotIn("Not for this conversation.", self.first_user_message())


class NotificationRecencyTests(PendingNotificationsInjectionTests):
    """
    The 24h-or-this-conversation rule: a project-scoped or scope-less update
    older than 24h is stale backlog and held back, but one tied to THIS
    still-open conversation surfaces no matter its age. See
    AgentLoop._notification_is_eligible.
    """

    def test_old_update_scoped_to_this_conversation_still_surfaces(self):
        ancient = datetime.now(timezone.utc) - timedelta(days=30)
        self.update_service._unviewed[1] = notification(
            1,
            message="Ancient but still this thread.",
            conversation_uuid=self.conversation_id,
            created_at=ancient,
        )
        self.run_turn()
        self.assertIn("Ancient but still this thread.", self.first_user_message())

    def test_old_project_scoped_update_is_held_back(self):
        self.conversation_service.project_id = 9
        stale = datetime.now(timezone.utc) - timedelta(hours=25)
        self.update_service._unviewed[2] = notification(
            2, message="Stale project backlog.", project_id=9, created_at=stale
        )
        self.run_turn()
        content = self.first_user_message()
        self.assertNotIn("Stale project backlog.", content)
        self.assertEqual(self.update_service.marked_viewed, [])

    def test_recent_project_scoped_update_surfaces(self):
        self.conversation_service.project_id = 9
        fresh = datetime.now(timezone.utc) - timedelta(hours=1)
        self.update_service._unviewed[3] = notification(
            3, message="Fresh project update.", project_id=9, created_at=fresh
        )
        self.run_turn()
        self.assertIn("Fresh project update.", self.first_user_message())

    def test_old_scope_less_update_is_held_back(self):
        stale = datetime.now(timezone.utc) - timedelta(hours=48)
        self.update_service._unviewed[4] = notification(
            4, message="Old global update.", created_at=stale
        )
        self.run_turn()
        self.assertNotIn("Old global update.", self.first_user_message())


class NotificationCapTests(PendingNotificationsInjectionTests):
    """Per-turn cap at 5 items, with a trailing "+N more" count. See
    AgentLoop._select_notifications / _build_notifications_block."""

    def _fill(self, count):
        for i in range(count):
            self.update_service._unviewed[i] = notification(i, message=f"Item {i} done.")

    def test_exactly_five_shows_all_five_with_no_overflow_note(self):
        self._fill(5)
        self.run_turn()
        content = self.first_user_message()
        for i in range(5):
            self.assertIn(f"Item {i} done.", content)
        self.assertNotIn("more update", content)
        self.assertEqual(sorted(self.update_service.marked_viewed), list(range(5)))

    def test_more_than_five_caps_at_five_and_reports_the_remainder(self):
        self._fill(8)
        self.run_turn()
        content = self.first_user_message()
        for i in range(5):
            self.assertIn(f"Item {i} done.", content)
        for i in range(5, 8):
            self.assertNotIn(f"Item {i} done.", content)
        self.assertIn("+3 more update", content)
        # Only the injected five are marked delivered -- the other three
        # stay unviewed to be picked up (and re-counted) on a later turn.
        self.assertEqual(sorted(self.update_service.marked_viewed), list(range(5)))

    def test_summary_is_truncated_to_600_characters(self):
        self.update_service._unviewed[1] = notification(1, message="x" * 900)
        self.run_turn()
        content = self.first_user_message()
        # 600 chars of summary plus the single truncation marker character.
        self.assertIn("x" * 599 + "…", content)
        self.assertNotIn("x" * 601, content)


class NotificationCrossMediumTests(PendingNotificationsInjectionTests):
    """
    The voice (SPEECH_PROMPT) and glasses (GLASSES_PROMPT) paths run the
    exact same `_conversation_turn` as chat -- there is no separate
    injection path per medium -- so one test per medium here is enough to
    confirm that, not a full redundant suite.
    """

    def run_turn(self, prompt="when do I deploy", prompt_source=None):
        from prompting.prompt_source_prompt import PromptSourceEnum

        return list(
            self.agent_loop.conversation_loop_events(
                prompt,
                self.conversation_id,
                prompt_source=prompt_source or PromptSourceEnum.CHAT_PROMPT,
            )
        )

    def test_voice_path_also_gets_the_notification(self):
        from prompting.prompt_source_prompt import PromptSourceEnum

        self.update_service._unviewed[7] = notification(7, message="PR #42 merged.")
        self.run_turn(prompt_source=PromptSourceEnum.SPEECH_PROMPT)
        self.assertIn("PR #42 merged.", self.first_user_message())

    def test_glasses_path_also_gets_the_notification(self):
        from prompting.prompt_source_prompt import PromptSourceEnum

        self.update_service._unviewed[7] = notification(7, message="PR #42 merged.")
        self.run_turn(prompt_source=PromptSourceEnum.GLASSES_PROMPT)
        self.assertIn("PR #42 merged.", self.first_user_message())


if __name__ == "__main__":
    unittest.main()
