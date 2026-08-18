"""
Nova over text message.

One endpoint: Twilio POSTs here whenever the Twilio number receives an SMS,
and Nova answers as a normal agent turn.

The shape of this is dictated by one hard constraint: Twilio gives a messaging
webhook about 15 seconds to respond, while an agent turn is allowed 120 and
routinely takes longer than 15 when tools are involved. So the webhook does
not answer the text — it acknowledges Twilio immediately with empty TwiML and
hands the turn to a background task, which sends the reply back through the
REST API when it is ready. A text arriving a few seconds later is normal; a
webhook timing out means Twilio retries and the user gets answered twice.

Inbound texts are gated twice over: Twilio's request signature proves the
request came from Twilio, and a sender allowlist decides whose texts may drive
an agent loop at all. The second gate is the important one — anyone can text a
public number, and this loop holds run_terminal_command and run_sql.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from prompting.prompt_source_prompt import PromptSourceEnum
from src.harness.agent_loop import AgentLoop
from src.model.conversation import Conversation
from src.service.conversation_service import ConversationClosedError, ConversationService
from src.service.twilio_service import (
    SMS_INBOUND_PATH,
    SmsRecipientError,
    TwilioService,
    describe_twilio_error,
    normalize_phone_number,
)

router = APIRouter(prefix="/sms", tags=["sms"])

twilio_service = TwilioService()
conversation_service = ConversationService()

agent_loop = AgentLoop()
agent_loop.conversation_service = conversation_service

# How long an SMS thread stays "the same conversation". Past this, a new text
# starts a fresh conversation rather than resuming one from days ago whose
# context no longer matches what the user is asking about.
SMS_THREAD_IDLE_HOURS = 12

_EMPTY_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'

# Guards against one text turning into a runaway reply; the SMS steer already
# asks for brevity, this is the backstop.
_MAX_REPLY_CHARS = 1200

_RELATIVE_ROUTE = SMS_INBOUND_PATH.removeprefix(router.prefix) or "/inbound"


def _ack() -> Response:
    """
    Empty TwiML: "received, nothing to say synchronously".

    Every exit path returns this, including rejections. A messaging webhook
    that returns an error status makes Twilio retry and raise account alerts,
    and there is nothing useful to retry — the text has already arrived.
    """
    return Response(content=_EMPTY_TWIML, media_type="application/xml")


async def _verified_form(request: Request) -> dict:
    """Parse an inbound Twilio webhook body after checking its signature."""
    form = await request.form()
    params = {key: str(value) for key, value in form.items()}

    signed_url = twilio_service.webhook_url(request.url.path)
    if request.url.query:
        signed_url = f"{signed_url}?{request.url.query}"

    signature = request.headers.get("X-Twilio-Signature")
    if not twilio_service.verify_signature(signed_url, params, signature):
        raise HTTPException(status_code=403, detail="Invalid signature.")
    return params


def _is_stale(conversation: Conversation) -> bool:
    """Whether an SMS thread has been quiet long enough to start fresh."""
    last = conversation.last_message_timestamp_utc
    if last is None:
        return False
    if isinstance(last, str):
        try:
            last = datetime.fromisoformat(last)
        except ValueError:
            return False
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last > timedelta(hours=SMS_THREAD_IDLE_HOURS)


def resolve_sms_conversation(phone_number: str) -> UUID:
    """
    The conversation an incoming text belongs to.

    Continues the number's open thread when there is a recent one, so a reply
    of "yes, do that" still knows what "that" was, and starts a new one when
    the last exchange is old enough that resuming it would be confusing.
    """
    existing = conversation_service.conversation_dao.get_latest_open_for_sms(phone_number)
    if existing is not None and not _is_stale(existing):
        return existing.uuid

    conversation = conversation_service.conversation_dao.create_conversation(
        Conversation(sms_phone_number=phone_number)
    )
    return conversation.uuid


def _run_sms_turn(phone_number: str, text: str) -> None:
    """
    Answer one text. Runs off the webhook, on a worker thread.

    Nothing is awaiting this, so every outcome has to end in a text going back
    — a silent failure here looks exactly like Nova ignoring you.
    """
    reply: str
    try:
        conversation_id = resolve_sms_conversation(phone_number)
        parts: list[str] = []
        final_text: str | None = None

        for event in agent_loop.conversation_loop_events(
            text, conversation_id, prompt_source=PromptSourceEnum.SMS_PROMPT
        ):
            event_type = event.get("type")
            if event_type == "text":
                parts.append(event["text"])
            elif event_type == "text_final":
                final_text = event["text"]
            # tool_call / artifact / status_text are screen and voice concerns.
            # A pre-tool "on it" line is reassuring when spoken into silence;
            # as a separate text it is just a second buzz in your pocket.

        reply = (final_text if final_text is not None else " ".join(parts)).strip()
        if not reply:
            reply = "Sorry — I didn't have anything to say to that."
        if len(reply) > _MAX_REPLY_CHARS:
            reply = reply[:_MAX_REPLY_CHARS].rstrip() + "…"
    except ConversationClosedError:
        reply = "That conversation is closed — text me again and I'll start a new one."
    except Exception as exc:
        print(f"SMS turn for {phone_number} failed: {exc}")
        reply = "Sorry, something went wrong on my end. Try me again in a moment."

    try:
        # allow_unlisted: this is a reply to someone who already passed the
        # inbound sender allowlist, not a destination the model picked.
        twilio_service.send_sms(phone_number, reply, allow_unlisted=True)
    except Exception as exc:
        print(f"Could not send SMS reply to {phone_number}: {describe_twilio_error(exc)}")


@router.post(_RELATIVE_ROUTE)
async def inbound_sms(request: Request) -> Response:
    """
    An SMS arrived at the Twilio number.

    Acknowledges immediately and answers out of band — see the module docstring
    for why the reply cannot be returned from here.
    """
    params = await _verified_form(request)

    raw_from = params.get("From") or ""
    body = (params.get("Body") or "").strip()

    try:
        sender = normalize_phone_number(raw_from)
    except SmsRecipientError:
        print(f"Ignoring inbound SMS from unparseable number '{raw_from}'.")
        return _ack()

    allowed = twilio_service.allowed_sms_senders()
    if sender not in allowed:
        # Deliberately silent. Replying would confirm the number is live to
        # whoever is probing it, and would let a stranger burn your Twilio
        # balance by texting it repeatedly.
        print(f"Ignoring inbound SMS from non-allowlisted sender {sender}.")
        return _ack()

    if not body:
        # An MMS with no text, or an empty message. Nothing to answer.
        return _ack()

    print(f"Inbound SMS from {sender}: {body[:80]}")
    # Fire-and-forget: the webhook must return long before this finishes.
    asyncio.create_task(asyncio.to_thread(_run_sms_turn, sender, body))
    return _ack()
