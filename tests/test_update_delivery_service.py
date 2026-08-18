import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from src.model.report_type import DeliveryStatus, ReportType
from src.model.update import Update
from src.service.update_delivery_service import (
    UpdateDeliveryService,
    describe_twilio_error,
    is_permanent_twilio_error,
)


class SimpleNamespace_Exception(Exception):
    """
    Stands in for twilio.base.exceptions.TwilioRestException.

    Only the attributes the classifier reads are modeled — status, code, msg —
    so the tests don't depend on the SDK's exception constructor signature.
    """

    def __init__(self, status=None, code=None, msg=""):
        super().__init__(msg)
        self.status = status
        self.code = code
        self.msg = msg


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 11, hour, minute, tzinfo=timezone.utc)


def make_update(
    id=1,
    message="Deploy finished cleanly.",
    report_type=ReportType.CALL,
    status=DeliveryStatus.PENDING,
    attempts=0,
    call_sid=None,
) -> Update:
    return Update(
        id=id,
        update_message=message,
        created_at=at(12),
        report_type=report_type,
        delivery_status=status,
        delivery_attempts=attempts,
        call_sid=call_sid,
    )


class FakeUpdateService:
    """Records state transitions so tests can assert on the delivery lifecycle."""

    def __init__(self, updates=()):
        self.updates = {u.id: u for u in updates}
        self.update_dao = self
        self.calls = []

    def get_pending_deliveries(self):
        return [
            u
            for u in self.updates.values()
            if u.delivery_status == DeliveryStatus.PENDING
        ]

    def get_update(self, update_id):
        return self.updates.get(int(update_id))

    def get_update_by_call_sid(self, call_sid):
        for update in self.updates.values():
            if update.call_sid == call_sid:
                return update
        return None

    def claim_for_delivery(self, update_id):
        update = self.updates.get(int(update_id))
        if update is None or update.delivery_status != DeliveryStatus.PENDING:
            return None
        update.delivery_status = DeliveryStatus.IN_PROGRESS
        self.calls.append(("claim", update_id))
        return update

    def mark_delivered(self, update_id):
        update = self.updates[int(update_id)]
        update.delivery_status = DeliveryStatus.DELIVERED
        update.is_viewed = True
        self.calls.append(("delivered", update_id))
        return update

    def mark_delivery_failed(self, update_id, error, attempts=None):
        update = self.updates[int(update_id)]
        update.delivery_status = DeliveryStatus.FAILED
        update.delivery_error = error
        if attempts is not None:
            update.delivery_attempts = attempts
        self.calls.append(("failed", update_id, error))
        return update

    def requeue_delivery(self, update_id, error=None, attempts=None):
        update = self.updates[int(update_id)]
        update.delivery_status = DeliveryStatus.PENDING
        update.delivery_error = error
        if attempts is not None:
            update.delivery_attempts = attempts
        self.calls.append(("requeued", update_id, attempts))
        return update

    # stands in for update_dao.set_delivery_state
    def set_delivery_state(
        self, id, status, call_sid=None, error=None, attempts=None, mark_viewed=False
    ):
        update = self.updates[int(id)]
        update.delivery_status = status
        if call_sid is not None:
            update.call_sid = call_sid
        if attempts is not None:
            update.delivery_attempts = attempts
        self.calls.append(("state", id, status, call_sid, attempts))
        return update


def build_service(updates=(), email_ok=True, twilio_ok=True, call_sid="CA123"):
    service = UpdateDeliveryService.__new__(UpdateDeliveryService)
    service.update_service = FakeUpdateService(updates)

    service.email_service = SimpleNamespace(
        sent=[],
        send_email=lambda to, subject, body, **kw: (
            service.email_service.sent.append((to, subject, body)) or email_ok
        ),
    )

    service.twilio_service = SimpleNamespace(
        placed=[],
        texted=[],
        is_configured=lambda: (twilio_ok, None if twilio_ok else "Missing configuration: X."),
        is_configured_for_sms=lambda: (
            twilio_ok,
            None if twilio_ok else "Missing configuration: X.",
        ),
        place_report_call=lambda update_id: (
            service.twilio_service.placed.append(update_id) or call_sid
        ),
        send_sms=lambda to, body, **kw: (
            service.twilio_service.texted.append((to, body))
            or {"status": "sent", "sent": 1, "total": 1, "results": []}
        ),
    )
    return service


class QuietHoursTests(unittest.TestCase):
    @mock.patch.dict("os.environ", {"NOVA_QUIET_HOURS_START": "22", "NOVA_QUIET_HOURS_END": "8"})
    def test_window_wraps_midnight(self):
        for hour, expected in {
            21: False,
            22: True,
            23: True,
            0: True,
            3: True,
            7: True,
            8: False,
            12: False,
        }.items():
            with self.subTest(hour=hour):
                self.assertEqual(
                    UpdateDeliveryService.in_quiet_hours(at(hour)), expected
                )

    @mock.patch.dict("os.environ", {"NOVA_QUIET_HOURS_START": "1", "NOVA_QUIET_HOURS_END": "5"})
    def test_window_within_one_day(self):
        self.assertFalse(UpdateDeliveryService.in_quiet_hours(at(0)))
        self.assertTrue(UpdateDeliveryService.in_quiet_hours(at(3)))
        self.assertFalse(UpdateDeliveryService.in_quiet_hours(at(6)))

    @mock.patch.dict("os.environ", {"NOVA_QUIET_HOURS_START": "0", "NOVA_QUIET_HOURS_END": "0"})
    def test_equal_bounds_disables_quiet_hours(self):
        self.assertFalse(UpdateDeliveryService.in_quiet_hours(at(3)))

    @mock.patch.dict("os.environ", {"NOVA_QUIET_HOURS_START": "not-a-number"})
    def test_bad_config_falls_back_to_default(self):
        self.assertEqual(UpdateDeliveryService.quiet_hours()[0], 22)


class EmailDeliveryTests(unittest.TestCase):
    @mock.patch.dict("os.environ", {"NOVA_REPORT_EMAIL": "me@example.com"})
    def test_sends_and_marks_delivered(self):
        service = build_service([make_update(report_type=ReportType.EMAIL)])

        result = service.deliver_pending(now=at(12))

        self.assertEqual(result["delivered"], 1)
        to, subject, body = service.email_service.sent[0]
        self.assertEqual(to, ["me@example.com"])
        self.assertIn("Nova update", subject)
        self.assertEqual(body, "Deploy finished cleanly.")
        self.assertEqual(
            service.update_service.updates[1].delivery_status, DeliveryStatus.DELIVERED
        )

    @mock.patch.dict("os.environ", {"NOVA_REPORT_EMAIL": "me@example.com"})
    def test_email_is_not_held_during_quiet_hours(self):
        service = build_service([make_update(report_type=ReportType.EMAIL)])

        result = service.deliver_pending(now=at(3))

        self.assertEqual(result["delivered"], 1)

    @mock.patch.dict("os.environ", {}, clear=True)
    def test_missing_recipient_fails_delivery(self):
        service = build_service([make_update(report_type=ReportType.EMAIL)])

        result = service.deliver_pending(now=at(12))

        self.assertEqual(result["failed"], 1)
        self.assertIn(
            "No report recipient configured",
            service.update_service.updates[1].delivery_error,
        )

    @mock.patch.dict("os.environ", {"NOVA_REPORT_EMAIL": "me@example.com"})
    def test_smtp_failure_requeues(self):
        service = build_service(
            [make_update(report_type=ReportType.EMAIL)], email_ok=False
        )

        service.deliver_pending(now=at(12))

        self.assertEqual(
            service.update_service.updates[1].delivery_status, DeliveryStatus.PENDING
        )


class CallDeliveryTests(unittest.TestCase):
    @mock.patch.dict("os.environ", {"NOVA_QUIET_HOURS_START": "22", "NOVA_QUIET_HOURS_END": "8"})
    def test_places_call_and_stays_in_progress(self):
        service = build_service([make_update()])

        result = service.deliver_pending(now=at(12))

        self.assertEqual(result["delivered"], 1)
        self.assertEqual(service.twilio_service.placed, [1])
        update = service.update_service.updates[1]
        # The call is only ringing; /calls/status decides whether it counted.
        self.assertEqual(update.delivery_status, DeliveryStatus.IN_PROGRESS)
        self.assertEqual(update.call_sid, "CA123")
        self.assertEqual(update.delivery_attempts, 1)

    @mock.patch.dict("os.environ", {"NOVA_QUIET_HOURS_START": "22", "NOVA_QUIET_HOURS_END": "8"})
    def test_defers_during_quiet_hours_without_claiming(self):
        service = build_service([make_update()])

        result = service.deliver_pending(now=at(2))

        self.assertEqual(result["deferred"], 1)
        self.assertEqual(service.twilio_service.placed, [])
        self.assertEqual(
            service.update_service.updates[1].delivery_status, DeliveryStatus.PENDING
        )

    @mock.patch.dict(
        "os.environ",
        {"NOVA_MAX_CALLS_PER_PASS": "1", "NOVA_QUIET_HOURS_START": "22", "NOVA_QUIET_HOURS_END": "8"},
    )
    def test_caps_calls_per_pass(self):
        service = build_service([make_update(id=1), make_update(id=2)])

        result = service.deliver_pending(now=at(12))

        self.assertEqual(result["delivered"], 1)
        self.assertEqual(result["deferred"], 1)
        self.assertEqual(len(service.twilio_service.placed), 1)

    def test_unconfigured_twilio_fails_rather_than_looping(self):
        service = build_service([make_update()], twilio_ok=False)

        result = service.deliver_pending(now=at(12))

        self.assertEqual(result["failed"], 1)
        self.assertEqual(
            service.update_service.updates[1].delivery_status, DeliveryStatus.FAILED
        )

    @mock.patch.dict("os.environ", {"NOVA_MAX_DELIVERY_ATTEMPTS": "2"})
    def test_gives_up_past_attempt_ceiling(self):
        service = build_service([make_update(attempts=2)])

        result = service.deliver_pending(now=at(12))

        self.assertEqual(result["failed"], 1)
        self.assertEqual(service.twilio_service.placed, [])
        self.assertIn("Gave up", service.update_service.updates[1].delivery_error)


class TwilioErrorClassificationTests(unittest.TestCase):
    """
    A rejected number fails the same way every minute. Retrying it burns the
    attempt budget and delays the honest failure showing up in the badge.
    """

    @staticmethod
    def _twilio_error(status, code, msg="Something went wrong"):
        return SimpleNamespace_Exception(status=status, code=code, msg=msg)

    def test_unverified_from_number_is_permanent(self):
        exc = self._twilio_error(400, 21210, "The source phone number provided is not yet verified")
        self.assertTrue(is_permanent_twilio_error(exc))

    def test_rate_limit_is_retryable(self):
        self.assertFalse(is_permanent_twilio_error(self._twilio_error(429, 20429)))

    def test_server_error_is_retryable(self):
        self.assertFalse(is_permanent_twilio_error(self._twilio_error(503, 20500)))

    def test_plain_exception_is_retryable(self):
        self.assertFalse(is_permanent_twilio_error(RuntimeError("connection reset")))

    def test_description_is_one_clean_line_with_the_code(self):
        exc = self._twilio_error(400, 21210, "\x1b[31mnot yet\x1b[0m  verified\n\nfor your account")
        described = describe_twilio_error(exc)

        self.assertNotIn("\x1b", described)
        self.assertNotIn("\n", described)
        self.assertIn("[21210]", described)
        self.assertIn("not yet verified for your account", described)

    def test_permanent_rejection_fails_immediately_without_retrying(self):
        service = build_service([make_update()])

        def reject(update_id):
            raise self._twilio_error(400, 21210, "not verified")

        service.twilio_service.place_report_call = reject

        result = service.deliver_pending(now=at(12))

        self.assertEqual(result["failed"], 1)
        update = service.update_service.updates[1]
        self.assertEqual(update.delivery_status, DeliveryStatus.FAILED)
        self.assertIn("21210", update.delivery_error)

    def test_transient_failure_still_requeues(self):
        service = build_service([make_update()])

        def flake(update_id):
            raise self._twilio_error(503, 20500, "service unavailable")

        service.twilio_service.place_report_call = flake

        result = service.deliver_pending(now=at(12))

        self.assertEqual(result["deferred"], 1)
        self.assertEqual(
            service.update_service.updates[1].delivery_status, DeliveryStatus.PENDING
        )


class SmsDeliveryTests(unittest.TestCase):
    @mock.patch.dict("os.environ", {"TWILIO_TARGET_NUMBER": "+18016477824"})
    def test_sends_and_marks_delivered(self):
        service = build_service([make_update(report_type=ReportType.SMS)])

        result = service.deliver_pending(now=at(12))

        self.assertEqual(result["delivered"], 1)
        self.assertEqual(service.twilio_service.texted[0][0], "+18016477824")
        self.assertEqual(
            service.update_service.updates[1].delivery_status, DeliveryStatus.DELIVERED
        )

    @mock.patch.dict("os.environ", {"TWILIO_TARGET_NUMBER": "+18016477824"})
    def test_sms_is_not_held_during_quiet_hours(self):
        # A text at 3am is silent-able by the phone; a phone call is not.
        service = build_service([make_update(report_type=ReportType.SMS)])

        self.assertEqual(service.deliver_pending(now=at(3))["delivered"], 1)

    @mock.patch.dict("os.environ", {"TWILIO_TARGET_NUMBER": ""}, clear=False)
    def test_missing_recipient_fails_delivery(self):
        service = build_service([make_update(report_type=ReportType.SMS)])

        result = service.deliver_pending(now=at(12))

        self.assertEqual(result["failed"], 1)
        self.assertIn(
            "No SMS recipient configured",
            service.update_service.updates[1].delivery_error,
        )

    @mock.patch.dict("os.environ", {"TWILIO_TARGET_NUMBER": "+18016477824"})
    def test_partial_send_is_requeued_not_marked_delivered(self):
        service = build_service([make_update(report_type=ReportType.SMS)])
        service.twilio_service.send_sms = lambda to, body, **kw: {
            "status": "failed",
            "results": [{"to": to, "status": "failed", "error": "carrier down"}],
        }

        result = service.deliver_pending(now=at(12))

        self.assertEqual(result["deferred"], 1)
        update = service.update_service.updates[1]
        self.assertEqual(update.delivery_status, DeliveryStatus.PENDING)
        self.assertFalse(update.is_viewed)


class UndeliverableTypeTests(unittest.TestCase):
    def test_chat_settles_without_a_channel(self):
        service = build_service([make_update(report_type=ReportType.CHAT)])

        result = service.deliver_pending(now=at(12))

        self.assertEqual(result["failed"], 1)
        update = service.update_service.updates[1]
        self.assertEqual(update.delivery_status, DeliveryStatus.FAILED)
        # The update itself survives — it is still in the badge.
        self.assertFalse(update.is_viewed)


class SettleCallTests(unittest.TestCase):
    def test_completed_alone_does_not_count_as_delivered(self):
        """
        A call answered by voicemail is hung up on and still reports
        'completed'. Trusting that status marked the update delivered and
        viewed, burying a report the user never heard.
        """
        service = build_service(
            [make_update(status=DeliveryStatus.IN_PROGRESS, call_sid="CA123", attempts=1)]
        )

        result = service.settle_call("CA123", "completed")

        self.assertEqual(result["status"], "requeued")
        update = service.update_service.updates[1]
        self.assertEqual(update.delivery_status, DeliveryStatus.PENDING)
        self.assertFalse(update.is_viewed)

    def test_relay_confirmed_delivery_is_respected(self):
        # The relay marks DELIVERED once it has actually spoken the report;
        # the status callback must not undo that.
        service = build_service(
            [make_update(status=DeliveryStatus.DELIVERED, call_sid="CA123", attempts=1)]
        )

        result = service.settle_call("CA123", "completed")

        self.assertEqual(result["status"], "delivered")
        self.assertEqual(
            service.update_service.updates[1].delivery_status, DeliveryStatus.DELIVERED
        )

    @mock.patch.dict("os.environ", {"NOVA_MAX_DELIVERY_ATTEMPTS": "3"})
    def test_completed_without_delivery_gives_up_at_the_ceiling(self):
        service = build_service(
            [make_update(status=DeliveryStatus.IN_PROGRESS, call_sid="CA123", attempts=3)]
        )

        result = service.settle_call("CA123", "completed")

        self.assertEqual(result["status"], "failed")
        update = service.update_service.updates[1]
        self.assertEqual(update.delivery_status, DeliveryStatus.FAILED)
        self.assertFalse(update.is_viewed)

    @mock.patch.dict("os.environ", {"NOVA_MAX_DELIVERY_ATTEMPTS": "3"})
    def test_no_answer_requeues_for_another_attempt(self):
        service = build_service(
            [make_update(status=DeliveryStatus.IN_PROGRESS, call_sid="CA123", attempts=1)]
        )

        result = service.settle_call("CA123", "no-answer")

        self.assertEqual(result["status"], "requeued")
        update = service.update_service.updates[1]
        self.assertEqual(update.delivery_status, DeliveryStatus.PENDING)
        self.assertFalse(update.is_viewed)

    @mock.patch.dict("os.environ", {"NOVA_MAX_DELIVERY_ATTEMPTS": "3"})
    def test_no_answer_at_ceiling_gives_up(self):
        service = build_service(
            [make_update(status=DeliveryStatus.IN_PROGRESS, call_sid="CA123", attempts=3)]
        )

        result = service.settle_call("CA123", "no-answer")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(
            service.update_service.updates[1].delivery_status, DeliveryStatus.FAILED
        )

    def test_unknown_call_sid_is_ignored(self):
        service = build_service([make_update()])

        result = service.settle_call("CA-nope", "completed")

        self.assertEqual(result["status"], "unknown_call")


class BadgeOnlyTests(unittest.TestCase):
    def test_updates_without_a_report_type_are_never_picked_up(self):
        service = build_service(
            [make_update(report_type=None, status=DeliveryStatus.NOT_REQUIRED)]
        )

        result = service.deliver_pending(now=at(12))

        self.assertEqual(result["pending"], 0)
        self.assertEqual(service.email_service.sent, [])
        self.assertEqual(service.twilio_service.placed, [])


if __name__ == "__main__":
    unittest.main()
