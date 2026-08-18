"""
How Nova delivers the outcome of background work back to the user.

A report type is an *intent*, chosen when work is spawned ("call me when this
is done") and carried on the Update the work produces. Delivery itself happens
system-side: the update lands in the table with a pending delivery status and
UpdateDeliveryService picks it up. Nothing is delivered from inside the agent
run, so a delivery can be retried, rate-limited, or deferred past quiet hours
without the agent needing to know.
"""

from enum import StrEnum


class ReportType(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    CALL = "call"
    CHAT = "chat"


# Types with a delivery channel behind them today. CHAT is modeled so the
# column and the tool schema don't have to change when it lands, but an update
# asking for it stays in the badge rather than failing — see
# UpdateDeliveryService.deliver_update.
SUPPORTED_REPORT_TYPES: frozenset[ReportType] = frozenset(
    {ReportType.EMAIL, ReportType.CALL, ReportType.SMS}
)


class DeliveryStatus(StrEnum):
    """
    Lifecycle of one update's delivery.

    NOT_REQUIRED is the default: an update with no report type is badge-only
    and was never meant to go anywhere. Keeping it in the same column (rather
    than leaving delivery_status null) means the dispatcher's query is a single
    equality check on PENDING and can never accidentally pick up a plain update.
    """

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    FAILED = "failed"
