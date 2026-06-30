import base64
import json
import os
import re
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from src.service.openai_service import OpenAIService
from src.service.tool_registry import ToolExecutionError
from src.service.tool_service import ToolService
from src.service.tts_service import TTSService
from src.service.whisper_service import WhisperService

router = APIRouter(tags=["transcribe"])
whisper_service = WhisperService()
tool_service = ToolService()
openai_service = OpenAIService(tool_service=tool_service)
tts_service = TTSService()


class ToolToggleRequest(BaseModel):
    enabled: bool


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
async def list_tools() -> list[dict[str, object]]:
    return tool_service.list_tools()


@router.patch("/tools/{name}")
async def toggle_tool(name: str, request: ToolToggleRequest) -> dict[str, object]:
    try:
        return tool_service.set_enabled(name, request.enabled)
    except ToolExecutionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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

                    async def emit_progress(progress_text: str, iteration: int) -> None:
                        await websocket.send_json(
                            {
                                "type": "assistant_progress",
                                "text": progress_text,
                                "iteration": iteration,
                            }
                        )
                        await stream_tts_audio(
                            websocket,
                            progress_text,
                            role="progress",
                            iteration=iteration,
                        )

                    loop_result = await openai_service.run_agent_loop(
                        transcript,
                        progress_callback=emit_progress
                    )

                    await stream_tts_audio(websocket, loop_result.final_text, role="final")

                    await websocket.send_json(
                        {
                            "type": "done",
                            "message": "Turn complete.",
                            "iterationsUsed": loop_result.iterations_used,
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
