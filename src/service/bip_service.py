"""
Text messaging through Infobip ("BIP"), and the trust boundary around it.

Nova texts in three ways — the send_sms tool, an update whose report_type is
sms, and the reply to a text the user sent in — and all of them go out through
here. Twilio still carries voice calls; its messaging is disabled on the
account, which is why SMS lives with a different provider.

The Infobip account and sender number are shared with admin-api, so the
inbound side matters more than usual: Infobip forwards every text that number
receives to /sms/inbound, including replies from admin-api's own users. Those
fall outside the sender allowlist and are ignored. And because an inbound text
starts an agent loop holding run_terminal_command and run_sql, while Infobip
does not sign its forwards the way Twilio does, the webhook is gated on a
shared secret first and the sender allowlist second — the "from" field alone
is just a JSON value anyone could write.
"""

import hmac
import os
import re
from base64 import b64decode

import requests

SMS_INBOUND_PATH = "/sms/inbound"

# Infobip concatenates a long text itself, but Nova's replies are split into
# numbered parts at the same size Twilio allowed so a reply reads the same on
# either provider and a runaway body never becomes one enormous billed send.
SMS_MAX_BODY_CHARS = 1600
SMS_SPLIT_CHARS = 1500

# One agent turn should never fan out into a bulk send. This is a blast-radius
# cap, not a product limit; a legitimate "text these three people" is fine.
SMS_MAX_RECIPIENTS = 10

# Default country code for numbers written the way people say them out loud
# ("801 647 7824").
DEFAULT_COUNTRY_CODE = "+1"

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")

SEND_PATH = "/sms/3/messages"
REQUEST_TIMEOUT_SECONDS = 15

# Infobip answers a send with a status per message. These groups mean the
# message will never arrive; PENDING and ACCEPTED mean Infobip has taken it,
# which is all a send can know.
_REJECTED_GROUPS = {"REJECTED", "UNDELIVERABLE", "EXPIRED"}


class BipConfigurationError(RuntimeError):
    """Raised when a text is attempted without the configuration to send it."""


class SmsRecipientError(ValueError):
    """Raised when a destination number is unusable or not permitted."""


class BipRequestError(RuntimeError):
    """
    Infobip refused a send.

    `status` is the HTTP status for a request-level failure, or None when the
    request was accepted but the message itself was rejected — which is just
    as permanent, so `permanent` is carried explicitly rather than derived.
    """

    def __init__(self, message: str, status: int | None = None, permanent: bool = False):
        super().__init__(message)
        self.status = status
        self.permanent = permanent


def is_permanent_bip_error(exc: Exception) -> bool:
    """
    Whether retrying this send could ever succeed.

    A 4xx is a bad key, a bad sender or a bad destination, none of which
    changes by waiting. 429 is rate limiting, an explicit "try later", and a
    5xx or a dropped connection is Infobip's problem or the network's.
    """
    if not isinstance(exc, BipRequestError):
        return False
    if exc.permanent:
        return True
    status = exc.status
    return isinstance(status, int) and 400 <= status < 500 and status != 429


def normalize_phone_number(value: str, default_country_code: str = DEFAULT_COUNTRY_CODE) -> str:
    """
    Coerce a phone number into E.164.

    Accepts what a person (or a model repeating a person) actually writes:
    "(801) 647-7824", "801-647-7824", "18016477824", "+1 801 647 7824". A
    number that cannot be made unambiguously valid raises rather than being
    guessed at — sending a text to the wrong number is not recoverable.
    """
    raw = (value or "").strip()
    if not raw:
        raise SmsRecipientError("A phone number is required.")

    has_plus = raw.startswith("+")
    digits = re.sub(r"\D", "", raw)
    if not digits:
        raise SmsRecipientError(f"'{value}' contains no digits.")

    if has_plus:
        candidate = f"+{digits}"
    elif len(digits) == 10:
        # Bare national number, e.g. 8016477824.
        candidate = f"{default_country_code}{digits}"
    elif len(digits) == 11 and digits.startswith("1"):
        candidate = f"+{digits}"
    else:
        raise SmsRecipientError(
            f"'{value}' is not a phone number I can send to. Write it in "
            "international format, like +18015551234."
        )

    if not _E164.match(candidate):
        raise SmsRecipientError(
            f"'{value}' does not resolve to a valid number (got '{candidate}')."
        )
    return candidate


def user_phone_number() -> str:
    """
    The user's own number: where reports are texted and whose texts Nova answers.

    Still read from TWILIO_TARGET_NUMBER because report calls ring the same
    phone, and one number configured in two places would drift.
    """
    return (os.getenv("TWILIO_TARGET_NUMBER") or "").strip()


def _parse_number_list(raw: str, label: str) -> set[str]:
    numbers: set[str] = set()
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            numbers.add(normalize_phone_number(entry))
        except SmsRecipientError:
            print(f"Ignoring unparseable {label} entry '{entry}'.")
    return numbers


def _describe_response_error(response) -> str:
    """One-line reason from an Infobip error body, falling back to the status."""
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        exception = (body.get("requestError") or {}).get("serviceException") or {}
        text = exception.get("text")
        if text:
            code = exception.get("messageId")
            return f"[{code}] {text}" if code else str(text)
    return f"HTTP {response.status_code}"


class BipService:
    def __init__(self, http=None) -> None:
        self.base_url = (os.getenv("BIP_BASE_URL") or "").strip()
        self.api_key = (os.getenv("BIP_API_KEY") or "").strip()
        self.sender = (os.getenv("BIP_SENDER") or "").strip()
        # Anything with requests' post(); tests hand in a fake.
        self.http = http or requests

    # ---------- configuration ----------

    def is_configured(self) -> tuple[bool, str | None]:
        """Whether a text could be sent right now, and what's missing if not."""
        missing = [
            name
            for name, value in (
                ("BIP_BASE_URL", self.base_url),
                ("BIP_API_KEY", self.api_key),
                ("BIP_SENDER", self.sender),
            )
            if not value
        ]
        if missing:
            return False, f"Missing configuration: {', '.join(missing)}."
        return True, None

    def send_url(self) -> str:
        """The send endpoint. Infobip hands out a bare host, so a scheme is added."""
        base = self.base_url.rstrip("/")
        if not re.match(r"^https?://", base, re.IGNORECASE):
            base = f"https://{base}"
        return f"{base}{SEND_PATH}"

    # ---------- allowlists ----------

    @staticmethod
    def allowed_sms_recipients() -> set[str] | None:
        """
        Numbers Nova may text, or None when unrestricted.

        NOVA_SMS_ALLOWED_RECIPIENTS is a comma-separated allowlist. Leaving it
        unset permits any destination, which is the right default for a tool
        the user explicitly asks to text someone with — the guardrail there is
        the tool description telling Nova to confirm first. Setting it turns
        that into a hard limit that no prompt can talk its way around, which is
        what you want if Nova is ever driven by input you don't fully control.
        """
        raw = (os.getenv("NOVA_SMS_ALLOWED_RECIPIENTS") or "").strip()
        if not raw:
            return None
        return _parse_number_list(raw, "NOVA_SMS_ALLOWED_RECIPIENTS") or None

    @staticmethod
    def allowed_sms_senders() -> set[str]:
        """
        Numbers whose inbound texts may drive the agent.

        Defaults to the user's own number. This is a real security boundary,
        not a convenience: the sender number is shared with admin-api, so its
        users' replies arrive here too, and every one of them would otherwise
        start an agent loop holding run_terminal_command and run_sql.
        """
        raw = (os.getenv("NOVA_SMS_ALLOWED_SENDERS") or "").strip() or user_phone_number()
        return _parse_number_list(raw, "allowed SMS sender")

    # ---------- inbound ----------

    @staticmethod
    def verify_inbound_secret(authorization: str | None, token: str | None) -> bool:
        """
        Whether an inbound forward carries BIP_INBOUND_SECRET.

        Accepted either as the password of HTTP Basic auth (any username) or as
        a `?token=` on the forward URL, whichever the Infobip portal was set up
        with. Fails closed: with no secret configured nothing is accepted,
        because an open endpoint here is an open agent loop.
        """
        secret = (os.getenv("BIP_INBOUND_SECRET") or "").strip()
        if not secret:
            return False

        candidates: list[str] = []
        if token:
            candidates.append(token)

        scheme, _, credentials = (authorization or "").partition(" ")
        if scheme.lower() == "basic" and credentials:
            try:
                decoded = b64decode(credentials.strip(), validate=True).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                decoded = ""
            _, separator, password = decoded.partition(":")
            if separator:
                candidates.append(password)

        expected = secret.encode("utf-8")
        return any(
            hmac.compare_digest(candidate.encode("utf-8"), expected)
            for candidate in candidates
        )

    # ---------- sending ----------

    @staticmethod
    def split_sms_body(body: str) -> list[str]:
        """
        Break a reply into individual messages.

        Splits on whitespace near the limit so words survive, and only numbers
        the parts when there is more than one — "(1/1)" on a single text reads
        like a bug.
        """
        text = (body or "").strip()
        if not text:
            raise ValueError("An SMS body is required.")
        if len(text) <= SMS_MAX_BODY_CHARS:
            return [text]

        parts: list[str] = []
        remaining = text
        while remaining:
            if len(remaining) <= SMS_SPLIT_CHARS:
                parts.append(remaining)
                break
            window = remaining[:SMS_SPLIT_CHARS]
            cut = window.rfind(" ")
            if cut < SMS_SPLIT_CHARS // 2:
                cut = SMS_SPLIT_CHARS  # one very long token; hard-split it
            parts.append(remaining[:cut].strip())
            remaining = remaining[cut:].strip()

        total = len(parts)
        return [f"({index}/{total}) {part}" for index, part in enumerate(parts, 1)]

    def _send_one(self, number: str, text: str) -> str:
        """Send one message to one number and return Infobip's message id."""
        payload = {
            "messages": [
                {
                    "sender": self.sender,
                    "destinations": [{"to": number}],
                    "content": {"text": text},
                }
            ]
        }
        try:
            response = self.http.post(
                self.send_url(),
                json=payload,
                headers={
                    "Authorization": f"App {self.api_key}",
                    "Accept": "application/json",
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise BipRequestError(f"Could not reach Infobip: {exc}") from exc

        if not 200 <= response.status_code < 300:
            raise BipRequestError(
                _describe_response_error(response), status=response.status_code
            )

        try:
            messages = response.json().get("messages") or []
        except (ValueError, AttributeError):
            messages = []
        if not messages:
            raise BipRequestError("Infobip accepted the request but returned no message.")

        message = messages[0]
        status = message.get("status") or {}
        if status.get("groupName") in _REJECTED_GROUPS:
            reason = status.get("description") or status.get("name") or status["groupName"]
            raise BipRequestError(f"Message rejected: {reason}", permanent=True)
        return str(message.get("messageId") or "")

    def send_sms(
        self,
        to: list[str] | str,
        body: str,
        allow_unlisted: bool = False,
    ) -> dict:
        """
        Text one or more people, returning what happened for each recipient.

        Every recipient is attempted independently: one bad number must not
        stop the rest, and the caller (usually the agent) gets a per-recipient
        result rather than a single boolean it would have to guess about. A
        body over the size limit is split into numbered parts rather than
        truncated.

        `allow_unlisted` is for internal callers that have already established
        the destination — the update dispatcher texting the user's own number,
        a reply to an allowlisted sender — and never for numbers chosen by the
        model.
        """
        configured, problem = self.is_configured()
        if not configured:
            raise BipConfigurationError(problem or "BIP messaging is not configured.")

        recipients = [to] if isinstance(to, str) else list(to or [])
        if not recipients:
            raise SmsRecipientError("At least one recipient is required.")
        if len(recipients) > SMS_MAX_RECIPIENTS:
            raise SmsRecipientError(
                f"Refusing to text {len(recipients)} recipients in one call; "
                f"the limit is {SMS_MAX_RECIPIENTS}."
            )

        parts = self.split_sms_body(body)
        allowlist = None if allow_unlisted else self.allowed_sms_recipients()

        results: list[dict] = []
        for raw_number in recipients:
            try:
                number = normalize_phone_number(str(raw_number))
            except SmsRecipientError as exc:
                results.append({"to": str(raw_number), "status": "invalid", "error": str(exc)})
                continue

            if allowlist is not None and number not in allowlist:
                results.append(
                    {
                        "to": number,
                        "status": "not_permitted",
                        "error": (
                            "This number is not in NOVA_SMS_ALLOWED_RECIPIENTS, so "
                            "Nova is not allowed to text it."
                        ),
                    }
                )
                continue

            message_ids: list[str] = []
            try:
                for part in parts:
                    message_ids.append(self._send_one(number, part))
                results.append(
                    {
                        "to": number,
                        "status": "sent",
                        "message_ids": message_ids,
                        "segments": len(parts),
                    }
                )
            except BipRequestError as exc:
                results.append(
                    {
                        "to": number,
                        "status": "failed",
                        "error": str(exc),
                        "permanent": is_permanent_bip_error(exc),
                        # A multi-part send that dies halfway has already
                        # delivered the earlier parts; say so rather than
                        # implying nothing arrived.
                        "message_ids": message_ids,
                    }
                )

        sent = sum(1 for entry in results if entry["status"] == "sent")
        return {
            "status": "sent" if sent == len(results) else ("partial" if sent else "failed"),
            "sent": sent,
            "total": len(results),
            "parts_per_recipient": len(parts),
            "results": results,
        }
