import os
import unittest
from types import SimpleNamespace
from unittest import mock
from uuid import UUID, uuid4

# call_controller builds its services at import time, the same way the other
# controllers do. These are connection settings only — the Supabase client is
# lazy and nothing here reaches the network.
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-key")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC-fake")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "fake-auth-token")
os.environ.setdefault("TWILIO_PHONE_NUMBER", "+15550000000")
os.environ.setdefault("TWILIO_TARGET_NUMBER", "+15551111111")
os.environ.setdefault("PUBLIC_BASE_URL", "https://nova.ngrok.io")

from src.controller import call_controller  # noqa: E402
from src.model.report_type import DeliveryStatus, ReportType  # noqa: E402
from src.model.update import Update  # noqa: E402
from src.service.twilio_service import DEFAULT_CALL_VOICE_ID  # noqa: E402


def make_update(id=42, message="The deploy finished.", conversation_uuid=None) -> Update:
    return Update(
        id=id,
        update_message=message,
        conversation_uuid=conversation_uuid,
        report_type=ReportType.CALL,
        delivery_status=DeliveryStatus.IN_PROGRESS,
    )


class RelayTokenTests(unittest.TestCase):
    def test_round_trips(self):
        token = call_controller.mint_relay_token(42)
        self.assertTrue(call_controller.verify_relay_token(token, 42))

    def test_rejects_a_different_update(self):
        token = call_controller.mint_relay_token(42)
        self.assertFalse(call_controller.verify_relay_token(token, 43))

    def test_rejects_a_tampered_signature(self):
        token = call_controller.mint_relay_token(42)
        payload, _, _ = token.rpartition(":")
        self.assertFalse(
            call_controller.verify_relay_token(f"{payload}:{'0' * 64}", 42)
        )

    def test_rejects_a_forged_id_under_a_valid_signature(self):
        # Swapping the id in the payload invalidates the HMAC over it.
        token = call_controller.mint_relay_token(42)
        _, _, digest = token.rpartition(":")
        self.assertFalse(call_controller.verify_relay_token(f"99:0:{digest}", 99))

    def test_rejects_an_expired_token(self):
        token = call_controller.mint_relay_token(42, issued_at=1000)
        self.assertFalse(call_controller.verify_relay_token(token, 42, now=1000 + 301))
        self.assertTrue(call_controller.verify_relay_token(token, 42, now=1000 + 299))

    def test_rejects_malformed_input(self):
        for bad in ("", "not-a-token", "1:2", "a:b:c"):
            with self.subTest(token=bad):
                self.assertFalse(call_controller.verify_relay_token(bad, 42))


class ConversationResolutionTests(unittest.TestCase):
    def test_continues_the_originating_conversation(self):
        conversation_uuid = uuid4()
        update = make_update(conversation_uuid=str(conversation_uuid))

        with mock.patch.object(
            call_controller.conversation_service,
            "get_conversation",
            return_value=SimpleNamespace(uuid=conversation_uuid, is_closed=False),
        ):
            resolved = call_controller._resolve_conversation_id(update)

        self.assertEqual(resolved, conversation_uuid)

    def test_starts_fresh_when_the_conversation_is_closed(self):
        conversation_uuid = uuid4()
        update = make_update(conversation_uuid=str(conversation_uuid))

        with mock.patch.object(
            call_controller.conversation_service,
            "get_conversation",
            return_value=SimpleNamespace(uuid=conversation_uuid, is_closed=True),
        ):
            resolved = call_controller._resolve_conversation_id(update)

        self.assertIsInstance(resolved, UUID)
        self.assertNotEqual(resolved, conversation_uuid)

    def test_starts_fresh_when_the_conversation_is_gone(self):
        update = make_update(conversation_uuid=str(uuid4()))

        with mock.patch.object(
            call_controller.conversation_service, "get_conversation", return_value=None
        ):
            self.assertIsInstance(
                call_controller._resolve_conversation_id(update), UUID
            )

    def test_starts_fresh_with_no_linked_conversation(self):
        self.assertIsInstance(
            call_controller._resolve_conversation_id(make_update()), UUID
        )

    def test_starts_fresh_on_an_unparseable_uuid(self):
        update = make_update(conversation_uuid="not-a-uuid")
        self.assertIsInstance(
            call_controller._resolve_conversation_id(update), UUID
        )


class OpeningPromptTests(unittest.TestCase):
    def test_carries_the_update_and_marks_itself_as_an_instruction(self):
        prompt = call_controller._opening_prompt(make_update(message="Build is green."))
        self.assertIn("Build is green.", prompt)
        self.assertIn("Do not read this instruction aloud", prompt)


class TwiMLTests(unittest.TestCase):
    """
    The answer webhook's TwiML is what configures the whole call, so its
    attributes are asserted rather than eyeballed.
    """

    def _answer_twiml(self, update, params=None):
        request = SimpleNamespace(
            query_params={"update_id": str(update.id)},
            url=SimpleNamespace(path="/calls/answer", query=f"update_id={update.id}"),
            headers={"X-Twilio-Signature": "sig"},
        )

        async def form():
            return params or {}

        request.form = form

        with mock.patch.object(
            call_controller.twilio_service, "verify_signature", return_value=True
        ), mock.patch.object(
            call_controller.update_service, "get_update", return_value=update
        ):
            import asyncio

            return asyncio.run(call_controller.answer_call(request))

    def test_opens_a_conversation_relay_to_the_public_websocket(self):
        body = self._answer_twiml(make_update()).body.decode()

        self.assertIn("<Connect>", body)
        self.assertIn('url="wss://nova.ngrok.io/calls/relay"', body)
        self.assertIn('<Parameter name="update_id" value="42"/>', body)
        self.assertIn('name="token"', body)

    def test_uses_a_conversationrelay_voice_not_the_personal_elevenlabs_one(self):
        """
        Twilio's ElevenLabs integration has its own voice-id namespace. Passing
        an id from the user's own ElevenLabs account gets rejected with error
        64112 and the caller hears "an application error has occurred".
        """
        with mock.patch.dict(
            os.environ, {"ELEVEN_LABS_VOICE_ID": "personal-voice-id"}, clear=False
        ):
            body = self._answer_twiml(make_update()).body.decode()

        self.assertIn('ttsProvider="ElevenLabs"', body)
        self.assertNotIn("personal-voice-id", body)
        self.assertIn(f'voice="{DEFAULT_CALL_VOICE_ID}"', body)

    def test_honours_an_explicit_call_voice(self):
        with mock.patch.dict(os.environ, {"NOVA_CALL_VOICE_ID": "NYC9WEgkq1u4jiqBseQ9"}):
            body = self._answer_twiml(make_update()).body.decode()

        self.assertIn('voice="NYC9WEgkq1u4jiqBseQ9"', body)

    def test_rejects_a_call_voice_copied_from_the_personal_account(self):
        with mock.patch.dict(
            os.environ,
            {
                "ELEVEN_LABS_VOICE_ID": "38ENUvwTBR448ATwyfF5",
                "NOVA_CALL_VOICE_ID": "38ENUvwTBR448ATwyfF5",
            },
        ):
            body = self._answer_twiml(make_update()).body.decode()

        self.assertNotIn("38ENUvwTBR448ATwyfF5", body)
        self.assertIn(f'voice="{DEFAULT_CALL_VOICE_ID}"', body)

    def test_allows_the_caller_to_interrupt(self):
        body = self._answer_twiml(make_update()).body.decode()

        self.assertIn('interruptible="any"', body)
        self.assertIn('reportInputDuringAgentSpeech="speech"', body)

    def test_hangs_up_on_an_answering_machine(self):
        body = self._answer_twiml(
            make_update(), params={"AnsweredBy": "machine_start"}
        ).body.decode()

        self.assertIn("<Hangup/>", body)
        self.assertNotIn("ConversationRelay", body)

    def test_proceeds_when_a_human_answers(self):
        body = self._answer_twiml(
            make_update(), params={"AnsweredBy": "human"}
        ).body.decode()

        self.assertIn("ConversationRelay", body)

    def test_rejects_an_unsigned_request(self):
        from fastapi import HTTPException

        request = SimpleNamespace(
            query_params={"update_id": "42"},
            url=SimpleNamespace(path="/calls/answer", query="update_id=42"),
            headers={},
        )

        async def form():
            return {}

        request.form = form

        with mock.patch.object(
            call_controller.twilio_service, "verify_signature", return_value=False
        ):
            import asyncio

            with self.assertRaises(HTTPException) as caught:
                asyncio.run(call_controller.answer_call(request))

        self.assertEqual(caught.exception.status_code, 403)


class ConfigurationGuardTests(unittest.TestCase):
    def test_placeholder_base_url_is_rejected(self):
        from src.service.twilio_service import TwilioService

        for placeholder in (
            "https://your-id.ngrok-free.app",
            "https://example.com",
            "https://<your-host>",
        ):
            with self.subTest(url=placeholder), mock.patch.dict(
                os.environ, {"PUBLIC_BASE_URL": placeholder}
            ):
                ok, problem = TwilioService().is_configured()
                self.assertFalse(ok)
                self.assertIn("placeholder", problem)

    def test_real_base_url_passes(self):
        from src.service.twilio_service import TwilioService

        with mock.patch.dict(
            os.environ, {"PUBLIC_BASE_URL": "https://abc123.ngrok-free.app"}
        ):
            ok, problem = TwilioService().is_configured()

        self.assertTrue(ok)
        self.assertIsNone(problem)


class EscapingTests(unittest.TestCase):
    def test_greeting_and_urls_are_xml_escaped(self):
        self.assertEqual(
            call_controller._escape('a & b < c > d "e"'),
            "a &amp; b &lt; c &gt; d &quot;e&quot;",
        )


if __name__ == "__main__":
    unittest.main()
