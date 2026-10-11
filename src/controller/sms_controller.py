"""
Nova over text message.

One endpoint: Infobip forwards every text the BIP number receives here as JSON,
and Nova answers each one as a normal agent turn.

The webhook does not answer the text itself. An agent turn is allowed 120
seconds and routinely takes longer than a webhook should be held open when
tools are involved, and Infobip retries a forward that doesn't get a 200 — so
the webhook acknowledges immediately and hands the turn to a background task,
which sends the reply through the BIP API when it is ready. A text arriving a
few seconds later is normal; a forward timing out means Infobip retries and
the user gets answered twice.

Inbound texts are gated twice over. A shared secret (BIP_INBOUND_SECRET, as a
Basic-auth password, a ?token=, or the last path segment) proves the request came from the forward
configured in the Infobip portal — Infobip does not sign forwards, so without
it anyone who found this URL could post a "from" of their choosing. Then a
sender allowlist decides whose texts may drive an agent loop at all, which
matters doubly because the number is shared with admin-api and its users'
replies land here too. This loop holds run_terminal_command and run_sql.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from prompting.prompt_source_prompt import PromptSourceEnum
from src.harness.agent_loop import AgentLoop
from src.model.conversation import Conversation
from src.service.bip_service import (
    SMS_INBOUND_PATH,
    BipService,
    SmsRecipientError,
    normalize_phone_number,
)
from src.service.conversation_service import ConversationClosedError, ConversationService

router = APIRouter(prefix="/sms", tags=["sms"])

bip_service = BipService()
conversation_service = ConversationService()

agent_loop = AgentLoop()
agent_loop.conversation_service = conversation_service

# How long an SMS thread stays "the same conversation". Past this, a new text
# starts a fresh conversation rather than resuming one from days ago whose
# context no longer matches what the user is asking about.
SMS_THREAD_IDLE_HOURS = 12

# Guards against one text turning into a runaway reply; the SMS steer already
# asks for brevity, this is the backstop.
_MAX_REPLY_CHARS = 1200

_RELATIVE_ROUTE = SMS_INBOUND_PATH.removeprefix(router.prefix) or "/inbound"


def _authorize(request: Request, path_token: str | None = None) -> None:
    """Refuse a forward that doesn't carry the shared secret."""
    authorized = bip_service.verify_inbound_secret(
        request.headers.get("Authorization"),
        path_token or request.query_params.get("token"),
    )
    if not authorized:
        raise HTTPException(status_code=403, detail="Invalid credentials.")


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
        result = bip_service.send_sms(phone_number, reply, allow_unlisted=True)
        if result.get("status") != "sent":
            print(f"SMS reply to {phone_number} not sent: {result.get('results')}")
    except Exception as exc:
        print(f"Could not send SMS reply to {phone_number}: {exc}")


def _handle_inbound(message: dict) -> None:
    """Gate one forwarded text and, if it passes, start answering it."""
    raw_from = str(message.get("from") or "")
    body = str(message.get("text") or "").strip()

    try:
        sender = normalize_phone_number(raw_from)
    except SmsRecipientError:
        print(f"Ignoring inbound SMS from unparseable number '{raw_from}'.")
        return

    if sender not in bip_service.allowed_sms_senders():
        # Deliberately silent. Replying would confirm the number is live to
        # whoever is probing it, would let a stranger burn the account balance
        # by texting it repeatedly, and would answer admin-api's users with
        # Nova.
        print(f"Ignoring inbound SMS from non-allowlisted sender {sender}.")
        return

    if not body:
        # An MMS with no text, or an empty message. Nothing to answer.
        return

    print(f"Inbound SMS from {sender}: {body[:80]}")
    # Fire-and-forget: the webhook must return long before this finishes.
    asyncio.create_task(asyncio.to_thread(_run_sms_turn, sender, body))


async def _receive(request: Request, path_token: str | None = None) -> dict:
    """Authenticate a forward, then gate and start answering each text in it."""
    _authorize(request, path_token)

    try:
        payload = await request.json()
    except ValueError:
        print("Ignoring inbound SMS forward with a non-JSON body.")
        return {"status": "ignored"}

    results = payload.get("results") if isinstance(payload, dict) else None
    for message in results if isinstance(results, list) else []:
        if isinstance(message, dict):
            _handle_inbound(message)
    return {"status": "received"}


@router.post(_RELATIVE_ROUTE)
async def inbound_sms(request: Request) -> dict:
    """
    Infobip forwarded one or more texts the BIP number received.

    Acknowledges immediately and answers out of band — see the module docstring
    for why the reply cannot be returned from here. Every authenticated forward
    gets a 200, including ones with nothing to act on: a non-200 makes Infobip
    retry, and there is nothing useful to retry — the text has already arrived.
    """
    return await _receive(request)


@router.post(_RELATIVE_ROUTE + "/{token}")
async def inbound_sms_with_path_token(request: Request, token: str) -> dict:
    """
    The same forward with the secret as the last path segment.

    For when the portal's forward arrives without its ?token= — a path segment
    survives where a query string may not. uvicorn's access log records the
    path, secret included, as it does a query string.
    """
    return await _receive(request, path_token=token)
