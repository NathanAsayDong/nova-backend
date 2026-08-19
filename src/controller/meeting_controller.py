"""
Meeting mode's HTTP and WebSocket surface.

Meeting capture gets its own socket rather than a flag on /ws/transcribe
because the two have opposite shapes. An assistant turn is seconds long and
re-transcribes its whole buffer for live captions; a meeting runs for an hour,
and re-transcribing the whole buffer every second would be quadratic and would
fall behind inside ten minutes.

So a meeting is written to disk as it arrives, and only the tail past a cursor
is ever transcribed: a cheap partial pass for the live view, and a commit pass
that persists once enough has accumulated. Cost per pass stays flat no matter
how long the meeting runs.
"""

import asyncio
import json
import os
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Query, WebSocket, WebSocketDisconnect

from src.controller.audio_ws import (
    asr_lock,
    asr_service,
    transcribe_segments_serialized,
)
from src.service.meeting_service import MeetingError, MeetingService

router = APIRouter(tags=["meetings"])

meeting_service = MeetingService()

# How often the live view refreshes. Each pass transcribes only the tail past
# the cursor, so this is bounded work however long the meeting has run.
PARTIAL_SECONDS = float(os.getenv("MEETING_PARTIAL_SECONDS", "5"))

# How much audio accumulates before the tail is written to the database.
WINDOW_SECONDS = float(os.getenv("MEETING_WINDOW_SECONDS", "30"))

# Below this there is not enough audio for a useful pass.
MIN_TAIL_SECONDS = 2.0

SAMPLE_RATE = 16000


def _meeting_error(exc: MeetingError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(exc))


# ---------- REST ----------


@router.post("/meetings")
async def start_meeting(payload: dict = Body(default={})) -> dict:
    """Enter meeting mode. The button, and the endpoint behind start_meeting."""
    try:
        return await asyncio.to_thread(
            meeting_service.start_meeting,
            title=payload.get("title"),
            project_id=payload.get("projectId") or payload.get("project_id"),
        )
    except MeetingError as exc:
        raise _meeting_error(exc)


@router.get("/meetings/active")
async def get_active_meeting() -> dict:
    """The recording meeting, or null. Drives the client's mode indicator."""
    return {"meeting": await asyncio.to_thread(meeting_service.get_active_meeting)}


@router.get("/meetings/search")
async def search_meetings(
    q: str = Query(..., description="What to search meeting transcripts for."),
    projectId: int | None = None,
    sinceDays: int | None = None,
    limit: int = 5,
) -> dict:
    """Declared before /meetings/{uuid} so 'search' is not read as an id."""
    try:
        results = await asyncio.to_thread(
            meeting_service.search_meetings,
            query=q,
            project_id=projectId,
            since_days=sinceDays,
            limit=limit,
        )
    except MeetingError as exc:
        raise _meeting_error(exc)
    return {"results": results}


@router.get("/meetings")
async def list_meetings(
    projectId: int | None = None, limit: int = 20, sinceDays: int | None = None
) -> dict:
    meetings = await asyncio.to_thread(
        meeting_service.list_meetings,
        project_id=projectId,
        limit=limit,
        since_days=sinceDays,
    )
    return {"meetings": meetings}


@router.get("/meetings/{meeting_uuid}")
async def get_meeting(meeting_uuid: str) -> dict:
    """One meeting with its notes, if written yet."""
    try:
        return await asyncio.to_thread(meeting_service.get_meeting_notes, meeting_uuid)
    except MeetingError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/meetings/{meeting_uuid}/segments")
async def get_meeting_segments(
    meeting_uuid: str, startMs: int | None = None, endMs: int | None = None
) -> dict:
    try:
        return await asyncio.to_thread(
            meeting_service.get_meeting_segments, meeting_uuid, startMs, endMs
        )
    except MeetingError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/meetings/{meeting_uuid}")
async def update_meeting(meeting_uuid: str, payload: dict = Body(default={})) -> dict:
    """Rename a meeting, or move it to (or off) a project."""
    try:
        return await asyncio.to_thread(
            meeting_service.update_meeting,
            meeting_uuid,
            title=payload.get("title"),
            project_id=payload.get("projectId") or payload.get("project_id"),
            clear_project=bool(payload.get("clearProject")),
        )
    except MeetingError as exc:
        raise _meeting_error(exc)


@router.delete("/meetings/{meeting_uuid}")
async def delete_meeting(meeting_uuid: str) -> dict:
    """Delete a meeting and everything derived from it."""
    try:
        return await asyncio.to_thread(meeting_service.delete_meeting, meeting_uuid)
    except MeetingError as exc:
        raise _meeting_error(exc)


@router.post("/meetings/{meeting_uuid}/stop")
async def stop_meeting(meeting_uuid: str, payload: dict = Body(default={})) -> dict:
    """Leave meeting mode. Notes are prepared in the background."""
    try:
        return await asyncio.to_thread(
            meeting_service.stop_meeting,
            meeting_uuid=meeting_uuid,
            generate_notes=payload.get("generateNotes", True),
        )
    except MeetingError as exc:
        raise _meeting_error(exc)


@router.post("/meetings/{meeting_uuid}/notes")
async def regenerate_notes(meeting_uuid: str, payload: dict = Body(default={})) -> dict:
    """Write the notes again, optionally for a specific cut. Additive."""
    try:
        return await asyncio.to_thread(
            meeting_service.generate_notes, meeting_uuid, payload.get("instructions")
        )
    except MeetingError as exc:
        raise _meeting_error(exc)


# ---------- WebSocket ----------


@router.websocket("/ws/meeting")
async def meeting_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json(
        {"type": "ready", "message": "Connected. Send start, then stream chunks."}
    )

    meeting: dict | None = None
    meeting_id: int | None = None
    audio_path: Path | None = None
    language: str | None = None
    recording = False
    # Where committed transcript ends, in seconds from the start of the
    # recording. Everything past it is the untranscribed tail.
    cursor_seconds = 0.0
    capture_task: asyncio.Task | None = None

    async def send(payload: dict) -> None:
        try:
            await websocket.send_json(payload)
        except Exception:
            # Client vanished mid-meeting; the receive loop will notice.
            pass

    def _transcribe_tail() -> tuple[list, float]:
        """
        Transcribe only the audio past the cursor.

        Runs on a worker thread. The container has to be decoded from its
        header every time — webm chunks are not independently decodable — but
        decoding is ~1000x realtime, so only the transcription is slice-sized.
        """
        samples = asr_service.decode_audio(str(audio_path))
        total_seconds = len(samples) / SAMPLE_RATE
        start_sample = int(cursor_seconds * SAMPLE_RATE)
        tail = samples[start_sample:]
        if len(tail) < MIN_TAIL_SECONDS * SAMPLE_RATE:
            return [], total_seconds
        return transcribe_segments_serialized(tail, language), total_seconds

    async def capture_loop() -> None:
        """
        Refresh the live view, and commit to the database once a window fills.

        Partial passes are best-effort and their text is replaced wholesale on
        the client; committed segments are the durable record.
        """
        nonlocal cursor_seconds
        while recording:
            await asyncio.sleep(PARTIAL_SECONDS)
            if not recording or audio_path is None or not audio_path.exists():
                continue
            # A spoken turn is waiting on the same GPU. Skip this pass; the
            # meeting can be a few seconds behind, a person cannot.
            if asr_lock.priority_pending:
                continue

            try:
                segments, total_seconds = await asyncio.to_thread(_transcribe_tail)
            except Exception as exc:
                print(f"Meeting tail transcription failed (ignored): {exc}")
                continue

            if not segments:
                continue

            tail_seconds = total_seconds - cursor_seconds
            if tail_seconds < WINDOW_SECONDS:
                await send(
                    {
                        "type": "partial_transcript",
                        "text": " ".join(s.text for s in segments).strip(),
                        "fromMs": int(cursor_seconds * 1000),
                    }
                )
                continue

            # Commit everything except a trailing segment that probably runs
            # past the end of what we have, so no utterance is split in half.
            complete = [s for s in segments if s.end < tail_seconds - 0.5] or segments
            try:
                committed = await asyncio.to_thread(
                    meeting_service.commit_segments,
                    meeting_id,
                    complete,
                    cursor_seconds,
                )
            except Exception as exc:
                print(f"Meeting segment commit failed: {exc}")
                continue

            if committed:
                cursor_seconds += complete[-1].end
                await send({"type": "segments_committed", "segments": committed})

    async def flush_tail() -> None:
        """Final pass so the last partial window is not lost on stop."""
        if audio_path is None or not audio_path.exists():
            return
        try:
            segments, _ = await asyncio.to_thread(_transcribe_tail)
            if segments:
                committed = await asyncio.to_thread(
                    meeting_service.commit_segments, meeting_id, segments, cursor_seconds
                )
                if committed:
                    await send({"type": "segments_committed", "segments": committed})
        except Exception as exc:
            print(f"Meeting final flush failed: {exc}")

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            chunk = message.get("bytes")
            text_data = message.get("text")

            if chunk is not None:
                if not recording or audio_path is None:
                    continue
                # Appended rather than buffered: an hour of audio has no
                # business sitting in the event loop's memory.
                with open(audio_path, "ab") as handle:
                    handle.write(chunk)
                continue

            if text_data is None:
                continue

            try:
                payload = json.loads(text_data)
            except json.JSONDecodeError:
                await send({"type": "error", "message": "Invalid JSON control message."})
                continue

            event = payload.get("event")

            if event == "start":
                raw_uuid = payload.get("meetingId") or payload.get("meeting_id")
                try:
                    if raw_uuid:
                        found = await asyncio.to_thread(
                            meeting_service.get_meeting_notes, str(raw_uuid)
                        )
                        meeting = found["meeting"]
                    else:
                        meeting = await asyncio.to_thread(
                            meeting_service.get_active_meeting
                        )
                except MeetingError as exc:
                    await send({"type": "error", "message": str(exc)})
                    continue

                if meeting is None:
                    await send(
                        {
                            "type": "error",
                            "message": (
                                "No meeting is recording. Start one first — Nova "
                                "can do it, or use the button."
                            ),
                        }
                    )
                    continue
                if meeting["status"] != "recording":
                    await send(
                        {
                            "type": "error",
                            "message": f"That meeting is {meeting['status']}, not recording.",
                        }
                    )
                    continue

                meeting_id = await asyncio.to_thread(
                    _resolve_meeting_id, meeting["uuid"]
                )
                language = payload.get("language")
                audio_path = meeting_service.audio_path_for(meeting_id)
                # Resume rather than truncate: a dropped socket reconnecting
                # mid-meeting must not throw away what it already captured.
                cursor_seconds = (
                    await asyncio.to_thread(
                        meeting_service.meeting_dao.get_last_segment_end_ms, meeting_id
                    )
                ) / 1000.0
                recording = True
                capture_task = asyncio.create_task(capture_loop())

                await send(
                    {
                        "type": "recording",
                        "meeting": meeting,
                        "resumedAtMs": int(cursor_seconds * 1000),
                        "message": "Meeting mode. Nova is transcribing, not answering.",
                    }
                )
                continue

            if event == "stop":
                recording = False
                if capture_task is not None:
                    capture_task.cancel()
                    capture_task = None
                await flush_tail()

                try:
                    result = await asyncio.to_thread(
                        meeting_service.stop_meeting,
                        meeting["uuid"] if meeting else None,
                        payload.get("generateNotes", True),
                    )
                    await send({"type": "processing", **result})
                except MeetingError as exc:
                    await send({"type": "error", "message": str(exc)})
                continue

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        print(f"Meeting socket failed: {exc}")
    finally:
        recording = False
        if capture_task is not None:
            capture_task.cancel()
        # Deliberately NOT stopping the meeting here. A dropped connection is
        # usually a flaky network, not the end of the meeting — the row stays
        # in 'recording' so a reconnect resumes it. Stopping is always an
        # explicit act, by the button or by Nova.


def _resolve_meeting_id(meeting_uuid: str) -> int:
    found = meeting_service.meeting_dao.get_by_uuid(UUID(str(meeting_uuid)))
    if found is None:
        raise MeetingError(f"No meeting found with id {meeting_uuid}.")
    return found.id
