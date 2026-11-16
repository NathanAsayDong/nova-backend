"""
How Nova delivers the outcome of background work back to the user.

A report type is an *intent*, chosen when work is spawned ("call me when this
is done") and carried on the Update the work produces. Delivery itself happens
system-side: the update lands in the table with a pending delivery status and
UpdateDeliveryService picks it up. Nothing is delivered from inside the agent
run, so a delivery can be retried, rate-limited, or deferred past quiet hours
without the agent needing to know.
"""

import json
from enum import StrEnum


class ReportType(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    CALL = "call"
    CHAT = "chat"
    # Proactive sidekick speech (see src/service/sidekick_service.py): when
    # sidekick mode is on and Nova is idle, the result is spoken immediately
    # through the live /ws/sidekick connection. When it isn't — mid
    # conversation, or sidekick off — this channel is a no-op and the result
    # still reaches Nate the existing way, via the next-turn notification
    # injection (see AgentLoop._conversation_turn), same as any other
    # kind-tagged update.
    SPEAK = "speak"


# Types with a delivery channel behind them today. CHAT is modeled so the
# column and the tool schema don't have to change when it lands, but an update
# asking for it stays in the badge rather than failing — see
# UpdateDeliveryService.deliver_update.
SUPPORTED_REPORT_TYPES: frozenset[ReportType] = frozenset(
    {ReportType.EMAIL, ReportType.CALL, ReportType.SMS, ReportType.SPEAK}
)


def normalize_report_types(value: "str | list | tuple | set | ReportType | None") -> list[ReportType]:
    """
    Turn whatever shape a report_type arrived in — None, a bare string
    ("email"), a JSON-encoded list stored on the row ('["chat", "speak"]'),
    or an actual list/tuple of strings — into a de-duplicated, order-
    preserving list of ReportType.

    This is the one place that understands both the legacy single-string
    shape (every row and caller that predates multi-channel reporting) and
    the new list shape, so every model and service can stay backward
    compatible by routing through here instead of re-deriving the logic.
    """
    if value is None:
        return []
    if isinstance(value, ReportType):
        return [value]
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return []
        if candidate.startswith("["):
            try:
                parsed = json.loads(candidate)
            except (TypeError, ValueError):
                parsed = None
            if isinstance(parsed, list):
                return normalize_report_types(parsed)
        try:
            return [ReportType(candidate.lower())]
        except ValueError:
            raise ValueError(
                f"Unknown report_type '{value}'. Valid types are "
                f"{[str(t) for t in ReportType]}."
            )
    if isinstance(value, (list, tuple, set)):
        seen: set[ReportType] = set()
        result: list[ReportType] = []
        for item in value:
            for parsed_type in normalize_report_types(item):
                if parsed_type not in seen:
                    seen.add(parsed_type)
                    result.append(parsed_type)
        return result
    raise ValueError(f"Unsupported report_type value: {value!r}")


def encode_report_types(value: "str | list | tuple | set | ReportType | None") -> str | None:
    """
    The text this normalizes to for storage in the `report_type` column.

    A single channel is stored as its bare value ("email") — exactly what
    every row written before multi-channel reporting already contains, so
    nothing needs a migration to keep reading. Two or more channels are
    stored as a JSON array ('["chat", "speak"]'); `normalize_report_types`
    is what decodes that back out.
    """
    types = normalize_report_types(value)
    if not types:
        return None
    if len(types) == 1:
        return str(types[0])
    return json.dumps([str(t) for t in types])


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
