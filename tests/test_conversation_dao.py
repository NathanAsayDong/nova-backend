import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from src.dao.conversation_dao import ConversationDao
from src.model.conversation import Conversation
from src.service.conversation_service import _most_recent_local_midnight_utc

_IDLE_HOURS = 3
_SMS_IDLE_HOURS = 12
_DENVER = ZoneInfo("America/Denver")


class IsIdleTests(unittest.TestCase):
    """
    Exercises ConversationDao._is_idle directly. It is a pure function of
    (conversation, now, idle_hours, sms_idle_hours), so no Supabase client is
    needed to cover the threshold logic that check_for_stale_conversations
    relies on.
    """

    def setUp(self):
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def _conversation(self, **kwargs):
        defaults = dict(uuid=uuid4(), is_closed=False)
        defaults.update(kwargs)
        return Conversation(**defaults)

    def test_non_sms_conversation_closes_past_idle_hours(self):
        conversation = self._conversation(
            last_message_timestamp_utc=self.now - timedelta(hours=_IDLE_HOURS, minutes=1)
        )
        self.assertTrue(
            ConversationDao._is_idle(conversation, self.now, _IDLE_HOURS, _SMS_IDLE_HOURS)
        )

    def test_non_sms_conversation_stays_open_within_idle_hours(self):
        conversation = self._conversation(
            last_message_timestamp_utc=self.now - timedelta(hours=_IDLE_HOURS, minutes=-1)
        )
        self.assertFalse(
            ConversationDao._is_idle(conversation, self.now, _IDLE_HOURS, _SMS_IDLE_HOURS)
        )

    def test_sms_conversation_uses_sms_threshold_not_default(self):
        # Past the non-SMS threshold but well inside the SMS threshold.
        conversation = self._conversation(
            sms_phone_number="+15555550100",
            last_message_timestamp_utc=self.now - timedelta(hours=_IDLE_HOURS + 1),
        )
        self.assertFalse(
            ConversationDao._is_idle(conversation, self.now, _IDLE_HOURS, _SMS_IDLE_HOURS)
        )

    def test_sms_conversation_closes_past_sms_threshold(self):
        conversation = self._conversation(
            sms_phone_number="+15555550100",
            last_message_timestamp_utc=self.now - timedelta(hours=_SMS_IDLE_HOURS, minutes=1),
        )
        self.assertTrue(
            ConversationDao._is_idle(conversation, self.now, _IDLE_HOURS, _SMS_IDLE_HOURS)
        )

    def test_null_timestamp_is_skipped(self):
        conversation = self._conversation(last_message_timestamp_utc=None)
        self.assertFalse(
            ConversationDao._is_idle(conversation, self.now, _IDLE_HOURS, _SMS_IDLE_HOURS)
        )

    def test_already_closed_conversation_is_left_untouched(self):
        conversation = self._conversation(
            is_closed=True,
            last_message_timestamp_utc=self.now - timedelta(days=365),
        )
        self.assertFalse(
            ConversationDao._is_idle(conversation, self.now, _IDLE_HOURS, _SMS_IDLE_HOURS)
        )

    def test_naive_timestamp_is_treated_as_utc(self):
        naive_last = (self.now - timedelta(hours=_IDLE_HOURS, minutes=1)).replace(tzinfo=None)
        conversation = self._conversation(last_message_timestamp_utc=naive_last)
        self.assertTrue(
            ConversationDao._is_idle(conversation, self.now, _IDLE_HOURS, _SMS_IDLE_HOURS)
        )

    def test_z_suffixed_string_timestamp_is_coerced(self):
        # Supabase/SQLModel hand last_message_timestamp_utc back as a raw str
        # when the dao builds Conversation(**row) (table models skip Pydantic
        # validation on init), so this is the realistic shape of the bug.
        last_str = (self.now - timedelta(hours=_IDLE_HOURS, minutes=1)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        ) + "Z"
        conversation = self._conversation(last_message_timestamp_utc=last_str)
        self.assertTrue(
            ConversationDao._is_idle(conversation, self.now, _IDLE_HOURS, _SMS_IDLE_HOURS)
        )

    def test_plus_offset_string_timestamp_is_coerced(self):
        last_str = (self.now - timedelta(hours=_IDLE_HOURS, minutes=1)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        ) + "+00:00"
        conversation = self._conversation(last_message_timestamp_utc=last_str)
        self.assertTrue(
            ConversationDao._is_idle(conversation, self.now, _IDLE_HOURS, _SMS_IDLE_HOURS)
        )

    def test_naive_string_timestamp_is_treated_as_utc(self):
        last_str = (self.now - timedelta(hours=_IDLE_HOURS, minutes=1)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        conversation = self._conversation(last_message_timestamp_utc=last_str)
        self.assertTrue(
            ConversationDao._is_idle(conversation, self.now, _IDLE_HOURS, _SMS_IDLE_HOURS)
        )

    def test_unparseable_string_timestamp_is_skipped_like_null(self):
        conversation = self._conversation(last_message_timestamp_utc="not-a-timestamp")
        self.assertFalse(
            ConversationDao._is_idle(conversation, self.now, _IDLE_HOURS, _SMS_IDLE_HOURS)
        )


class IsPastRolloverTests(unittest.TestCase):
    """
    Exercises ConversationDao._is_past_rollover directly, using
    _most_recent_local_midnight_utc (the real helper the service computes
    with) for the cutoff in each case so these tests stay honest about the
    actual DST math rather than hand-waving the cutoff.
    """

    def _conversation(self, **kwargs):
        defaults = dict(uuid=uuid4(), is_closed=False)
        defaults.update(kwargs)
        return Conversation(**defaults)

    def test_activity_before_local_midnight_closes(self):
        # 11pm Denver time on Jan 14, "now" is 1am Denver time Jan 15 — last
        # activity is before the midnight that just passed.
        now_utc = datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc)  # 1am MST Jan 15
        cutoff = _most_recent_local_midnight_utc("America/Denver", now_utc)
        last_activity = datetime(2026, 1, 14, 23, 0, tzinfo=_DENVER).astimezone(timezone.utc)

        conversation = self._conversation(last_message_timestamp_utc=last_activity)
        self.assertTrue(ConversationDao._is_past_rollover(conversation, cutoff))

    def test_activity_after_local_midnight_stays_open(self):
        # Same "now" as above, but last activity is 12:30am Denver time —
        # after the midnight that just passed, so it should not roll over.
        now_utc = datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc)  # 1am MST Jan 15
        cutoff = _most_recent_local_midnight_utc("America/Denver", now_utc)
        last_activity = datetime(2026, 1, 15, 0, 30, tzinfo=_DENVER).astimezone(timezone.utc)

        conversation = self._conversation(last_message_timestamp_utc=last_activity)
        self.assertFalse(ConversationDao._is_past_rollover(conversation, cutoff))

    def test_still_within_idle_window_but_past_rollover_still_closes(self):
        # A conversation active 5 minutes before midnight is nowhere near the
        # 3-hour idle threshold, but the rollover rule closes it anyway.
        now_utc = datetime(2026, 1, 15, 7, 30, tzinfo=timezone.utc)  # 12:30am MST Jan 15
        cutoff = _most_recent_local_midnight_utc("America/Denver", now_utc)
        last_activity = datetime(2026, 1, 14, 23, 55, tzinfo=_DENVER).astimezone(timezone.utc)

        conversation = self._conversation(last_message_timestamp_utc=last_activity)
        self.assertTrue(ConversationDao._is_past_rollover(conversation, cutoff))

    def test_dst_spring_forward_edge(self):
        # Conversation last active at 11pm MST on 2026-03-07 (the night
        # before the spring-forward transition). "Now" is the next morning,
        # already on MDT. A fixed-offset implementation would get this cutoff
        # wrong by an hour; zoneinfo gets it right.
        now_utc = datetime(2026, 3, 8, 16, 0, tzinfo=timezone.utc)  # 10am MDT Mar 8
        cutoff = _most_recent_local_midnight_utc("America/Denver", now_utc)
        last_activity = datetime(2026, 3, 7, 23, 0, tzinfo=_DENVER).astimezone(timezone.utc)

        conversation = self._conversation(last_message_timestamp_utc=last_activity)
        self.assertTrue(ConversationDao._is_past_rollover(conversation, cutoff))

    def test_dst_fall_back_edge(self):
        # Conversation last active at 11pm MDT on 2025-11-07 (the night
        # before the fall-back transition). "Now" is the next morning,
        # already on MST.
        now_utc = datetime(2025, 11, 8, 16, 0, tzinfo=timezone.utc)  # 9am MST Nov 8
        cutoff = _most_recent_local_midnight_utc("America/Denver", now_utc)
        last_activity = datetime(2025, 11, 7, 23, 0, tzinfo=_DENVER).astimezone(timezone.utc)

        conversation = self._conversation(last_message_timestamp_utc=last_activity)
        self.assertTrue(ConversationDao._is_past_rollover(conversation, cutoff))

    def test_already_closed_conversation_is_left_untouched(self):
        now_utc = datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc)
        cutoff = _most_recent_local_midnight_utc("America/Denver", now_utc)
        conversation = self._conversation(
            is_closed=True,
            last_message_timestamp_utc=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        self.assertFalse(ConversationDao._is_past_rollover(conversation, cutoff))

    def test_null_timestamp_is_skipped(self):
        now_utc = datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc)
        cutoff = _most_recent_local_midnight_utc("America/Denver", now_utc)
        conversation = self._conversation(last_message_timestamp_utc=None)
        self.assertFalse(ConversationDao._is_past_rollover(conversation, cutoff))

    def test_string_timestamp_before_local_midnight_closes(self):
        # Same scenario as test_activity_before_local_midnight_closes, but
        # last_message_timestamp_utc arrives as the raw Z-suffixed string the
        # dao actually sees, to prove rollover closing survives the str bug
        # too, not just _is_idle.
        now_utc = datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc)  # 1am MST Jan 15
        cutoff = _most_recent_local_midnight_utc("America/Denver", now_utc)
        last_activity = datetime(2026, 1, 14, 23, 0, tzinfo=_DENVER).astimezone(timezone.utc)
        last_str = last_activity.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

        conversation = self._conversation(last_message_timestamp_utc=last_str)
        self.assertTrue(ConversationDao._is_past_rollover(conversation, cutoff))

    def test_worker_restart_after_missing_a_midnight_still_closes(self):
        """
        The rollover is computed fresh from "now" on every run rather than
        scheduled for an exact clock time, so a worker that was down for a
        day and a half (missing a midnight entirely) still closes a
        conversation from two days ago the moment it comes back up — there is
        no "I missed my window" state to get stuck in.
        """
        # Conversation last touched Jan 13, 10am Denver time.
        last_activity = datetime(2026, 1, 13, 10, 0, tzinfo=_DENVER).astimezone(timezone.utc)
        conversation = self._conversation(last_message_timestamp_utc=last_activity)

        # Worker comes back up on Jan 15 at 9am Denver time — it missed the
        # Jan 14 AND Jan 15 midnights entirely.
        now_utc = datetime(2026, 1, 15, 16, 0, tzinfo=timezone.utc)  # 9am MST Jan 15
        cutoff = _most_recent_local_midnight_utc("America/Denver", now_utc)

        self.assertTrue(ConversationDao._is_past_rollover(conversation, cutoff))


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    """
    Minimal stand-in for the supabase-py table query builder, just enough to
    serve check_for_stale_conversations' select-then-per-row-update pattern
    without a live Supabase connection.
    """

    def __init__(self, client):
        self._client = client
        self._pending_update = None
        self._eq_uuid = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column, value):
        if column == "uuid":
            self._eq_uuid = value
        return self

    def update(self, payload):
        self._pending_update = payload
        return self

    def execute(self):
        if self._pending_update is not None:
            self._client.update_calls.append((self._eq_uuid, self._pending_update))
            return _FakeResponse([{"uuid": self._eq_uuid, **self._pending_update}])
        return _FakeResponse(self._client.rows)


class _FakeSupabaseClient:
    def __init__(self, rows):
        self.rows = rows
        self.update_calls = []

    def table(self, _name):
        return _FakeTable(self)


class CheckForStaleConversationsLoopTests(unittest.TestCase):
    """
    Exercises the actual loop in check_for_stale_conversations (not just the
    pure _is_idle/_is_past_rollover helpers) against a fake Supabase client,
    to prove a single bad row no longer aborts the whole batch the way the
    original str/.tzinfo AttributeError did.
    """

    def _dao(self, rows):
        dao = ConversationDao.__new__(ConversationDao)
        dao.supabase = _FakeSupabaseClient(rows)
        return dao

    def test_bad_row_is_logged_and_does_not_block_remaining_rows(self):
        now = datetime.now(timezone.utc)
        bad_uuid = uuid4()
        idle_uuid = uuid4()
        open_uuid = uuid4()
        rows = [
            {
                "uuid": str(bad_uuid),
                "is_closed": False,
                # Not a str, not a datetime, not None — _is_idle's isinstance
                # check won't catch it and `.tzinfo` raises AttributeError,
                # simulating any unexpected bad value in this column.
                "last_message_timestamp_utc": 12345,
            },
            {
                "uuid": str(idle_uuid),
                "is_closed": False,
                "last_message_timestamp_utc": (now - timedelta(hours=2)).isoformat(),
            },
            {
                "uuid": str(open_uuid),
                "is_closed": False,
                "last_message_timestamp_utc": (now - timedelta(minutes=5)).isoformat(),
            },
        ]
        dao = self._dao(rows)
        # Rollover cutoff far in the past so only the idle threshold decides.
        rollover_cutoff_utc = datetime(1970, 1, 1, tzinfo=timezone.utc)

        # Must not raise despite the bad row.
        dao.check_for_stale_conversations(
            idle_hours=1, sms_idle_hours=12, rollover_cutoff_utc=rollover_cutoff_utc
        )

        updated_uuids = [str(uuid) for uuid, _ in dao.supabase.update_calls]
        self.assertIn(str(idle_uuid), updated_uuids)
        self.assertNotIn(str(open_uuid), updated_uuids)
        self.assertNotIn(str(bad_uuid), updated_uuids)


if __name__ == "__main__":
    unittest.main()
