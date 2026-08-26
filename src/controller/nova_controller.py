import asyncio
import base64
import json
import os
import re
import tempfile
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Body, HTTPException
from fastapi.responses import StreamingResponse

from prompting.prompt_source_prompt import PromptSourceEnum
from src.harness.agent_loop import AgentLoop
from src.harness.streaming import iter_in_thread
from src.controller.audio_ws import (
    asr_service,
    suffix_for_mime,
    transcribe_serialized,
)
from src.service.conversation_service import ConversationClosedError, ConversationService
from src.service.endpointing_service import DEFAULT_SILENCE_MS, endpoint_decision
from src.service.meeting_service import MeetingService
from src.service.tts_service import TTSService

router = APIRouter(tags=["transcribe"])
tts_service = TTSService()
conversation_service = ConversationService()
meeting_service = MeetingService()
agent_loop = AgentLoop()
agent_loop.conversation_service = conversation_service


# In-memory power state for the assistant. Single-user personal deployment,
# so a module-level flag is sufficient — no need for per-session storage.
_nova_power_state = {"enabled": True}

# Live captions re-transcribe the whole buffer each pass, so wait for enough
# audio to be worth decoding (~0.9s at the client's 450ms chunk cadence) and
# require that much NEW audio before running again.
_PARTIAL_MIN_CHUNKS = 2
_PARTIAL_NEW_CHUNKS = 2
# Webm chunks only decode from the start, so every caption pass re-transcribes
# the whole buffer — cost grows with the utterance while the interval stays
# fixed, which is quadratic work on the one GPU the final transcription also
# needs. Stretch the interval as the buffer grows: roughly one pass per sixth
# of the audio so far, so a long utterance captions less often instead of
# starving the turn it belongs to.
_PARTIAL_BACKOFF_DIVISOR = 6


def _partial_is_due(total_chunks: int, chunks_done: int) -> bool:
    """Whether enough new audio has arrived to justify another caption pass."""
    if total_chunks < _PARTIAL_MIN_CHUNKS:
        return False
    required = max(_PARTIAL_NEW_CHUNKS, total_chunks // _PARTIAL_BACKOFF_DIVISOR)
    return total_chunks - chunks_done >= required


def _speculative_asr_enabled() -> bool:
    """
    Whether to transcribe the turn during the endpointing wait.

    On by default. The trade is a rare clipped trailing word (audio that
    arrived after the client called the pause but before it called the stop)
    against removing a full transcription pass from the critical path of every
    turn. Set NOVA_SPECULATIVE_ASR=0 to go back to transcribing on stop.
    """
    raw = os.getenv("NOVA_SPECULATIVE_ASR")
    if raw is None:
        return True
    return raw.strip().lower() not in {"false", "0", "no", "off"}


@router.get("/nova/power")
async def get_nova_power() -> dict[str, bool]:
    """Report whether Nova is currently allowed to listen."""
    return {"enabled": _nova_power_state["enabled"]}


@router.get("/nova/state")
async def get_nova_state() -> dict:
    """
    Power plus mode, in one call for the client's header.

    Mode is derived from whether a meeting is recording rather than held
    alongside the power flag: a meeting row is the only source of truth for
    it, so the two can never drift apart.
    """
    state = await asyncio.to_thread(meeting_service.get_state)
    return {"enabled": _nova_power_state["enabled"], **state}


@router.post("/nova/power")
async def set_nova_power(payload: dict = Body(...)) -> dict[str, bool]:
    """Turn Nova's listening on or off from the UI toggle."""
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        raise HTTPException(status_code=400, detail="'enabled' must be a boolean.")
    _nova_power_state["enabled"] = enabled
    return {"enabled": _nova_power_state["enabled"]}


def parse_conversation_id(value: str | None) -> UUID | None:
    if not value:
        return None
    return UUID(value)


def resolve_chat_request(payload: dict) -> tuple[str, UUID]:
    """
    Pull the message and conversation id out of a text-chat request body.

    Accepts either camelCase or snake_case for the conversation id, and mints a
    new one when the client hasn't started a conversation yet.
    """
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="A non-empty 'message' is required.")

    raw_conversation_id = payload.get("conversationId") or payload.get("conversation_id")
    try:
        conversation_id = parse_conversation_id(raw_conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversationId.")

    return message, conversation_id or agent_loop.new_conversation_id()


def sse_event(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload)}\n\n"

@router.post("/chat/stream")
async def chat_stream(payload: dict = Body(...)) -> StreamingResponse:
    """Text chat turn, emitting sentence chunks as server-sent events."""
    message, conversation_id = resolve_chat_request(payload)

    # Reject closed conversations with a real status code before the stream
    # opens; the agent loop re-checks as a backstop.
    existing = await asyncio.to_thread(conversation_service.get_conversation, conversation_id)
    if existing is not None and existing.is_closed:
        raise HTTPException(
            status_code=409,
            detail="This conversation is closed. Start a new conversation to continue.",
        )

    async def event_source():
        yield sse_event({"type": "start", "conversationId": str(conversation_id)})

        event_stream = agent_loop.conversation_loop_events(
            message, conversation_id, prompt_source=PromptSourceEnum.CHAT_PROMPT
        )
        parts: list[str] = []
        final_text: str | None = None
        try:
            async for event in iter_in_thread(event_stream):
                event_type = event.get("type")
                if event_type == "text":
                    parts.append(event["text"])
                    # Assistant prose is markdown: the model writes it that way,
                    # and the client renders it as such.
                    yield sse_event(
                        {
                            "type": "delta",
                            "text": event["text"],
                            "format": "markdown",
                            "seq": len(parts),
                        }
                    )
                elif event_type == "text_final":
                    # Whitespace-exact version of what was just streamed, so
                    # markdown lists and fences survive sentence chunking.
                    final_text = event["text"]
                    yield sse_event(
                        {"type": "text_final", "text": final_text, "format": "markdown"}
                    )
                else:
                    # status_text / tool_call / artifact pass through untouched;
                    # the client renders the acknowledgment as a status bubble.
                    yield sse_event(event)
        except ConversationClosedError:
            yield sse_event(
                {
                    "type": "error",
                    "code": "conversation_closed",
                    "message": "This conversation is closed. Start a new conversation to continue.",
                }
            )
            return
        except Exception as exc:
            yield sse_event({"type": "error", "message": f"Chat pipeline failed: {str(exc)}"})
            return

        # switch_project closes the conversation mid-turn and continues under
        # a successor — point the client at the new conversation.
        switched_to = conversation_service.pop_switch_target(conversation_id)
        final_conversation_id = switched_to or conversation_id
        if switched_to is not None:
            agent_loop.conversations.pop(conversation_id, None)
            yield sse_event(
                {
                    "type": "conversation_switched",
                    "previousConversationId": str(conversation_id),
                    "conversationId": str(switched_to),
                }
            )

        # Typed chat has no listening loop to stop, but the flag must still be
        # cleared here: left set, it would fire on the next spoken turn of this
        # conversation and cut the user off mid-sentence.
        stop_reason = conversation_service.pop_stop_request(conversation_id)
        if stop_reason is not None:
            yield sse_event({"type": "session_ended", "reason": stop_reason})

        yield sse_event(
            {
                "type": "done",
                "conversationId": str(final_conversation_id),
                "assistantText": final_text if final_text is not None else " ".join(parts),
            }
        )

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )




def normalize_wake_text(value: str) -> str:
    lowered = value.lower()
    normalized = re.sub(r"[^a-z0-9\s]+", " ", lowered)
    return re.sub(r"\s+", " ", normalized).strip()


def has_wake_phrase(value: str) -> bool:
    normalized = normalize_wake_text(value)
    if not normalized:
        return False

    tokens = normalized.split(" ")
    if not tokens:
        return False

    wake_prefixes = {"hey", "hi", "hello", "ok", "okay", "yo"}

    if tokens[0] == "nova":
        return True

    if len(tokens) >= 2 and tokens[0] in wake_prefixes and tokens[1] == "nova":
        return True

    # Keep short "addressing" utterances forgiving, e.g., "yo nova please".
    return len(tokens) <= 3 and "nova" in tokens


def has_stop_phrase(value: str) -> bool:
    normalized = normalize_wake_text(value)
    if not normalized:
        return False

    tokens = normalized.split(" ")
    if not tokens:
        return False

    exact_stops = {
        "stop",
        "nova stop",
        "stop nova",
        "ok stop",
        "okay stop",
        "ok nova stop",
        "okay nova stop",
        "nova stop listening",
        "stop listening",
        "thank you",
        "thank you nova",
        "thank you nova stop",
        "thank you nova stop listening",
        "thank you nova stop listening",
        "thanks",
        "thanks nova",
        "thanks nova stop",
        "thanks nova stop listening",
        "thanks nova stop listening",
    }
    if normalized in exact_stops:
        return True

    collapsed = normalized.replace(" ", "")
    if collapsed in {
        "thatsall",
        "thatsallfornow",
        "okaythatsall",
        "okaythatsallfornow",
        "okthatsall",
        "okthatsallfornow",
        "okaythatsallfornow",
        "okthatsallfornow",
        "okaythatsallfornow",
        "thanks",
        "thanksnova",
        "thanksnovastop",
        "thanksnovastoplistening",
        "thanksnovastoplistening",
    }:
        return True

    return (
        "that s all for now" in normalized
        or "thats all for now" in normalized
        or "that s all" in normalized
        or "thats all" in normalized
    )


async def send_assistant_text(
    websocket: WebSocket,
    text: str,
    *,
    seq: int,
    conversation_id: UUID,
    markdown_display: str | None = None,
) -> None:
    event: dict[str, object] = {
        "type": "assistant_text",
        "text": text,
        "seq": seq,
        "conversationId": str(conversation_id),
    }
    if markdown_display is not None:
        event["markdownDisplay"] = markdown_display
    await websocket.send_json(event)


async def stream_tts_audio(
    websocket: WebSocket,
    text: str,
    *,
    role: str,
    iteration: int | None = None,
) -> bool:
    """
    Speak `text` to the client as a chunked audio stream.

    Returns True when the full clip was streamed, False when TTS failed.
    TTS failures are contained here rather than raised: the stream-start
    event has already been sent by the time the provider errors, so the
    client must always receive the matching stream-end (or it waits forever
    on a stream that will never arrive) plus an error message saying why
    there is no audio. Websocket send failures still propagate — a dead
    socket ends the turn either way.
    """
    stream_id = str(uuid.uuid4())
    response_mime = tts_service.output_mime_type()

    start_event: dict[str, object] = {
        "type": "assistant_audio_stream_start",
        "streamId": stream_id,
        "mimeType": response_mime,
        "role": role,
    }
    if iteration is not None:
        start_event["iteration"] = iteration

    await websocket.send_json(start_event)

    sequence = 0
    tts_error: str | None = None
    audio_chunks = tts_service.stream_text_to_speech(text)
    while True:
        try:
            audio_chunk = next(audio_chunks)
        except StopIteration:
            break
        except Exception as exc:
            tts_error = str(exc)
            break

        sequence += 1
        chunk_b64 = base64.b64encode(audio_chunk).decode("ascii")
        await websocket.send_json(
            {
                "type": "assistant_audio_stream_chunk",
                "streamId": stream_id,
                "chunkBase64": chunk_b64,
                "seq": sequence,
            }
        )

    if tts_error is not None:
        print(f"TTS stream {stream_id} failed after {sequence} chunks: {tts_error}")
        preview = tts_error if len(tts_error) <= 300 else tts_error[:300] + "…"
        await websocket.send_json(
            {
                "type": "error",
                "message": f"Voice playback failed — continuing without audio. ({preview})",
            }
        )

    await websocket.send_json(
        {
            "type": "assistant_audio_stream_end",
            "streamId": stream_id,
        }
    )
    return tts_error is None


@router.websocket("/ws/transcribe")
async def transcribe_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json(
        {
            "type": "ready",
            "message": "Connected. Send start, stream chunks, then stop.",
        }
    )

    recording_started = False
    language: str | None = None
    mime_type = "audio/webm"
    chunks: list[bytes] = []
    conversation_id: UUID | None = None
    capture_purpose = "turn"

    # Live-caption state. `generation` invalidates in-flight partials when a
    # recording stops or restarts; `chunks_done` is how much audio the last
    # completed partial covered; `seq` orders the captions client-side.
    # `text` is the newest caption, which is what the endpointing scorer reads.
    partial_task: asyncio.Task | None = None
    partial_state = {"generation": 0, "chunks_done": 0, "seq": 0, "text": ""}

    # Speculative transcription state. The client announces the pause that
    # starts its endpointing countdown, and the turn is transcribed during
    # that window rather than after it — the audio recorded from the pause
    # onward is silence by the client's own reckoning, and if it turns out not
    # to be, `speech_resume` invalidates the result. `token` rises whenever the
    # buffer's meaning changes (new recording, speech resumed, turn consumed),
    # so a result computed against an older buffer can never be used.
    #
    # `pause_pending` is the deferral between the pause announcement and the
    # snapshot. The recorder flushes on a cadence, so when `speech_pause`
    # arrives, the audio holding the user's LAST WORDS is usually still in the
    # recorder's buffer client-side — snapshotting now would transcribe a turn
    # with its tail cut off. The client flushes on pause, so speculation waits
    # for the next chunk (which covers audio through the pause) and starts
    # then.
    speculative_task: asyncio.Task | None = None
    speculative_state: dict = {"token": 0, "valid_for": -1, "text": None}
    pause_pending = False

    def invalidate_speculative() -> None:
        speculative_state["token"] += 1
        speculative_state["valid_for"] = -1
        speculative_state["text"] = None

    async def run_speculative_transcription(
        audio_bytes: bytes, token: int
    ) -> None:
        """
        Transcribe the turn while the client waits out its silence window.

        Best-effort in exactly the way the caption pass is: a failure here just
        means `stop` falls back to transcribing the buffer itself.

        On success this also emits a final caption with a fresh endpoint
        window. Every earlier caption was stale by construction — it lagged
        the audio it described — but this one covers the WHOLE utterance, so
        its verdict is the authoritative one: a client waiting out a long
        "trailing off" window hears "actually, that sentence resolved" and can
        stop waiting immediately.
        """
        file_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix_for_mime(mime_type)
            ) as temp:
                temp.write(audio_bytes)
                file_path = Path(temp.name)

            text = await asyncio.to_thread(transcribe_serialized, file_path, language)
            if token != speculative_state["token"]:
                return  # speech resumed, or the turn was already consumed
            text = (text or "").strip()
            speculative_state["text"] = text
            speculative_state["valid_for"] = token

            if text:
                partial_state["text"] = text
                decision = endpoint_decision(text)
                partial_state["seq"] += 1
                await websocket.send_json(
                    {
                        "type": "partial_transcript",
                        "text": text,
                        "seq": partial_state["seq"],
                        "endpointMs": decision.silence_ms,
                        "endpointReason": decision.reason,
                    }
                )
        except Exception as exc:
            print(f"Speculative transcription failed (ignored): {exc}")
        finally:
            if file_path and file_path.exists():
                os.remove(file_path)

    async def emit_partial_transcript(
        audio_bytes: bytes, chunk_count: int, generation: int
    ) -> None:
        """
        Best-effort live caption for the recording in progress.

        Re-transcribes the accumulated buffer (webm chunks only decode from
        the start) and emits the whole partial text; the client replaces its
        draft rather than appending. Failures are logged and swallowed — the
        final transcription on stop is the one that matters.

        Carries `endpointMs`: how long the client should wait out silence
        before calling the turn over, given what has been said so far. The
        caption pass is where the transcript already exists, so the semantic
        half of turn detection rides along on it for free.
        """
        file_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix_for_mime(mime_type)
            ) as temp:
                temp.write(audio_bytes)
                file_path = Path(temp.name)

            text = await asyncio.to_thread(transcribe_serialized, file_path, language)
            text = (text or "").strip()

            if generation != partial_state["generation"]:
                return  # recording stopped or restarted while transcribing
            partial_state["chunks_done"] = chunk_count
            if text:
                partial_state["text"] = text
                decision = endpoint_decision(text)
                partial_state["seq"] += 1
                await websocket.send_json(
                    {
                        "type": "partial_transcript",
                        "text": text,
                        "seq": partial_state["seq"],
                        "endpointMs": decision.silence_ms,
                        "endpointReason": decision.reason,
                    }
                )
        except Exception as exc:
            print(f"Partial transcription failed (ignored): {exc}")
        finally:
            if file_path and file_path.exists():
                os.remove(file_path)

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            chunk = message.get("bytes")
            text_data = message.get("text")

            if chunk is not None:
                if not recording_started:
                    continue

                chunks.append(chunk)
                await websocket.send_json(
                    {
                        "type": "chunk_received",
                        "count": len(chunks),
                        "bytes": len(chunk),
                    }
                )

                # A pause was announced and this is the first chunk since:
                # the flush that carries the audio up to the pause itself.
                # NOW the buffer covers the whole utterance — snapshot it and
                # start transcribing while the client waits out its window.
                if pause_pending and capture_purpose == "turn":
                    pause_pending = False
                    invalidate_speculative()
                    speculative_task = asyncio.create_task(
                        run_speculative_transcription(
                            b"".join(chunks), speculative_state["token"]
                        )
                    )
                    continue

                # Live caption: re-transcribe the buffer whenever enough new
                # audio arrived and no partial pass is already running. Only
                # for real turns — wake checks are too short to bother.
                #
                # Suspended while the client is counting out its silence
                # window: everything arriving then is silence, and a caption
                # pass started now would hold the GPU that the turn's own
                # transcription is about to need.
                if (
                    capture_purpose == "turn"
                    and speculative_task is None
                    and (partial_task is None or partial_task.done())
                    and _partial_is_due(len(chunks), partial_state["chunks_done"])
                ):
                    partial_task = asyncio.create_task(
                        emit_partial_transcript(
                            b"".join(chunks),
                            len(chunks),
                            partial_state["generation"],
                        )
                    )
                continue

            if text_data is None:
                continue

            try:
                payload = json.loads(text_data)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "message": "Invalid JSON control message."}
                )
                continue

            event = payload.get("event")

            if event == "start":
                if not _nova_power_state["enabled"]:
                    # Backstop: the UI toggle tears its own pipeline down, but
                    # never record while Nova is powered off.
                    await websocket.send_json(
                        {
                            "type": "follow_up_stopped",
                            "message": "Nova is powered off.",
                        }
                    )
                    continue
                # Backstop for meeting mode, mirroring the power check above.
                # While a meeting is recording, Nova transcribes the room and
                # answers nobody — without this, any voice in the meeting
                # would open a turn and get a spoken reply.
                if payload.get("purpose", "turn") == "turn":
                    active_meeting = await asyncio.to_thread(
                        meeting_service.get_active_meeting
                    )
                    if active_meeting is not None:
                        await websocket.send_json(
                            {
                                "type": "meeting_mode",
                                "meeting": active_meeting,
                                "message": (
                                    "Nova is in meeting mode and is not taking "
                                    "turns. Stop the meeting to talk to Nova."
                                ),
                            }
                        )
                        continue

                recording_started = True
                chunks.clear()
                language = payload.get("language")
                mime_type = payload.get("mimeType", "audio/webm")
                capture_purpose = payload.get("purpose", "turn")
                partial_state["generation"] += 1
                partial_state["chunks_done"] = 0
                partial_state["seq"] = 0
                partial_state["text"] = ""
                speculative_task = None
                pause_pending = False
                invalidate_speculative()
                raw_conversation_id = payload.get("conversationId")
                if raw_conversation_id:
                    try:
                        conversation_id = parse_conversation_id(raw_conversation_id)
                    except ValueError:
                        await websocket.send_json(
                            {"type": "error", "message": "Invalid conversationId."}
                        )
                        continue
                await websocket.send_json(
                    {
                        "type": "listening",
                        "message": "Streaming audio chunks to backend.",
                        # Starting silence window, until the first caption
                        # gives the scorer something to read. Sent rather than
                        # hardcoded client-side so the windows have one owner.
                        "endpointMs": DEFAULT_SILENCE_MS,
                    }
                )
                continue

            if event == "speech_pause":
                # The client's voice detector just went quiet and started its
                # endpointing countdown. Don't snapshot the buffer yet: the
                # chunk carrying the user's last words is still in flight (the
                # client flushes its recorder on pause). Mark the pause and
                # let that chunk's arrival start the transcription, so the
                # wait is spent doing the work — on a buffer that actually
                # ends where the speech did.
                if (
                    recording_started
                    and capture_purpose == "turn"
                    and speculative_task is None
                    and _speculative_asr_enabled()
                ):
                    pause_pending = True
                continue

            if event == "speech_resume":
                # A pause inside a sentence, not the end of one. Whatever the
                # speculative pass produced covers only part of the turn now.
                pause_pending = False
                speculative_task = None
                invalidate_speculative()
                continue

            if event == "abort":
                # The client opened a turn on what turned out to be a click or
                # a cough, not speech. Nothing to transcribe, nothing to say —
                # drop the buffer and stand by for a real turn.
                recording_started = False
                chunks.clear()
                partial_state["generation"] += 1
                partial_state["text"] = ""
                pause_pending = False
                speculative_task = None
                invalidate_speculative()
                continue

            if event == "wake_greeting":
                if not _nova_power_state["enabled"]:
                    await websocket.send_json(
                        {
                            "type": "follow_up_stopped",
                            "message": "Nova is powered off.",
                        }
                    )
                    continue
                try:
                    await stream_tts_audio(
                        websocket,
                        "Hello sir.",
                        role="wake",
                    )
                    await websocket.send_json(
                        {
                            "type": "wake_greeting_done",
                            "message": "Wake greeting complete.",
                        }
                    )
                except Exception as exc:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Wake greeting failed: {str(exc)}",
                        }
                    )
                continue

            if event == "stop":
                # Whatever partial is in flight is now stale; the final
                # transcription below supersedes it.
                partial_state["generation"] += 1
                # A pause whose flush chunk never arrived: no speculation
                # started, so the fallback below transcribes the full buffer.
                pause_pending = False

                # Collect the speculative pass started at the pause. It was
                # launched a silence-window ago, so this usually resolves
                # immediately — and when it does not, waiting on it still
                # beats starting the same work from scratch below.
                speculative_transcript: str | None = None
                if speculative_task is not None:
                    expected_token = speculative_state["token"]
                    try:
                        await speculative_task
                    except Exception as exc:
                        print(f"Speculative transcription failed (ignored): {exc}")
                    if speculative_state["valid_for"] == expected_token:
                        speculative_transcript = speculative_state["text"]
                    speculative_task = None
                invalidate_speculative()

                purpose = payload.get("purpose", "turn")
                if not chunks:
                    if purpose == "wake_check":
                        await websocket.send_json(
                            {
                                "type": "wake_not_detected",
                                "message": "Wake phrase not detected.",
                            }
                        )
                    else:
                        await websocket.send_json(
                            {"type": "error", "message": "No audio chunks received."}
                        )
                    recording_started = False
                    continue

                file_path: Path | None = None
                try:
                    if speculative_transcript:
                        # Already transcribed during the endpointing wait, and
                        # over byte-identical audio minus the trailing silence.
                        transcript = speculative_transcript
                        print(f"[turn] transcript ready at stop (speculative): {transcript!r}")
                    else:
                        suffix = suffix_for_mime(mime_type)
                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix=suffix
                        ) as temp:
                            for audio_chunk in chunks:
                                temp.write(audio_chunk)
                            file_path = Path(temp.name)

                        # Off the event loop, and serialized behind any
                        # in-flight partial pass so two whisper runs never
                        # share the GPU.
                        transcript = await asyncio.to_thread(
                            transcribe_serialized, file_path, language
                        )
                        transcript = (transcript or "").strip()
                        print(f"[turn] transcribed at stop (full buffer): {transcript!r}")

                    if purpose == "wake_check":
                        if has_wake_phrase(transcript):
                            await stream_tts_audio(
                                websocket,
                                "Hello sir!",
                                role="wake",
                            )
                            await websocket.send_json(
                                {
                                    "type": "wake_greeting_done",
                                    "message": "Wake phrase confirmed.",
                                }
                            )
                        else:
                            await websocket.send_json(
                                {
                                    "type": "wake_not_detected",
                                    "message": "Wake phrase not detected.",
                                }
                            )
                        recording_started = False
                        chunks.clear()
                        continue

                    if not transcript:
                        await websocket.send_json(
                            {
                                "type": "no_speech",
                                "message": "No speech detected in that turn.",
                            }
                        )
                        recording_started = False
                        chunks.clear()
                        continue

                    if has_stop_phrase(transcript):
                        await websocket.send_json(
                            {
                                "type": "follow_up_stopped",
                                "message": "Stopped. Returning to idle.",
                            }
                        )
                        recording_started = False
                        chunks.clear()
                        continue

                    raw_conversation_id = payload.get("conversationId")
                    if raw_conversation_id:
                        try:
                            conversation_id = parse_conversation_id(raw_conversation_id)
                        except ValueError:
                            await websocket.send_json(
                                {"type": "error", "message": "Invalid conversationId."}
                            )
                            recording_started = False
                            chunks.clear()
                            continue

                    if conversation_id is None:
                        conversation_id = agent_loop.new_conversation_id()
                    else:
                        # Stale client state can hand us a conversation that
                        # was since closed (e.g. the New Conversation button).
                        # Closed conversations are terminal, so continue in a
                        # fresh one — the user_transcript echo below carries
                        # the replacement id and the client re-syncs to it.
                        existing = await asyncio.to_thread(
                            conversation_service.get_conversation, conversation_id
                        )
                        if existing is not None and existing.is_closed:
                            conversation_id = agent_loop.new_conversation_id()

                    # Echo what was heard so the transcript shows the spoken
                    # turn the same way it shows a typed one.
                    await websocket.send_json(
                        {
                            "type": "user_transcript",
                            "text": transcript,
                            "conversationId": str(conversation_id),
                        }
                    )

                    # Same event stream the chat endpoint consumes: speech and
                    # chat are one conversation, so they see the same tool
                    # calls and artifacts. Only text is spoken.
                    event_stream = agent_loop.conversation_loop_events(
                        transcript,
                        conversation_id,
                        prompt_source=PromptSourceEnum.SPEECH_PROMPT,
                    )
                    spoken_parts: list[str] = []
                    final_text: str | None = None
                    tts_available = True
                    async for event in iter_in_thread(event_stream):
                        event_type = event.get("type")

                        if event_type == "text":
                            spoken_parts.append(event["text"])
                            await send_assistant_text(
                                websocket,
                                event["text"],
                                seq=len(spoken_parts),
                                conversation_id=conversation_id,
                            )
                            # One failure mutes TTS for the rest of the turn:
                            # every remaining sentence would fail the same way
                            # and spam the client with error toasts. The text
                            # above was already sent, so the turn degrades to
                            # text-only instead of dying.
                            if tts_available:
                                tts_available = await stream_tts_audio(
                                    websocket, event["text"], role="final"
                                )
                        elif event_type == "status_text":
                            # Pre-tool acknowledgment: spoken so the user gets
                            # feedback before tool work goes quiet, but kept
                            # out of spoken_parts — the turn's assistantText
                            # is the final answer, not the "on it" line.
                            await websocket.send_json(
                                {
                                    "type": "status_text",
                                    "text": event["text"],
                                    "conversationId": str(conversation_id),
                                }
                            )
                            if tts_available:
                                tts_available = await stream_tts_audio(
                                    websocket, event["text"], role="status"
                                )
                        elif event_type == "text_final":
                            final_text = event["text"]
                            await websocket.send_json(
                                {
                                    "type": "text_final",
                                    "text": final_text,
                                    "format": "markdown",
                                    "conversationId": str(conversation_id),
                                }
                            )
                        else:
                            # tool_call / artifact: rendered, never spoken.
                            await websocket.send_json(
                                {**event, "conversationId": str(conversation_id)}
                            )

                    await websocket.send_json(
                        {
                            "type": "done",
                            "message": "Turn complete.",
                            "conversationId": str(conversation_id),
                            "assistantText": (
                                final_text
                                if final_text is not None
                                else " ".join(spoken_parts)
                            ),
                        }
                    )

                    # Nova decided the user was finished (end_session tool).
                    # Sent after "done" so the goodbye is spoken first, and
                    # deliberately the same event the stop-phrase path emits,
                    # so the client needs no new handling.
                    stop_reason = conversation_service.pop_stop_request(conversation_id)
                    if stop_reason is not None:
                        print(f"Nova ended the session: {stop_reason}")
                        await websocket.send_json(
                            {
                                "type": "follow_up_stopped",
                                "message": "Stopped. Returning to idle.",
                            }
                        )
                except ConversationClosedError as exc:
                    # Should be prevented by the pre-turn check above; kept as
                    # a backstop for races. The code lets the client drop its
                    # stored conversation id instead of retrying it forever.
                    try:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "code": "conversation_closed",
                                "message": str(exc),
                            }
                        )
                    except Exception:
                        pass
                except Exception as exc:
                    try:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": f"Voice pipeline failed: {str(exc)}",
                            }
                        )
                    except Exception:
                        # Client powered off / disconnected mid-turn; the next
                        # receive() will surface the disconnect and end the loop.
                        pass
                finally:
                    if file_path and file_path.exists():
                        os.remove(file_path)

                recording_started = False
                chunks.clear()
                partial_state["text"] = ""
                continue

            if event == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            await websocket.send_json(
                {"type": "error", "message": f"Unknown event: {event}"}
            )

    except WebSocketDisconnect:
        pass
