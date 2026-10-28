import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.dao.conversation_dao import ConversationDao
from src.model.conversation import Conversation

_IDLE_HOURS = 3
_SMS_IDLE_HOURS = 12


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


if __name__ == "__main__":
    unittest.main()
