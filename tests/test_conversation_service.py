import os
import unittest
from dataclasses import dataclass, field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# test_sms_threshold_is_12_hours_matching_sms_controller imports
# sms_controller, which builds a real ConversationService() (and thus a real
# ConversationDao -> BaseDao) at module scope; BaseDao requires these to be
# set even though nothing here talks to Supabase. Same pattern as
# test_sms_controller.py / test_sms.py / test_call_controller.py.
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-key")

from src.service.conversation_service import (
    SMS_THREAD_IDLE_HOURS,
    ConversationService,
    _most_recent_local_midnight_utc,
)


@dataclass
class FakeConversationDao:
    calls: list = field(default_factory=list)

    def check_for_stale_conversations(self, idle_hours, sms_idle_hours, rollover_cutoff_utc):
        self.calls.append((idle_hours, sms_idle_hours, rollover_cutoff_utc))


def build_service() -> ConversationService:
    service = ConversationService.__new__(ConversationService)
    service.conversation_dao = FakeConversationDao()
    return service


class CheckForStaleConversationsTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("NOVA_CONVERSATION_IDLE_HOURS", None)
        os.environ.pop("NOVA_CONVERSATION_ROLLOVER_TZ", None)

    def tearDown(self):
        os.environ.pop("NOVA_CONVERSATION_IDLE_HOURS", None)
        os.environ.pop("NOVA_CONVERSATION_ROLLOVER_TZ", None)

    def test_uses_default_idle_hours_and_sms_threshold(self):
        service = build_service()

        service.check_for_stale_conversations()

        self.assertEqual(len(service.conversation_dao.calls), 1)
        idle_hours, sms_idle_hours, rollover_cutoff_utc = service.conversation_dao.calls[0]
        self.assertEqual(idle_hours, 3.0)
        self.assertEqual(sms_idle_hours, SMS_THREAD_IDLE_HOURS)
        self.assertIsNotNone(rollover_cutoff_utc.tzinfo)

    def test_honors_idle_hours_env_override(self):
        os.environ["NOVA_CONVERSATION_IDLE_HOURS"] = "6"
        service = build_service()

        service.check_for_stale_conversations()

        idle_hours, sms_idle_hours, _ = service.conversation_dao.calls[0]
        self.assertEqual(idle_hours, 6.0)
        self.assertEqual(sms_idle_hours, SMS_THREAD_IDLE_HOURS)

    def test_sms_threshold_is_12_hours_matching_sms_controller(self):
        from src.controller.sms_controller import SMS_THREAD_IDLE_HOURS as controller_value

        self.assertEqual(SMS_THREAD_IDLE_HOURS, controller_value)

    def test_default_rollover_tz_is_america_denver(self):
        service = build_service()
        service.check_for_stale_conversations()

        _, _, rollover_cutoff_utc = service.conversation_dao.calls[0]
        expected = _most_recent_local_midnight_utc(
            "America/Denver", datetime.now(timezone.utc)
        )
        # Both computed within the same test run, so they should land on the
        # same instant unless the test happens to straddle midnight itself.
        self.assertEqual(rollover_cutoff_utc, expected)

    def test_honors_rollover_tz_env_override(self):
        os.environ["NOVA_CONVERSATION_ROLLOVER_TZ"] = "America/New_York"
        service = build_service()

        service.check_for_stale_conversations()

        _, _, rollover_cutoff_utc = service.conversation_dao.calls[0]
        expected = _most_recent_local_midnight_utc(
            "America/New_York", datetime.now(timezone.utc)
        )
        self.assertEqual(rollover_cutoff_utc, expected)


class MostRecentLocalMidnightUtcTests(unittest.TestCase):
    """
    Exercises the zoneinfo-based rollover math directly, including the
    America/Denver DST transitions, so this can never silently regress to a
    fixed UTC-7 offset.
    """

    def test_before_local_midnight_still_counts_the_prior_day(self):
        # 11:30pm Denver time on Jan 14 is still before the Jan 15 midnight
        # rollover — the cutoff must be the midnight that *just passed*
        # locally, i.e. the start of Jan 14, not Jan 15.
        now_utc = datetime(2026, 1, 15, 6, 30, tzinfo=timezone.utc)  # 11:30pm MST Jan 14
        result = _most_recent_local_midnight_utc("America/Denver", now_utc)
        expected = datetime(2026, 1, 14, tzinfo=ZoneInfo("America/Denver")).astimezone(
            timezone.utc
        )
        self.assertEqual(result, expected)

    def test_after_local_midnight_rolls_to_the_new_day(self):
        # 12:05am Denver time on Jan 15 — the rollover should now be today's
        # midnight (Jan 15), not yesterday's.
        now_utc = datetime(2026, 1, 15, 7, 5, tzinfo=timezone.utc)  # 12:05am MST Jan 15
        result = _most_recent_local_midnight_utc("America/Denver", now_utc)
        expected = datetime(2026, 1, 15, tzinfo=ZoneInfo("America/Denver")).astimezone(
            timezone.utc
        )
        self.assertEqual(result, expected)

    def test_mst_offset_before_spring_forward(self):
        # 2026-03-01 is before the second-Sunday-in-March DST switch, so
        # Denver is on MST (UTC-7): local midnight is 07:00 UTC.
        now_utc = datetime(2026, 3, 1, 15, 0, tzinfo=timezone.utc)
        result = _most_recent_local_midnight_utc("America/Denver", now_utc)
        self.assertEqual(result, datetime(2026, 3, 1, 7, 0, tzinfo=timezone.utc))

    def test_mdt_offset_after_spring_forward(self):
        # 2026-03-15 is after the spring-forward transition (2026-03-08), so
        # Denver is on MDT (UTC-6): local midnight is 06:00 UTC — a fixed
        # UTC-7 offset would get this wrong by an hour.
        now_utc = datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc)
        result = _most_recent_local_midnight_utc("America/Denver", now_utc)
        self.assertEqual(result, datetime(2026, 3, 15, 6, 0, tzinfo=timezone.utc))

    def test_mdt_offset_before_fall_back(self):
        # 2026-11-01 is before the first-Sunday-in-November fall-back
        # transition (2026-11-01 itself, 2am local), so the midnight at the
        # very start of that day is still MDT (UTC-6).
        now_utc = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
        result = _most_recent_local_midnight_utc("America/Denver", now_utc)
        self.assertEqual(result, datetime(2026, 11, 1, 6, 0, tzinfo=timezone.utc))

    def test_mst_offset_after_fall_back(self):
        # 2026-11-08 is a full week after the fall-back transition, so Denver
        # is back on MST (UTC-7) — a fixed UTC-6 offset would get this wrong.
        now_utc = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)
        result = _most_recent_local_midnight_utc("America/Denver", now_utc)
        self.assertEqual(result, datetime(2026, 11, 8, 7, 0, tzinfo=timezone.utc))

    def test_different_timezone_is_respected(self):
        now_utc = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
        result = _most_recent_local_midnight_utc("America/New_York", now_utc)
        # Mid-June, New York is on EDT (UTC-4).
        self.assertEqual(result, datetime(2026, 6, 15, 4, 0, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
