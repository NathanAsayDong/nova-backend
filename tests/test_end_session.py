import os
import unittest
from uuid import uuid4

os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-key")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC-fake")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "fake-auth-token")
os.environ.setdefault("TWILIO_PHONE_NUMBER", "+15550000000")
os.environ.setdefault("TWILIO_TARGET_NUMBER", "+15551111111")
os.environ.setdefault("PUBLIC_BASE_URL", "https://abc123.ngrok-free.app")

from src.controller import call_controller  # noqa: E402
from src.service.conversation_service import ConversationService  # noqa: E402


def build_service() -> ConversationService:
    return ConversationService.__new__(ConversationService)


class EndSessionTests(unittest.TestCase):
    def setUp(self):
        ConversationService._stop_requests.clear()
        self.addCleanup(ConversationService._stop_requests.clear)

    def test_records_a_stop_request_for_the_conversation(self):
        service = build_service()
        uuid = uuid4()

        result = service.end_session(str(uuid), reason="user said 'that's all'")

        self.assertEqual(result["status"], "ending")
        self.assertEqual(service.pop_stop_request(uuid), "user said 'that's all'")

    def test_pop_is_one_shot(self):
        service = build_service()
        uuid = uuid4()
        service.end_session(str(uuid))

        self.assertIsNotNone(service.pop_stop_request(uuid))
        # A second turn must not inherit the previous turn's stop.
        self.assertIsNone(service.pop_stop_request(uuid))

    def test_defaults_a_reason_when_none_given(self):
        service = build_service()
        uuid = uuid4()
        service.end_session(str(uuid))

        self.assertTrue(service.pop_stop_request(uuid))

    def test_blank_reason_is_replaced_not_stored(self):
        service = build_service()
        uuid = uuid4()
        service.end_session(str(uuid), reason="   ")

        # A falsy reason would read as "no stop requested" at the call site.
        self.assertTrue(service.pop_stop_request(uuid))

    def test_is_scoped_to_one_conversation(self):
        service = build_service()
        ending, untouched = uuid4(), uuid4()
        service.end_session(str(ending))

        self.assertIsNone(service.pop_stop_request(untouched))
        self.assertIsNotNone(service.pop_stop_request(ending))

    def test_visible_across_service_instances(self):
        # The tool layer builds its own ConversationService per call, while the
        # controller holds a different one — the flag has to cross that gap.
        uuid = uuid4()
        build_service().end_session(str(uuid))

        self.assertIsNotNone(build_service().pop_stop_request(uuid))

    def test_does_not_close_the_conversation(self):
        # end_session ends the session, not the conversation; closing would be
        # terminal and the user could never continue it.
        service = build_service()
        uuid = uuid4()
        result = service.end_session(str(uuid))

        self.assertNotIn("closed", str(result.get("status", "")).lower())
        self.assertIn("stays open", result["note"])


class GoodbyeTimingTests(unittest.TestCase):
    """
    Twilio does not document whether {"type":"end"} flushes pending speech, so
    the hangup waits roughly as long as the goodbye takes to say — but always
    within bounds, so a bad estimate can neither clip the goodbye to nothing
    nor leave the caller on a dead line.
    """

    def test_short_goodbye_gets_a_floor(self):
        self.assertGreaterEqual(call_controller._speech_seconds("Bye."), 1.5)

    def test_longer_goodbye_waits_longer(self):
        short = call_controller._speech_seconds("Bye.")
        longer = call_controller._speech_seconds(
            "Alright, I'll let you get back to it. Talk to you later, sir."
        )
        self.assertGreater(longer, short)

    def test_runaway_text_is_capped(self):
        self.assertLessEqual(call_controller._speech_seconds("x" * 100_000), 12.0)

    def test_empty_text_still_returns_the_floor(self):
        self.assertGreaterEqual(call_controller._speech_seconds(""), 1.5)


if __name__ == "__main__":
    unittest.main()
