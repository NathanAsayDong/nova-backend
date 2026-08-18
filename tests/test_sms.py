import os
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-key")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC-fake")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "fake-auth-token")
os.environ.setdefault("TWILIO_PHONE_NUMBER", "+13853601934")
os.environ.setdefault("TWILIO_TARGET_NUMBER", "+18016477824")
os.environ.setdefault("PUBLIC_BASE_URL", "https://abc123.ngrok-free.app")

from src.service.twilio_service import (  # noqa: E402
    SMS_MAX_BODY_CHARS,
    SMS_MAX_RECIPIENTS,
    SmsRecipientError,
    TwilioService,
    normalize_phone_number,
)


class FakeMessages:
    def __init__(self, fail_on=None, exception=None):
        self.sent = []
        self.fail_on = fail_on
        self.exception = exception

    def create(self, to, from_, body):
        if self.fail_on is not None and to == self.fail_on:
            raise self.exception or RuntimeError("carrier rejected")
        self.sent.append((to, body))
        return SimpleNamespace(sid=f"SM{len(self.sent):04d}")


def build_service(messages: FakeMessages) -> TwilioService:
    service = TwilioService()
    service._client = SimpleNamespace(messages=messages)
    return service


class NormalizationTests(unittest.TestCase):
    def test_accepts_the_ways_people_write_numbers(self):
        for raw in (
            "8016477824",
            "801-647-7824",
            "(801) 647-7824",
            "+1 801 647 7824",
            "18016477824",
            " +18016477824 ",
        ):
            with self.subTest(raw=raw):
                self.assertEqual(normalize_phone_number(raw), "+18016477824")

    def test_keeps_non_us_numbers_intact(self):
        self.assertEqual(normalize_phone_number("+447911123456"), "+447911123456")

    def test_rejects_rather_than_guesses(self):
        # Guessing at a malformed number means texting a stranger.
        for raw in ("", "   ", "abc", "12345", "+", "1" * 20):
            with self.subTest(raw=raw):
                with self.assertRaises(SmsRecipientError):
                    normalize_phone_number(raw)


class BodySplittingTests(unittest.TestCase):
    def test_short_body_is_one_unnumbered_message(self):
        parts = TwilioService.split_sms_body("All done.")
        self.assertEqual(parts, ["All done."])

    def test_long_body_is_split_and_numbered(self):
        parts = TwilioService.split_sms_body(" ".join(["word"] * 600))

        self.assertGreater(len(parts), 1)
        self.assertTrue(parts[0].startswith(f"(1/{len(parts)})"))
        for part in parts:
            self.assertLessEqual(len(part), SMS_MAX_BODY_CHARS)

    def test_split_preserves_all_words(self):
        original = " ".join(f"w{i}" for i in range(800))
        rejoined = " ".join(
            part.split(") ", 1)[1] for part in TwilioService.split_sms_body(original)
        )
        self.assertEqual(rejoined.split(), original.split())

    def test_one_enormous_token_is_hard_split_rather_than_hanging(self):
        parts = TwilioService.split_sms_body("x" * 5000)

        self.assertGreater(len(parts), 1)
        for part in parts:
            self.assertLessEqual(len(part), SMS_MAX_BODY_CHARS)

    def test_empty_body_rejected(self):
        with self.assertRaises(ValueError):
            TwilioService.split_sms_body("   ")


class SendSmsTests(unittest.TestCase):
    def test_sends_to_several_recipients(self):
        messages = FakeMessages()
        result = build_service(messages).send_sms(
            ["801-647-7824", "+13853601934"], "Deploy is green."
        )

        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["sent"], 2)
        self.assertEqual(
            [to for to, _ in messages.sent], ["+18016477824", "+13853601934"]
        )

    def test_accepts_a_bare_string_recipient(self):
        messages = FakeMessages()
        result = build_service(messages).send_sms("8016477824", "hi")

        self.assertEqual(result["sent"], 1)

    def test_one_bad_number_does_not_stop_the_others(self):
        messages = FakeMessages()
        result = build_service(messages).send_sms(
            ["not-a-number", "801-647-7824"], "hi"
        )

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["results"][0]["status"], "invalid")
        self.assertEqual(result["results"][1]["status"], "sent")

    def test_send_failure_is_reported_per_recipient(self):
        messages = FakeMessages(fail_on="+18016477824")
        result = build_service(messages).send_sms(
            ["801-647-7824", "+13853601934"], "hi"
        )

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["results"][0]["status"], "failed")
        self.assertIn("carrier rejected", result["results"][0]["error"])

    def test_refuses_a_bulk_send(self):
        numbers = [f"+1801647{n:04d}" for n in range(SMS_MAX_RECIPIENTS + 1)]
        with self.assertRaises(SmsRecipientError):
            build_service(FakeMessages()).send_sms(numbers, "hi")

    def test_requires_at_least_one_recipient(self):
        with self.assertRaises(SmsRecipientError):
            build_service(FakeMessages()).send_sms([], "hi")

    def test_long_body_sends_as_multiple_messages(self):
        messages = FakeMessages()
        result = build_service(messages).send_sms(
            "801-647-7824", " ".join(["word"] * 600)
        )

        self.assertGreater(result["parts_per_recipient"], 1)
        self.assertEqual(len(messages.sent), result["parts_per_recipient"])


class RecipientAllowlistTests(unittest.TestCase):
    @mock.patch.dict(
        "os.environ", {"NOVA_SMS_ALLOWED_RECIPIENTS": "801-647-7824"}, clear=False
    )
    def test_allowlist_blocks_other_numbers(self):
        messages = FakeMessages()
        result = build_service(messages).send_sms(
            ["+18016477824", "+15551234567"], "hi"
        )

        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["results"][1]["status"], "not_permitted")
        self.assertEqual([to for to, _ in messages.sent], ["+18016477824"])

    @mock.patch.dict(
        "os.environ", {"NOVA_SMS_ALLOWED_RECIPIENTS": "801-647-7824"}, clear=False
    )
    def test_internal_callers_may_bypass_the_allowlist(self):
        # The dispatcher texting the user's own number already knows the
        # destination; the allowlist exists to constrain model-chosen ones.
        messages = FakeMessages()
        result = build_service(messages).send_sms(
            "+15551234567", "hi", allow_unlisted=True
        )

        self.assertEqual(result["sent"], 1)

    @mock.patch.dict("os.environ", {"NOVA_SMS_ALLOWED_RECIPIENTS": ""}, clear=False)
    def test_unset_allowlist_permits_any_number(self):
        messages = FakeMessages()
        result = build_service(messages).send_sms("+15551234567", "hi")

        self.assertEqual(result["sent"], 1)


class SenderAllowlistTests(unittest.TestCase):
    @mock.patch.dict("os.environ", {"NOVA_SMS_ALLOWED_SENDERS": ""}, clear=False)
    def test_defaults_to_the_users_own_number(self):
        self.assertEqual(TwilioService.allowed_sms_senders(), {"+18016477824"})

    @mock.patch.dict(
        "os.environ",
        {"NOVA_SMS_ALLOWED_SENDERS": "801-647-7824, +13853601934"},
        clear=False,
    )
    def test_accepts_several_and_normalizes_them(self):
        self.assertEqual(
            TwilioService.allowed_sms_senders(), {"+18016477824", "+13853601934"}
        )

    @mock.patch.dict(
        "os.environ", {"NOVA_SMS_ALLOWED_SENDERS": "garbage, 801-647-7824"}, clear=False
    )
    def test_unparseable_entries_are_dropped_not_fatal(self):
        # A typo in the allowlist must not open it up or crash the webhook.
        self.assertEqual(TwilioService.allowed_sms_senders(), {"+18016477824"})


if __name__ == "__main__":
    unittest.main()
