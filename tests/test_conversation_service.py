import os
import unittest
from dataclasses import dataclass, field

from src.service.conversation_service import (
    SMS_THREAD_IDLE_HOURS,
    ConversationService,
)


@dataclass
class FakeConversationDao:
    calls: list = field(default_factory=list)

    def check_for_stale_conversations(self, idle_hours, sms_idle_hours):
        self.calls.append((idle_hours, sms_idle_hours))


def build_service() -> ConversationService:
    service = ConversationService.__new__(ConversationService)
    service.conversation_dao = FakeConversationDao()
    return service


class CheckForStaleConversationsTests(unittest.TestCase):
    def test_uses_default_idle_hours_and_sms_threshold(self):
        os.environ.pop("NOVA_CONVERSATION_IDLE_HOURS", None)
        service = build_service()

        service.check_for_stale_conversations()

        self.assertEqual(service.conversation_dao.calls, [(3.0, SMS_THREAD_IDLE_HOURS)])

    def test_honors_env_override(self):
        os.environ["NOVA_CONVERSATION_IDLE_HOURS"] = "6"
        try:
            service = build_service()
            service.check_for_stale_conversations()
            self.assertEqual(
                service.conversation_dao.calls, [(6.0, SMS_THREAD_IDLE_HOURS)]
            )
        finally:
            os.environ.pop("NOVA_CONVERSATION_IDLE_HOURS", None)

    def test_sms_threshold_is_12_hours_matching_sms_controller(self):
        from src.controller.sms_controller import SMS_THREAD_IDLE_HOURS as controller_value

        self.assertEqual(SMS_THREAD_IDLE_HOURS, controller_value)


if __name__ == "__main__":
    unittest.main()
