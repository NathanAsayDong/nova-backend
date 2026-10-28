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


if __name__ == "__main__":
    unittest.main()
