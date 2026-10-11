import os
import unittest
from base64 import b64encode
from unittest import mock

import requests

os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-key")
os.environ.setdefault("TWILIO_TARGET_NUMBER", "+18016477824")
os.environ.setdefault("BIP_BASE_URL", "abc123.api.infobip.com")
os.environ.setdefault("BIP_API_KEY", "fake-bip-key")
os.environ.setdefault("BIP_SENDER", "14355723870")

from src.service.bip_service import (  # noqa: E402
    SMS_MAX_BODY_CHARS,
    SMS_MAX_RECIPIENTS,
    BipConfigurationError,
    BipRequestError,
    BipService,
    SmsRecipientError,
    is_permanent_bip_error,
    normalize_phone_number,
)


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("no body")
        return self._body


class FakeHttp:
    """
    Stands in for requests: records each send and answers the way Infobip's
    /sms/3/messages does — PENDING for an accepted message, a requestError
    body for a refused request.
    """

    def __init__(self, fail_on=None, response=None, raises=None):
        self.sent = []
        self.requests = []
        self.fail_on = fail_on
        self.response = response
        self.raises = raises

    def post(self, url, json, headers, timeout):
        self.requests.append((url, json, headers))
        if self.raises is not None:
            raise self.raises
        message = json["messages"][0]
        to = message["destinations"][0]["to"]
        if self.fail_on is not None and to == self.fail_on:
            return FakeResponse(
                400,
                {
                    "requestError": {
                        "serviceException": {
                            "messageId": "BAD_REQUEST",
                            "text": "Invalid destination address",
                        }
                    }
                },
            )
        if self.response is not None:
            return self.response
        self.sent.append((to, message["content"]["text"]))
        return FakeResponse(
            200,
            {
                "bulkId": "bulk-1",
                "messages": [
                    {
                        "messageId": f"msg-{len(self.sent)}",
                        "status": {"groupId": 1, "groupName": "PENDING", "name": "PENDING_ACCEPTED"},
                        "destination": to,
                    }
                ],
            },
        )


def build_service(http: FakeHttp) -> BipService:
    return BipService(http=http)


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
        parts = BipService.split_sms_body("All done.")
        self.assertEqual(parts, ["All done."])

    def test_long_body_is_split_and_numbered(self):
        parts = BipService.split_sms_body(" ".join(["word"] * 600))

        self.assertGreater(len(parts), 1)
        self.assertTrue(parts[0].startswith(f"(1/{len(parts)})"))
        for part in parts:
            self.assertLessEqual(len(part), SMS_MAX_BODY_CHARS)

    def test_split_preserves_all_words(self):
        original = " ".join(f"w{i}" for i in range(800))
        rejoined = " ".join(
            part.split(") ", 1)[1] for part in BipService.split_sms_body(original)
        )
        self.assertEqual(rejoined.split(), original.split())

    def test_one_enormous_token_is_hard_split_rather_than_hanging(self):
        parts = BipService.split_sms_body("x" * 5000)

        self.assertGreater(len(parts), 1)
        for part in parts:
            self.assertLessEqual(len(part), SMS_MAX_BODY_CHARS)

    def test_empty_body_rejected(self):
        with self.assertRaises(ValueError):
            BipService.split_sms_body("   ")


class SendSmsTests(unittest.TestCase):
    def test_sends_to_several_recipients(self):
        http = FakeHttp()
        result = build_service(http).send_sms(
            ["801-647-7824", "+13853601934"], "Deploy is green."
        )

        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["sent"], 2)
        self.assertEqual(
            [to for to, _ in http.sent], ["+18016477824", "+13853601934"]
        )

    def test_accepts_a_bare_string_recipient(self):
        http = FakeHttp()
        result = build_service(http).send_sms("8016477824", "hi")

        self.assertEqual(result["sent"], 1)

    def test_one_bad_number_does_not_stop_the_others(self):
        http = FakeHttp()
        result = build_service(http).send_sms(
            ["not-a-number", "801-647-7824"], "hi"
        )

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["results"][0]["status"], "invalid")
        self.assertEqual(result["results"][1]["status"], "sent")

    def test_send_failure_is_reported_per_recipient(self):
        http = FakeHttp(fail_on="+18016477824")
        result = build_service(http).send_sms(
            ["801-647-7824", "+13853601934"], "hi"
        )

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["results"][0]["status"], "failed")
        self.assertIn("Invalid destination", result["results"][0]["error"])
        self.assertTrue(result["results"][0]["permanent"])

    def test_refuses_a_bulk_send(self):
        numbers = [f"+1801647{n:04d}" for n in range(SMS_MAX_RECIPIENTS + 1)]
        with self.assertRaises(SmsRecipientError):
            build_service(FakeHttp()).send_sms(numbers, "hi")

    def test_requires_at_least_one_recipient(self):
        with self.assertRaises(SmsRecipientError):
            build_service(FakeHttp()).send_sms([], "hi")

    def test_long_body_sends_as_multiple_messages(self):
        http = FakeHttp()
        result = build_service(http).send_sms(
            "801-647-7824", " ".join(["word"] * 600)
        )

        self.assertGreater(result["parts_per_recipient"], 1)
        self.assertEqual(len(http.sent), result["parts_per_recipient"])


class RecipientAllowlistTests(unittest.TestCase):
    @mock.patch.dict(
        "os.environ", {"NOVA_SMS_ALLOWED_RECIPIENTS": "801-647-7824"}, clear=False
    )
    def test_allowlist_blocks_other_numbers(self):
        http = FakeHttp()
        result = build_service(http).send_sms(
            ["+18016477824", "+15551234567"], "hi"
        )

        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["results"][1]["status"], "not_permitted")
        self.assertEqual([to for to, _ in http.sent], ["+18016477824"])

    @mock.patch.dict(
        "os.environ", {"NOVA_SMS_ALLOWED_RECIPIENTS": "801-647-7824"}, clear=False
    )
    def test_internal_callers_may_bypass_the_allowlist(self):
        # The dispatcher texting the user's own number already knows the
        # destination; the allowlist exists to constrain model-chosen ones.
        http = FakeHttp()
        result = build_service(http).send_sms(
            "+15551234567", "hi", allow_unlisted=True
        )

        self.assertEqual(result["sent"], 1)

    @mock.patch.dict("os.environ", {"NOVA_SMS_ALLOWED_RECIPIENTS": ""}, clear=False)
    def test_unset_allowlist_permits_any_number(self):
        http = FakeHttp()
        result = build_service(http).send_sms("+15551234567", "hi")

        self.assertEqual(result["sent"], 1)


class SenderAllowlistTests(unittest.TestCase):
    @mock.patch.dict("os.environ", {"NOVA_SMS_ALLOWED_SENDERS": ""}, clear=False)
    def test_defaults_to_the_users_own_number(self):
        self.assertEqual(BipService.allowed_sms_senders(), {"+18016477824"})

    @mock.patch.dict(
        "os.environ",
        {"NOVA_SMS_ALLOWED_SENDERS": "801-647-7824, +13853601934"},
        clear=False,
    )
    def test_accepts_several_and_normalizes_them(self):
        self.assertEqual(
            BipService.allowed_sms_senders(), {"+18016477824", "+13853601934"}
        )

    @mock.patch.dict(
        "os.environ", {"NOVA_SMS_ALLOWED_SENDERS": "garbage, 801-647-7824"}, clear=False
    )
    def test_unparseable_entries_are_dropped_not_fatal(self):
        # A typo in the allowlist must not open it up or crash the webhook.
        self.assertEqual(BipService.allowed_sms_senders(), {"+18016477824"})


class InfobipRequestTests(unittest.TestCase):
    def test_request_matches_what_infobip_expects(self):
        http = FakeHttp()
        build_service(http).send_sms("801-647-7824", "hi")

        url, payload, headers = http.requests[0]
        self.assertEqual(url, "https://abc123.api.infobip.com/sms/3/messages")
        self.assertEqual(headers["Authorization"], "App fake-bip-key")
        message = payload["messages"][0]
        self.assertEqual(message["sender"], "14355723870")
        self.assertEqual(message["destinations"], [{"to": "+18016477824"}])
        self.assertEqual(message["content"], {"text": "hi"})

    def test_base_url_with_scheme_is_kept(self):
        service = build_service(FakeHttp())
        service.base_url = "https://abc123.api.infobip.com/"

        self.assertEqual(service.send_url(), "https://abc123.api.infobip.com/sms/3/messages")

    def test_rejected_message_counts_as_a_permanent_failure(self):
        # Infobip can accept the request yet reject the message inside it.
        http = FakeHttp(
            response=FakeResponse(
                200,
                {
                    "messages": [
                        {
                            "messageId": "m1",
                            "status": {"groupName": "REJECTED", "description": "Not enough credits"},
                        }
                    ]
                },
            )
        )
        result = build_service(http).send_sms("801-647-7824", "hi")

        entry = result["results"][0]
        self.assertEqual(entry["status"], "failed")
        self.assertIn("Not enough credits", entry["error"])
        self.assertTrue(entry["permanent"])

    def test_network_failure_is_retryable(self):
        http = FakeHttp(raises=requests.ConnectionError("reset"))
        result = build_service(http).send_sms("801-647-7824", "hi")

        entry = result["results"][0]
        self.assertEqual(entry["status"], "failed")
        self.assertFalse(entry["permanent"])

    def test_rate_limit_and_server_errors_are_retryable(self):
        self.assertFalse(is_permanent_bip_error(BipRequestError("slow down", status=429)))
        self.assertFalse(is_permanent_bip_error(BipRequestError("oops", status=503)))
        self.assertTrue(is_permanent_bip_error(BipRequestError("bad key", status=401)))

    @mock.patch.dict("os.environ", {"BIP_SENDER": ""}, clear=False)
    def test_missing_configuration_refuses_to_send(self):
        with self.assertRaises(BipConfigurationError) as caught:
            BipService(http=FakeHttp()).send_sms("801-647-7824", "hi")

        self.assertIn("BIP_SENDER", str(caught.exception))


def basic(user: str, password: str) -> str:
    return "Basic " + b64encode(f"{user}:{password}".encode()).decode()


class InboundSecretTests(unittest.TestCase):
    """
    Infobip does not sign its forwards, so the shared secret is the only thing
    standing between the public URL and an agent loop with shell access.
    """

    @mock.patch.dict("os.environ", {"BIP_INBOUND_SECRET": "s3cret"}, clear=False)
    def test_accepts_the_secret_as_a_basic_auth_password(self):
        self.assertTrue(BipService.verify_inbound_secret(basic("infobip", "s3cret"), None))

    @mock.patch.dict("os.environ", {"BIP_INBOUND_SECRET": "s3cret"}, clear=False)
    def test_accepts_the_secret_as_a_query_token(self):
        self.assertTrue(BipService.verify_inbound_secret(None, "s3cret"))

    @mock.patch.dict("os.environ", {"BIP_INBOUND_SECRET": "s3cret"}, clear=False)
    def test_rejects_a_wrong_or_missing_secret(self):
        for authorization, token in (
            (None, None),
            (None, "wrong"),
            (basic("infobip", "wrong"), None),
            ("Bearer s3cret", None),
            ("Basic !!!not-base64", None),
        ):
            with self.subTest(authorization=authorization, token=token):
                self.assertFalse(BipService.verify_inbound_secret(authorization, token))

    @mock.patch.dict("os.environ", {"BIP_INBOUND_SECRET": ""}, clear=False)
    def test_fails_closed_without_a_configured_secret(self):
        # An empty secret must not match an empty token.
        self.assertFalse(BipService.verify_inbound_secret(None, ""))
        self.assertFalse(BipService.verify_inbound_secret(basic("x", ""), None))


if __name__ == "__main__":
    unittest.main()
