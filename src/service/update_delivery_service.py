"""
Delivering updates to the user, outside the agent that produced them.

Background work records an Update carrying a report_type, and this service is
what turns that intent into an email or a phone call. Nothing here runs inside
an agent loop: by the time an update is delivered the agent that wrote it has
exited, which is exactly the point — a delivery can be retried after a missed
call, held until the user is awake, or dropped when the channel isn't
configured, none of which an agent mid-run could do.

Email is delivered outright. A call only *starts* here — the call is placed,
and the conversation itself happens in call_controller once Twilio connects
back. So a call update stays IN_PROGRESS until the call ends, and the status
callback is what finally settles it.
"""

import os
from datetime import datetime, time, timezone

from src.model.report_type import SUPPORTED_REPORT_TYPES, DeliveryStatus, ReportType
from src.model.update import Update
from src.service.email_service import EmailService
from src.service.twilio_service import (
    SmsRecipientError,
    TwilioConfigurationError,
    TwilioService,
    describe_twilio_error,
    is_permanent_twilio_error,
)
from src.service.update_service import UpdateService

# A call the user never picks up is retried, but not forever — after this many
# attempts the update falls back to being an ordinary unread badge.
DEFAULT_MAX_DELIVERY_ATTEMPTS = 3

# Ceiling on calls placed per dispatcher pass. A burst of finished background
# work should not turn into a burst of phone calls.
DEFAULT_MAX_CALLS_PER_PASS = 1

# Quiet hours, local time, inclusive of the start hour and exclusive of the
# end. Calls due inside the window wait; email is unaffected because an email
# arriving at 3am costs the user nothing.
DEFAULT_QUIET_HOURS_START = 22
DEFAULT_QUIET_HOURS_END = 8


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"{name}='{raw}' is not an integer; using default {default}.")
        return default


# Re-exported so existing callers and tests keep importing these from here;
# they live with the rest of the Twilio-specific knowledge.
__all__ = [
    "UpdateDeliveryService",
    "describe_twilio_error",
    "is_permanent_twilio_error",
]


class UpdateDeliveryService:
    def __init__(self) -> None:
        self.update_service = UpdateService()
        self.email_service = EmailService()
        self.twilio_service = TwilioService()

    # ---------- policy ----------

    @staticmethod
    def quiet_hours() -> tuple[int, int]:
        return (
            _env_int("NOVA_QUIET_HOURS_START", DEFAULT_QUIET_HOURS_START),
            _env_int("NOVA_QUIET_HOURS_END", DEFAULT_QUIET_HOURS_END),
        )

    @classmethod
    def in_quiet_hours(cls, now: datetime | None = None) -> bool:
        """
        Whether calling right now would be antisocial.

        Local time, because "10pm" is a local-clock concept. A window whose
        start is later than its end wraps midnight, which is the normal case.
        """
        now = now or datetime.now().astimezone()
        start_hour, end_hour = cls.quiet_hours()
        if start_hour == end_hour:
            return False

        current = time(now.hour, now.minute)
        start = time(start_hour % 24, 0)
        end = time(end_hour % 24, 0)

        if start < end:
            return start <= current < end
        return current >= start or current < end

    @staticmethod
    def max_delivery_attempts() -> int:
        return _env_int("NOVA_MAX_DELIVERY_ATTEMPTS", DEFAULT_MAX_DELIVERY_ATTEMPTS)

    @staticmethod
    def max_calls_per_pass() -> int:
        return _env_int("NOVA_MAX_CALLS_PER_PASS", DEFAULT_MAX_CALLS_PER_PASS)

    @staticmethod
    def report_email_recipient() -> str | None:
        return os.getenv("NOVA_REPORT_EMAIL") or os.getenv("EMAIL_SENDER")

    # ---------- dispatch ----------

    def deliver_pending(self, now: datetime | None = None) -> dict:
        """
        Deliver everything that is due. Called by the worker on a schedule.

        One update failing must not stop the rest, so every delivery is
        contained. Calls are capped per pass and skipped entirely during quiet
        hours; the updates stay queued and go out on a later pass.
        """
        now = now or datetime.now().astimezone()

        try:
            pending = self.update_service.get_pending_deliveries()
        except Exception as exc:
            print(f"Failed to load pending deliveries: {exc}")
            return {"pending": 0, "delivered": 0, "deferred": 0, "failed": 0}

        quiet = self.in_quiet_hours(now)
        calls_remaining = self.max_calls_per_pass()

        delivered = 0
        deferred = 0
        failed = 0

        for update in pending:
            report_type = update.report_type

            if report_type not in SUPPORTED_REPORT_TYPES:
                # Recorded intent we can't act on (sms, chat). Settle it now so
                # it stops being scanned on every pass; the update itself is
                # still in the badge, which is the honest outcome.
                self.update_service.mark_delivery_failed(
                    update.id,
                    f"No delivery channel for report type '{report_type}'.",
                )
                failed += 1
                continue

            if report_type == ReportType.CALL:
                if quiet:
                    deferred += 1
                    continue
                if calls_remaining <= 0:
                    deferred += 1
                    continue

            outcome = self.deliver_update(update)
            if outcome == "delivered":
                delivered += 1
                if report_type == ReportType.CALL:
                    calls_remaining -= 1
            elif outcome == "deferred":
                deferred += 1
            else:
                failed += 1

        summary = {
            "pending": len(pending),
            "delivered": delivered,
            "deferred": deferred,
            "failed": failed,
            "quiet_hours": quiet,
        }
        if pending:
            print(f"deliver_pending: {summary}")
        return summary

    def deliver_update(self, update: Update) -> str:
        """
        Deliver one update. Returns "delivered", "deferred", or "failed".

        "delivered" means handed to the channel — for a call that means the
        call was placed, not that the user picked up; the status callback
        settles that later.
        """
        claimed = self.update_service.claim_for_delivery(update.id)
        if claimed is None:
            # Another dispatcher took it between the query and here.
            return "deferred"

        attempts = (claimed.delivery_attempts or 0) + 1

        try:
            if claimed.report_type == ReportType.EMAIL:
                return self._deliver_email(claimed, attempts)
            if claimed.report_type == ReportType.SMS:
                return self._deliver_sms(claimed, attempts)
            if claimed.report_type == ReportType.CALL:
                return self._deliver_call(claimed, attempts)

            self.update_service.mark_delivery_failed(
                claimed.id,
                f"No delivery channel for report type '{claimed.report_type}'.",
                attempts=attempts,
            )
            return "failed"
        except Exception as exc:
            # Never leave a claimed update stuck IN_PROGRESS: an unexpected
            # error here would otherwise strand it out of the queue forever.
            print(f"Delivery of update {claimed.id} raised: {exc}")
            self._settle_or_retry(claimed, attempts, str(exc))
            return "failed"

    # ---------- channels ----------

    def _deliver_email(self, update: Update, attempts: int) -> str:
        recipient = self.report_email_recipient()
        if not recipient:
            self.update_service.mark_delivery_failed(
                update.id,
                "No report recipient configured (set NOVA_REPORT_EMAIL or EMAIL_SENDER).",
                attempts=attempts,
            )
            return "failed"

        subject = self._email_subject(update)
        sent = self.email_service.send_email(
            to=[recipient],
            subject=subject,
            body=update.update_message or "",
        )
        if not sent:
            # EmailService swallows SMTP errors and returns False, so this is
            # as much detail as there is. SMTP failures are usually transient.
            print(f"Update {update.id}: SMTP send failed (attempt {attempts}).")
            self._settle_or_retry(update, attempts, "SMTP send failed.")
            return "deferred" if attempts < self.max_delivery_attempts() else "failed"

        self.update_service.mark_delivered(update.id)
        return "delivered"

    @staticmethod
    def _email_subject(update: Update) -> str:
        created = update.created_at
        stamp = (
            created.strftime("%b %d")
            if hasattr(created, "strftime")
            else datetime.now(timezone.utc).strftime("%b %d")
        )
        return f"Nova update — {stamp}"

    def _deliver_sms(self, update: Update, attempts: int) -> str:
        """
        Text the update to the user.

        Unlike a call, an SMS is delivered the moment Twilio accepts it —
        there is no session to wait on, so this settles the update itself.
        """
        recipient = (os.getenv("TWILIO_TARGET_NUMBER") or "").strip()
        if not recipient:
            self.update_service.mark_delivery_failed(
                update.id,
                "No SMS recipient configured (set TWILIO_TARGET_NUMBER).",
                attempts=attempts,
            )
            return "failed"

        configured, problem = self.twilio_service.is_configured_for_sms()
        if not configured:
            self.update_service.mark_delivery_failed(
                update.id, f"Cannot send SMS: {problem}", attempts=attempts
            )
            return "failed"

        try:
            result = self.twilio_service.send_sms(
                recipient, update.update_message or "", allow_unlisted=True
            )
        except (TwilioConfigurationError, SmsRecipientError) as exc:
            self.update_service.mark_delivery_failed(
                update.id, f"Cannot send SMS: {exc}", attempts=attempts
            )
            return "failed"
        except Exception as exc:
            reason = describe_twilio_error(exc)
            if is_permanent_twilio_error(exc):
                print(f"Update {update.id}: SMS rejected permanently — {reason}")
                self.update_service.mark_delivery_failed(
                    update.id, f"SMS rejected: {reason}", attempts=attempts
                )
                return "failed"
            print(f"Update {update.id}: SMS could not be sent — {reason}")
            self._settle_or_retry(update, attempts, f"SMS could not be sent: {reason}")
            return "deferred"

        if result.get("status") == "sent":
            self.update_service.mark_delivered(update.id)
            print(f"Update {update.id} delivered by SMS.")
            return "delivered"

        # send_sms reports per recipient and never raises for a rejected
        # number, so a non-sent status here is the failure detail.
        failures = "; ".join(
            entry.get("error", "unknown error")
            for entry in result.get("results", [])
            if entry.get("status") != "sent"
        )
        self._settle_or_retry(update, attempts, f"SMS not delivered: {failures}")
        return "deferred"

    def _deliver_call(self, update: Update, attempts: int) -> str:
        configured, problem = self.twilio_service.is_configured()
        if not configured:
            # Not the update's fault and not worth burning an attempt on, but
            # retrying every minute against a deployment with no Twilio
            # credentials is noise — fail it and leave it in the badge.
            self.update_service.mark_delivery_failed(
                update.id,
                f"Cannot place call: {problem}",
                attempts=attempts,
            )
            return "failed"

        if attempts > self.max_delivery_attempts():
            self.update_service.mark_delivery_failed(
                update.id,
                f"Gave up after {attempts - 1} unanswered call attempts.",
                attempts=attempts - 1,
            )
            return "failed"

        try:
            call_sid = self.twilio_service.place_report_call(update.id)
        except TwilioConfigurationError as exc:
            print(f"Update {update.id}: cannot place call — {exc}")
            self.update_service.mark_delivery_failed(
                update.id, f"Cannot place call: {exc}", attempts=attempts
            )
            return "failed"
        except Exception as exc:
            reason = describe_twilio_error(exc)
            # A rejected number or a malformed request will be rejected again
            # in sixty seconds and every minute after that. Only retry things
            # that could plausibly succeed later.
            if is_permanent_twilio_error(exc):
                print(f"Update {update.id}: call rejected permanently — {reason}")
                self.update_service.mark_delivery_failed(
                    update.id, f"Call rejected: {reason}", attempts=attempts
                )
                return "failed"

            print(f"Update {update.id}: call could not be placed — {reason}")
            self._settle_or_retry(update, attempts, f"Call could not be placed: {reason}")
            return "deferred"

        # Deliberately left IN_PROGRESS with the sid recorded: the call is
        # ringing, and /calls/status decides whether it counted.
        self.update_service.update_dao.set_delivery_state(
            update.id,
            DeliveryStatus.IN_PROGRESS,
            call_sid=call_sid,
            attempts=attempts,
        )
        print(f"Placed call {call_sid} to deliver update {update.id}.")
        return "delivered"

    # ---------- outcome from the call status callback ----------

    def settle_call(self, call_sid: str, call_status: str) -> dict:
        """
        Record how a report call ended.

        Twilio's "completed" only means the call reached a terminal state, NOT
        that the user heard anything: a call answered by voicemail is hung up
        on by /calls/answer and still completes. So delivery is not decided
        here — the relay session marks the update DELIVERED once it has
        actually spoken the report, and this method's job is to notice when
        that never happened and put the update back on the queue.
        """
        update = self.update_service.get_update_by_call_sid(call_sid)
        if update is None:
            return {"status": "unknown_call", "call_sid": call_sid}

        status = (call_status or "").strip().lower()

        if update.delivery_status == DeliveryStatus.DELIVERED:
            # The relay already confirmed the report was read out.
            return {"status": "delivered", "update_id": update.id}

        attempts = update.delivery_attempts or 0

        if status == "completed":
            # Connected, but nothing was spoken — answering machine, or the
            # caller hung up before Nova got through the report.
            if attempts >= self.max_delivery_attempts():
                self.update_service.mark_delivery_failed(
                    update.id,
                    f"Call completed after {attempts} attempts without the "
                    "report being delivered (voicemail or early hangup).",
                    attempts=attempts,
                )
                return {"status": "failed", "update_id": update.id}
            self.update_service.requeue_delivery(
                update.id,
                error="Call completed without the report being delivered "
                "(voicemail or early hangup).",
                attempts=attempts,
            )
            return {"status": "requeued", "update_id": update.id, "attempts": attempts}
        if attempts >= self.max_delivery_attempts():
            self.update_service.mark_delivery_failed(
                update.id,
                f"Call ended as '{status}' after {attempts} attempts.",
                attempts=attempts,
            )
            return {"status": "failed", "update_id": update.id}

        self.update_service.requeue_delivery(
            update.id, error=f"Call ended as '{status}'.", attempts=attempts
        )
        return {"status": "requeued", "update_id": update.id, "attempts": attempts}

    def _settle_or_retry(self, update: Update, attempts: int, error: str) -> None:
        """Requeue a failed attempt, or give up once the ceiling is reached."""
        if attempts >= self.max_delivery_attempts():
            self.update_service.mark_delivery_failed(
                update.id, error, attempts=attempts
            )
            return
        self.update_service.requeue_delivery(update.id, error=error, attempts=attempts)
