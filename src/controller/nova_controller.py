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

from src.harness.agent_loop import AgentLoop
from src.model.tool import Tool
from src.service.conversation_service import ConversationClosedError, ConversationService
from src.service.project_service import ProjectService
from src.service.tool_service import ToolService
from src.service.tts_service import TTSService
from src.service.whisper_service import WhisperService

router = APIRouter(tags=["transcribe"])
whisper_service = WhisperService()
tool_service = ToolService()
tts_service = TTSService()
conversation_service = ConversationService()
project_service = ProjectService()
agent_loop = AgentLoop()
agent_loop.conversation_service = conversation_service


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

        sentence_stream = agent_loop.conversation_loop_stream(message, conversation_id)
        parts: list[str] = []
        try:
            async for sentence in iter_in_thread(sentence_stream):
                parts.append(sentence)
                yield sse_event(
                    {"type": "delta", "text": sentence, "seq": len(parts)}
                )
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

        yield sse_event(
            {
                "type": "done",
                "conversationId": str(final_conversation_id),
                "assistantText": " ".join(parts),
            }
        )

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str) -> dict:
    """Current state of a conversation, including its attached project (if any)."""
    try:
        uuid_value = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation id.")

    conversation = await asyncio.to_thread(
        conversation_service.get_conversation, uuid_value
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    project_payload = None
    if conversation.project_id is not None:
        project = await asyncio.to_thread(
            project_service.get_project, conversation.project_id
        )
        if project is not None:
            project_payload = {"id": project.id, **project.to_payload()}

    return {
        "conversationId": str(conversation.uuid),
        "isClosed": conversation.is_closed,
        "project": project_payload,
    }


@router.post("/conversations/{conversation_id}/close")
async def close_conversation(conversation_id: str) -> dict:
    """Close a conversation permanently. Closed conversations cannot be reopened."""
    try:
        uuid_value = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation id.")

    conversation = await asyncio.to_thread(
        conversation_service.close_conversation, uuid_value
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    # Drop the in-process LLM history so the closed conversation can't keep
    # accumulating context if the same id is replayed.
    agent_loop.conversations.pop(uuid_value, None)

    return {"conversationId": str(uuid_value), "isClosed": True}


@router.get("/projects")
async def list_projects() -> list[dict]:
    return await asyncio.to_thread(project_service.list_projects)


async def iter_in_thread(generator):
    """Consume a sync generator without blocking the event loop."""
    sentinel = object()
    while True:
        item = await asyncio.to_thread(next, generator, sentinel)
        if item is sentinel:
            return
        yield item


def suffix_for_mime(mime_type: str) -> str:
    mime = (mime_type or "").lower()
    if "wav" in mime:
        return ".wav"
    if "ogg" in mime:
        return ".ogg"
    if "mp4" in mime or "mpeg" in mime:
        return ".mp4"
    return ".webm"


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
) -> None:
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

    for sequence, audio_chunk in enumerate(tts_service.stream_text_to_speech(text), start=1):
        chunk_b64 = base64.b64encode(audio_chunk).decode("ascii")
        await websocket.send_json(
            {
                "type": "assistant_audio_stream_chunk",
                "streamId": stream_id,
                "chunkBase64": chunk_b64,
                "seq": sequence,
            }
        )

    await websocket.send_json(
        {
            "type": "assistant_audio_stream_end",
            "streamId": stream_id,
        }
    )


@router.get("/tools")
async def list_tools() -> list[Tool]:
    return tool_service.list_tools()


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
                recording_started = True
                chunks.clear()
                language = payload.get("language")
                mime_type = payload.get("mimeType", "audio/webm")
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
                    }
                )
                continue

            if event == "wake_greeting":
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
                    suffix = suffix_for_mime(mime_type)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                        for audio_chunk in chunks:
                            temp.write(audio_chunk)
                        file_path = Path(temp.name)

                    transcript = whisper_service.transcribe_file_path(file_path, language)
                    transcript = (transcript or "").strip()

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

                    sentence_stream = agent_loop.conversation_loop_stream(
                        transcript, conversation_id
                    )
                    spoken_parts: list[str] = []
                    async for sentence in iter_in_thread(sentence_stream):
                        spoken_parts.append(sentence)
                        await send_assistant_text(
                            websocket,
                            sentence,
                            seq=len(spoken_parts),
                            conversation_id=conversation_id,
                        )
                        await stream_tts_audio(websocket, sentence, role="final")

                    await websocket.send_json(
                        {
                            "type": "done",
                            "message": "Turn complete.",
                            "conversationId": str(conversation_id),
                            "assistantText": " ".join(spoken_parts),
                        }
                    )
                except Exception as exc:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Voice pipeline failed: {str(exc)}",
                        }
                    )
                finally:
                    if file_path and file_path.exists():
                        os.remove(file_path)

                recording_started = False
                chunks.clear()
                continue

            if event == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            await websocket.send_json(
                {"type": "error", "message": f"Unknown event: {event}"}
            )

    except WebSocketDisconnect:
        pass
