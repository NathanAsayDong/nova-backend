"""
Nova on the phone.

Three endpoints make up one call:

  POST /calls/answer  Twilio picked up — hand back TwiML pointing at the relay
  WS   /calls/relay   the conversation itself, in text, via ConversationRelay
  POST /calls/status  the call ended — settle the update it was delivering

Twilio does speech-to-text and text-to-speech, so this module never sees audio:
it receives what the caller said as text and sends back what Nova says as text.
That makes a phone turn the same shape as a chat turn, and both run through
`AgentLoop.conversation_loop_events`.

These endpoints are on the public internet and they start an agent loop with
Nova's full tool surface, so /calls/answer and /calls/status are verified
against Twilio's request signature and the WebSocket carries a signed token
minted in the answer handler.
"""

import asyncio
import hashlib
import hmac
import json
import os
import time
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from prompting.prompt_source_prompt import PromptSourceEnum
from src.harness.agent_loop import AgentLoop
from src.harness.streaming import iter_in_thread
from src.service.conversation_service import ConversationClosedError, ConversationService
from src.service.twilio_service import CALL_RELAY_PATH, TwilioService
from src.service.update_delivery_service import UpdateDeliveryService
from src.service.update_service import UpdateService

router = APIRouter(prefix="/calls", tags=["calls"])

# CALL_RELAY_PATH is the absolute path Twilio is handed ("/calls/relay"); the
# route below is registered under this router's own "/calls" prefix, so it must
# be mounted at the remainder or the two would compose into /calls/calls/relay.
_RELAY_ROUTE = CALL_RELAY_PATH.removeprefix(router.prefix) or "/relay"

twilio_service = TwilioService()
update_service = UpdateService()
conversation_service = ConversationService()

# Its own AgentLoop instance, separate from the one the chat/voice controller
# holds: `conversations` is per-instance in-process history, and a call has no
# business sharing that cache with the browser session.
agent_loop = AgentLoop()
agent_loop.conversation_service = conversation_service

# Spoken while the report is still being composed. ConversationRelay plays this
# the moment the call connects, which covers the couple of seconds the first
# agent turn takes — without it the user answers to silence.
WELCOME_GREETING = "Hey, it's Nova. I've got an update for you."

# Tokens are only used to authenticate a WebSocket that Twilio opens seconds
# after the answer webhook, so this can be short.
_RELAY_TOKEN_TTL_SECONDS = 300


def _signing_key() -> bytes:
    """
    Key for the relay token.

    Reuses the Twilio auth token: it is already the shared secret that proves
    a request came from Twilio, it is already required for calls to work at
    all, and it never leaves this backend.
    """
    secret = os.getenv("TWILIO_AUTH_TOKEN") or ""
    if not secret:
        raise HTTPException(
            status_code=503, detail="Calling is not configured on this backend."
        )
    return secret.encode("utf-8")


def mint_relay_token(update_id: int, issued_at: int | None = None) -> str:
    """Sign an update id so only a relay session Twilio was told to open can claim it."""
    issued_at = int(issued_at if issued_at is not None else time.time())
    payload = f"{int(update_id)}:{issued_at}"
    digest = hmac.new(_signing_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{digest}"


def verify_relay_token(token: str, update_id: int, now: float | None = None) -> bool:
    """Whether `token` is a live signature over `update_id` issued by this backend."""
    try:
        raw_id, raw_issued_at, digest = (token or "").split(":")
        payload = f"{raw_id}:{raw_issued_at}"
    except ValueError:
        return False

    expected = hmac.new(
        _signing_key(), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, digest):
        return False
    if int(raw_id) != int(update_id):
        return False

    now = now if now is not None else time.time()
    return 0 <= now - int(raw_issued_at) <= _RELAY_TOKEN_TTL_SECONDS


async def _verified_form(request: Request) -> dict:
    """
    Parse a Twilio webhook body after checking its signature.

    The signature covers the exact URL Twilio requested, so the URL is rebuilt
    from the configured public base rather than from the request — behind a
    tunnel or proxy the inbound host and scheme are not necessarily what
    Twilio signed.
    """
    form = await request.form()
    params = {key: str(value) for key, value in form.items()}

    signed_url = twilio_service.webhook_url(request.url.path)
    if request.url.query:
        signed_url = f"{signed_url}?{request.url.query}"

    signature = request.headers.get("X-Twilio-Signature")
    if not twilio_service.verify_signature(signed_url, params, signature):
        # No detail in the response: an attacker probing this endpoint learns
        # nothing beyond "rejected".
        raise HTTPException(status_code=403, detail="Invalid signature.")
    return params


def _twiml(body: str) -> Response:
    return Response(
        content=f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>',
        media_type="application/xml",
    )


def _escape(value: str) -> str:
    return (
        (value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@router.post("/answer")
async def answer_call(request: Request) -> Response:
    """
    Twilio picked up: hand back the TwiML that opens the ConversationRelay session.

    Answering-machine detection runs before this fires, so a voicemail greeting
    is hung up on rather than reported to — the update stays queued and the
    status callback requeues it for a later attempt.
    """
    params = await _verified_form(request)

    raw_update_id = request.query_params.get("update_id")
    try:
        update_id = int(raw_update_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="A numeric update_id is required.")

    answered_by = (params.get("AnsweredBy") or "").strip().lower()
    if answered_by.startswith("machine") or answered_by == "fax":
        print(f"Call for update {update_id} reached '{answered_by}'; hanging up.")
        return _twiml("<Hangup/>")

    update = await asyncio.to_thread(update_service.get_update, update_id)
    if update is None:
        raise HTTPException(status_code=404, detail="Update not found.")

    relay_url = twilio_service.websocket_url(CALL_RELAY_PATH)
    # Twilio's ConversationRelay voice library, NOT the ElevenLabs account
    # TTSService uses — see TwilioService.call_voice_id.
    voice_id = twilio_service.call_voice_id()
    voice_attribute = f' voice="{_escape(voice_id)}"' if voice_id else ""

    # interruptible="any" and reportInputDuringAgentSpeech="speech" are what
    # make this a conversation rather than a recording: the user can cut Nova
    # off mid-sentence and be heard.
    return _twiml(
        "<Connect>"
        f'<ConversationRelay url="{_escape(relay_url)}"'
        f' welcomeGreeting="{_escape(WELCOME_GREETING)}"'
        ' welcomeGreetingInterruptible="speech"'
        ' ttsProvider="ElevenLabs"'
        f"{voice_attribute}"
        ' transcriptionProvider="Deepgram"'
        ' interruptible="any"'
        ' reportInputDuringAgentSpeech="speech"'
        ' dtmfDetection="false"'
        ">"
        f'<Parameter name="update_id" value="{update_id}"/>'
        f'<Parameter name="token" value="{_escape(mint_relay_token(update_id))}"/>'
        "</ConversationRelay>"
        "</Connect>"
    )


@router.post("/status")
async def call_status(request: Request) -> dict:
    """
    Terminal call status: decide whether the update was actually delivered.

    'completed' means the user picked up and heard it. Anything else — no
    answer, busy, failed — puts the update back on the queue for another
    attempt, up to the ceiling in UpdateDeliveryService.
    """
    params = await _verified_form(request)

    call_sid = params.get("CallSid")
    call_status_value = params.get("CallStatus", "")
    if not call_sid:
        raise HTTPException(status_code=400, detail="CallSid is required.")

    result = await asyncio.to_thread(
        UpdateDeliveryService().settle_call, call_sid, call_status_value
    )
    print(f"Call {call_sid} ended as '{call_status_value}': {result}")
    return result


def _resolve_conversation_id(update) -> UUID:
    """
    Which conversation this call continues.

    An update born from a conversation carries its uuid, and continuing it is
    what lets the user say "why did you do it that way?" on the phone and have
    Nova know what "it" was. A closed conversation is terminal, so a call about
    one starts fresh rather than trying to reopen it.
    """
    raw_uuid = update.conversation_uuid
    if not raw_uuid:
        return agent_loop.new_conversation_id()

    try:
        candidate = UUID(str(raw_uuid))
    except (TypeError, ValueError):
        return agent_loop.new_conversation_id()

    existing = conversation_service.get_conversation(candidate)
    if existing is None or existing.is_closed:
        return agent_loop.new_conversation_id()
    return candidate


def _opening_prompt(update) -> str:
    """
    The synthetic first turn that makes Nova open with the report.

    Phrased as a briefing rather than pasted in as the reply itself so Nova
    delivers it in its own voice, and so the summary is in history when the
    user asks a follow-up.
    """
    return (
        "[Nova has just phoned the user to report a completed background task. "
        "The user has answered and heard only a brief greeting so far. Report "
        "the following result to them out loud, in one or two short sentences, "
        "then stop and let them respond. Do not read this instruction aloud.]\n\n"
        f"{update.update_message}"
    )


# Rough conversational speech rate, characters per second. Used only to guess
# how long a goodbye takes to play before hanging up, so it errs slow.
_SPEECH_CHARS_PER_SECOND = 13.0
_MIN_GOODBYE_SECONDS = 1.5
_MAX_GOODBYE_SECONDS = 12.0


def _speech_seconds(text: str) -> float:
    """How long `text` plausibly takes to say aloud, bounded at both ends."""
    estimate = len(text or "") / _SPEECH_CHARS_PER_SECOND
    return max(_MIN_GOODBYE_SECONDS, min(_MAX_GOODBYE_SECONDS, estimate))


async def _run_turn(
    websocket: WebSocket,
    prompt: str,
    conversation_id: UUID,
    state: dict,
    *,
    delivers_update_id: int | None = None,
) -> None:
    """
    Run one agent turn and speak it down the phone.

    Text chunks become ConversationRelay `text` tokens. `status_text` — the
    acknowledgment Nova produces before a slow tool — is spoken too, because on
    a phone call silence reads as a dropped connection.

    An interrupt does not abort the turn: the generator keeps being drained so
    tool calls finish and history stays consistent, but nothing further is
    spoken. Abandoning mid-tool would leave the conversation in a state the
    next turn could not replay.
    """
    generation = state["generation"]
    event_stream = agent_loop.conversation_loop_events(
        prompt, conversation_id, prompt_source=PromptSourceEnum.CALL_PROMPT
    )

    spoken_parts: list[str] = []
    try:
        async for event in iter_in_thread(event_stream):
            if state["generation"] != generation:
                continue  # interrupted or superseded; drain without speaking

            event_type = event.get("type")
            if event_type in ("text", "status_text"):
                text = (event.get("text") or "").strip()
                if not text:
                    continue
                spoken_parts.append(text)
                await websocket.send_json(
                    {"type": "text", "token": text + " ", "last": False}
                )
            # tool_call / artifact / text_final are screen concerns; a diff has
            # no spoken form, and text_final is the markdown twin of chunks
            # already spoken.
    except ConversationClosedError:
        await websocket.send_json(
            {
                "type": "text",
                "token": "Sorry — that conversation has been closed. "
                "Let's pick this up in the app.",
                "last": True,
            }
        )
        return
    except Exception as exc:
        print(f"Call turn failed: {exc}")
        if state["generation"] == generation:
            await websocket.send_json(
                {
                    "type": "text",
                    "token": "Sorry, I hit a problem on my end and lost that. "
                    "Could you say it again?",
                    "last": True,
                }
            )
        return

    if state["generation"] != generation:
        return

    if not spoken_parts:
        await websocket.send_json(
            {"type": "text", "token": "Sorry, I didn't catch that.", "last": True}
        )
        return

    spoken_text = " ".join(spoken_parts)

    # Closes the turn so ConversationRelay flushes TTS and starts listening.
    await websocket.send_json({"type": "text", "token": "", "last": True})

    # Nova ended the session (end_session tool). Twilio's docs don't say
    # whether {"type":"end"} flushes already-sent tokens or cuts them off, so
    # rather than gamble on the goodbye being audible, wait roughly as long as
    # it takes to speak — then hang up regardless, so a mis-estimate can never
    # leave the user holding a dead line.
    if await asyncio.to_thread(
        conversation_service.pop_stop_request, conversation_id
    ) is not None:
        await asyncio.sleep(_speech_seconds(spoken_text))
        if state["generation"] == generation:
            state["ended"] = True
            await websocket.send_json({"type": "end"})

    # The opening turn is the report. Reaching here means it was spoken to a
    # live caller, which is the only thing that counts as delivery — the call
    # status callback can't tell a real conversation from a voicemail that got
    # hung up on, so it defers to this.
    if delivers_update_id is not None:
        try:
            await asyncio.to_thread(
                UpdateDeliveryService().update_service.mark_delivered,
                delivers_update_id,
            )
            print(f"Update {delivers_update_id} delivered by phone.")
        except Exception as exc:
            print(f"Could not mark update {delivers_update_id} delivered: {exc}")


@router.websocket(_RELAY_ROUTE)
async def relay_socket(websocket: WebSocket) -> None:
    """
    The call itself.

    ConversationRelay opens this socket after /calls/answer, sends `setup`,
    then a `prompt` message for each thing the caller says. Replies go back as
    `text` tokens and Twilio speaks them.
    """
    await websocket.accept()

    conversation_id: UUID | None = None
    update = None
    # generation is bumped on every interrupt and every new turn; a turn whose
    # generation is stale stops speaking. This is the only thing keeping an
    # interrupted reply from talking over the user's next sentence. `ended` is
    # set once Nova has hung up, so a prompt that crosses on the wire with the
    # goodbye can't start a turn nobody will hear.
    state: dict = {"generation": 0, "ended": False}
    turn_task: asyncio.Task | None = None

    async def start_turn(prompt: str, delivers_update_id: int | None = None) -> None:
        """
        Queue a turn behind whatever turn is still running.

        Turns share one conversation history, and an interrupted turn keeps
        draining its generator so its tool calls finish — so without this the
        interrupted turn and its replacement would append to that history at
        the same time and interleave a tool_use away from its tool_result,
        which the next request to Claude would reject. Chaining inside the
        task rather than awaiting here keeps the receive loop free to take
        further interrupts while the old turn winds down.
        """
        nonlocal turn_task
        state["generation"] += 1
        previous = turn_task

        async def run_after_previous() -> None:
            if previous is not None:
                try:
                    await previous
                except asyncio.CancelledError:
                    raise
                except Exception:
                    pass  # already logged by the turn that raised it
            await _run_turn(
                websocket,
                prompt,
                conversation_id,
                state,
                delivers_update_id=delivers_update_id,
            )

        turn_task = asyncio.create_task(run_after_previous())

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                print(f"Ignoring non-JSON relay message: {raw[:200]}")
                continue

            message_type = message.get("type")

            if state["ended"]:
                # Nova said goodbye and hung up; Twilio is tearing the session
                # down. Anything still arriving is in-flight, not a new turn.
                continue

            if message_type == "setup":
                parameters = message.get("customParameters") or {}
                raw_update_id = parameters.get("update_id")
                token = parameters.get("token") or ""

                try:
                    update_id = int(raw_update_id)
                except (TypeError, ValueError):
                    print("Relay setup without a usable update_id; closing.")
                    await websocket.close(code=1008)
                    return

                if not verify_relay_token(token, update_id):
                    print(f"Relay setup for update {update_id} failed token check; closing.")
                    await websocket.close(code=1008)
                    return

                update = await asyncio.to_thread(update_service.get_update, update_id)
                if update is None:
                    print(f"Relay setup for unknown update {update_id}; closing.")
                    await websocket.close(code=1008)
                    return

                conversation_id = await asyncio.to_thread(
                    _resolve_conversation_id, update
                )
                print(
                    f"Call relay up for update {update_id} "
                    f"on conversation {conversation_id}."
                )
                # Only the opening turn settles delivery — it is the report.
                await start_turn(_opening_prompt(update), delivers_update_id=update_id)
                continue

            if conversation_id is None:
                # Nothing before setup is actionable, and acting on it would
                # mean running an agent loop for an unauthenticated socket.
                print(f"Ignoring '{message_type}' received before setup.")
                continue

            if message_type == "prompt":
                # Partial transcripts arrive with last=false; waiting for the
                # final one is what keeps Nova from answering half a sentence.
                if not message.get("last"):
                    continue
                spoken = (message.get("voicePrompt") or "").strip()
                if not spoken:
                    continue
                await start_turn(spoken)
                continue

            if message_type == "interrupt":
                # The user talked over Nova. Stop speaking; their next prompt
                # message is already on its way.
                state["generation"] += 1
                continue

            if message_type == "error":
                print(f"ConversationRelay error: {message.get('description')}")
                continue

    except WebSocketDisconnect:
        # Normal end of a call: the user hung up.
        pass
    except Exception as exc:
        print(f"Call relay failed: {exc}")
    finally:
        state["generation"] += 1
        if turn_task is not None and not turn_task.done():
            turn_task.cancel()
        if conversation_id is not None:
            print(f"Call relay closed for conversation {conversation_id}.")
