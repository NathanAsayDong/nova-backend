"""
Outbound voice calls, and the trust boundary around Twilio's webhooks.

Nova places a call to report an update, and Twilio calls back into this
backend to drive the conversation. Those callbacks are public HTTP endpoints
that start an agent loop with Nova's full tool surface behind them, so every
one of them is signature-checked here before it is allowed to do anything.
Text messaging goes through Infobip instead (bip_service): Twilio messaging
is disabled on the account.

Speech-to-text and text-to-speech are Twilio's job, not ours: the call runs
through ConversationRelay, which transcribes the caller and speaks our replies,
talking to the backend in plain text over a WebSocket. That is why nothing in
this module touches audio.
"""

import os
import re
from urllib.parse import urljoin, urlparse, urlunparse

from twilio.request_validator import RequestValidator
from twilio.rest import Client

# Where Twilio reaches this backend. In development this is the ngrok https
# URL; the WebSocket URL for ConversationRelay is derived from it.
PUBLIC_BASE_URL_ENV = "PUBLIC_BASE_URL"

CALL_ANSWER_PATH = "/calls/answer"
CALL_RELAY_PATH = "/calls/relay"
CALL_STATUS_PATH = "/calls/status"

# ConversationRelay defaults to ElevenLabs for TTS, so Nova keeps the same
# voice on the phone as in the browser by passing the existing voice id
# straight through. Deepgram handles transcription on Twilio's side.
DEFAULT_TTS_PROVIDER = "ElevenLabs"
DEFAULT_TRANSCRIPTION_PROVIDER = "Deepgram"

# ConversationRelay speaks through Twilio's OWN ElevenLabs integration, whose
# voice ids are a different namespace from your ElevenLabs account's. A voice
# id from your account is rejected with error 64112 ("voice not found"), and
# the caller hears Twilio's "an application error has occurred" — so this is
# deliberately its own setting and never falls back to ELEVEN_LABS_VOICE_ID,
# which belongs to TTSService and the browser path.
# Twilio's en-US default; browse the library at
# https://www.twilio.com/docs/voice/conversationrelay/voice-configuration
DEFAULT_CALL_VOICE_ID = "UgBBYS2sOqTuMpoF3BR0"
CALL_VOICE_ID_ENV = "NOVA_CALL_VOICE_ID"

# Twilio hangs up on an unanswered call after this many seconds. Kept short:
# an update is not worth 30 seconds of ringing, and an unanswered call is
# requeued rather than lost.
DEFAULT_RING_TIMEOUT_SECONDS = 25

# Hosts that only ever appear in copied-and-pasted setup instructions.
_PLACEHOLDER_HOST_MARKERS = ("your-id.", "example.com", "<", "YOUR_")

_DISABLED_VALUES = {"off", "false", "0", "no", "none", "disable", "disabled"}


class TwilioConfigurationError(RuntimeError):
    """Raised when a call is attempted without the configuration to place it."""


# Twilio's exception __str__ is a multi-line block with ANSI colour codes in
# it, which is unreadable in a log and worse in a database column.
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def describe_twilio_error(exc: Exception) -> str:
    """One-line, human-readable reason a Twilio request failed."""
    code = getattr(exc, "code", None)
    message = getattr(exc, "msg", None) or str(exc)
    message = " ".join(_ANSI.sub("", message).split())
    if code:
        return f"[{code}] {message} (https://www.twilio.com/docs/errors/{code})"
    return message


def is_permanent_twilio_error(exc: Exception) -> bool:
    """
    Whether retrying this request could ever succeed.

    Twilio answers a bad request with a 4xx and a stable error code — an
    unverified caller id, a number the account doesn't own, a malformed
    destination. None of that changes by waiting, so retrying just burns the
    attempt budget and delays the honest "this failed" in the badge. 429 is
    the exception: rate limiting is explicitly a "try later" answer, and a
    5xx is Twilio's own problem.
    """
    status = getattr(exc, "status", None)
    if not isinstance(status, int):
        return False
    return 400 <= status < 500 and status != 429


class TwilioService:
    def __init__(self) -> None:
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER")
        self.target_number = os.getenv("TWILIO_TARGET_NUMBER")

        self._client: Client | None = None
        self._validator: RequestValidator | None = None

    # ---------- configuration ----------

    @property
    def client(self) -> Client:
        """
        Lazily built so importing this module never requires Twilio credentials.

        The worker imports the delivery path on every tick whether or not any
        call is due, and the test suite imports it with no credentials at all.
        """
        if self._client is None:
            if not self.account_sid or not self.auth_token:
                raise TwilioConfigurationError(
                    "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set to place calls."
                )
            self._client = Client(self.account_sid, self.auth_token)
        return self._client

    @property
    def validator(self) -> RequestValidator:
        if self._validator is None:
            if not self.auth_token:
                raise TwilioConfigurationError(
                    "TWILIO_AUTH_TOKEN must be set to verify Twilio webhooks."
                )
            self._validator = RequestValidator(self.auth_token)
        return self._validator

    @staticmethod
    def call_voice_id() -> str:
        """
        The ConversationRelay voice Nova speaks with on the phone.

        Refuses a value copied from ELEVEN_LABS_VOICE_ID: that id addresses a
        voice in your own ElevenLabs account, which Twilio's integration
        cannot see. Silently accepting it produces a call that connects and
        then plays an error message, which is a miserable thing to debug.
        """
        configured = (os.getenv(CALL_VOICE_ID_ENV) or "").strip()
        if not configured:
            return DEFAULT_CALL_VOICE_ID

        personal = (os.getenv("ELEVEN_LABS_VOICE_ID") or "").strip()
        if personal and configured == personal:
            print(
                f"{CALL_VOICE_ID_ENV} is set to ELEVEN_LABS_VOICE_ID "
                f"('{configured}'), which is a voice in your own ElevenLabs "
                "account and is not available to Twilio. Falling back to "
                f"'{DEFAULT_CALL_VOICE_ID}'. Pick a ConversationRelay voice at "
                "https://www.twilio.com/docs/voice/conversationrelay/voice-configuration"
            )
            return DEFAULT_CALL_VOICE_ID
        return configured

    @staticmethod
    def public_base_url() -> str:
        base = (os.getenv(PUBLIC_BASE_URL_ENV) or "").strip().rstrip("/")
        if not base:
            raise TwilioConfigurationError(
                f"{PUBLIC_BASE_URL_ENV} is not set. Twilio has to reach this "
                "backend over the public internet to drive a call — set it to "
                "your ngrok https URL (or your deployed host)."
            )
        return base

    @classmethod
    def webhook_url(cls, path: str) -> str:
        return urljoin(cls.public_base_url() + "/", path.lstrip("/"))

    @classmethod
    def websocket_url(cls, path: str = CALL_RELAY_PATH) -> str:
        """
        The wss:// URL ConversationRelay connects back to.

        Derived from the same public base URL as the HTTP webhooks so there is
        one thing to configure; ConversationRelay requires wss, so an http base
        (a bare local tunnel) is upgraded rather than silently failing later.
        """
        parsed = urlparse(cls.public_base_url())
        scheme = "wss" if parsed.scheme in ("https", "wss") else "ws"
        return urlunparse((scheme, parsed.netloc, path, "", "", ""))

    def is_configured(self) -> tuple[bool, str | None]:
        """
        Whether a call could be placed right now, and what's missing if not.

        Checked before claiming an update for delivery so a misconfigured
        deployment doesn't burn delivery attempts on calls that can never go out.
        """
        missing = [
            name
            for name, value in (
                ("TWILIO_ACCOUNT_SID", self.account_sid),
                ("TWILIO_AUTH_TOKEN", self.auth_token),
                ("TWILIO_PHONE_NUMBER", self.from_number),
                ("TWILIO_TARGET_NUMBER", self.target_number),
                (PUBLIC_BASE_URL_ENV, os.getenv(PUBLIC_BASE_URL_ENV)),
            )
            if not (value or "").strip()
        ]
        if missing:
            return False, f"Missing configuration: {', '.join(missing)}."

        # A placeholder host passes every other check and fails in the worst
        # possible place: Twilio dials, the user answers, and then hears
        # silence because the TwiML fetch 404s. Catch it before the phone rings.
        base = (os.getenv(PUBLIC_BASE_URL_ENV) or "").strip()
        if any(marker in base for marker in _PLACEHOLDER_HOST_MARKERS):
            return False, (
                f"{PUBLIC_BASE_URL_ENV} is still the placeholder '{base}'. Set it "
                "to the https URL your tunnel is actually serving, or Twilio "
                "will connect the call and then fail to reach this backend."
            )
        return True, None

    # ---------- webhook verification ----------

    def verify_signature(self, url: str, params: dict, signature: str | None) -> bool:
        """
        Whether a request genuinely came from Twilio.

        The signature covers the full URL Twilio requested plus the POST body,
        so the URL passed here must be the externally visible one — behind
        ngrok the request's own host header is the tunnel host, which is what
        Twilio signed, but a proxy that rewrites it would need the public base
        URL substituted instead.
        """
        if not signature:
            return False
        try:
            return self.validator.validate(url, params, signature)
        except TwilioConfigurationError:
            raise
        except Exception as exc:
            print(f"Twilio signature validation errored (treating as invalid): {exc}")
            return False

    # ---------- outbound calls ----------

    def place_report_call(
        self,
        update_id: int,
        to: str | None = None,
        ring_timeout_seconds: int = DEFAULT_RING_TIMEOUT_SECONDS,
    ) -> str:
        """
        Call the user to report one update. Returns the Twilio call sid.

        The update id travels as a query parameter on the answer webhook rather
        than as call state, so the TwiML handler can look the update up when
        Twilio comes back — and so a retry of the same update is just another
        call to this method.

        Answering-machine detection is on: reporting an update to a voicemail
        greeting is worse than not reporting it, so the answer webhook checks
        AnsweredBy and hangs up on a machine, leaving the update to be retried.
        """
        configured, problem = self.is_configured()
        if not configured:
            raise TwilioConfigurationError(problem or "Twilio is not configured.")

        destination = (to or self.target_number or "").strip()
        if not destination:
            raise TwilioConfigurationError(
                "No destination number: set TWILIO_TARGET_NUMBER or pass `to`."
            )

        answer_url = f"{self.webhook_url(CALL_ANSWER_PATH)}?update_id={int(update_id)}"

        # AMD is right often enough to be worth having, but a false positive
        # hangs up on a live user mid-"hello". NOVA_CALL_MACHINE_DETECTION=off
        # turns it off for anyone who finds that trade the wrong way round.
        detection = (os.getenv("NOVA_CALL_MACHINE_DETECTION") or "Enable").strip()
        machine_detection = None if detection.lower() in _DISABLED_VALUES else detection
        optional: dict[str, object] = {}
        if machine_detection:
            optional["machine_detection"] = machine_detection

        call = self.client.calls.create(
            url=answer_url,
            method="POST",
            to=destination,
            from_=self.from_number,
            status_callback=self.webhook_url(CALL_STATUS_PATH),
            status_callback_method="POST",
            # Only these four are valid call *events*. no-answer/busy/failed are
            # CallStatus values, not events — asking for them makes Twilio warn
            # (error 21626) and drop them. "completed" fires for every terminal
            # outcome and carries the real CallStatus in the payload, which is
            # what /calls/status reads.
            status_callback_event=["completed"],
            timeout=int(ring_timeout_seconds),
            **optional,
        )
        return call.sid

    def end_call(self, call_sid: str) -> None:
        """Hang up a call already in progress. Best-effort."""
        try:
            self.client.calls(call_sid).update(status="completed")
        except Exception as exc:
            print(f"Failed to end call {call_sid}: {exc}")
