"""
The tower's end of the Mac's coding link, plus the UI's read side.

Nate's repos are on his Mac and this process is on the tower, so Nova cannot
run Claude Code itself — it asks the Mac to. The Mac dials in here (the same
direction the browser dials /ws/face, and for the same reasons), and this
module is the switchboard: commands out, events in, everything persisted so
the UI and Nova's tools can read a session's state whether or not the laptop
is currently awake.

Exactly one agent connects. A second connection replaces the first rather
than being refused, because the common cause is a reconnect racing a
half-dead socket the tower has not noticed yet.
"""

import asyncio
import json
import os
import uuid
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Query, WebSocket, WebSocketDisconnect

from src.service.coding_service import CodingService

router = APIRouter(tags=["coding"])
coding_service = CodingService()


class AgentLink:
    """
    The live connection to the Mac, and the request/response layer over it.

    The websocket is message-oriented and the tools want call-and-return, so
    every command carries a request_id and waits on a future the reader
    resolves. A command sent while the Mac is away fails fast rather than
    hanging: the caller can then queue the work and tell the user the laptop
    is asleep, which is a better answer than a timeout.
    """

    def __init__(self) -> None:
        self.socket: WebSocket | None = None
        self.pending: dict[str, asyncio.Future] = {}

    @property
    def connected(self) -> bool:
        return self.socket is not None

    async def call(self, command: str, timeout: float = 90.0, **fields: Any) -> Any:
        socket = self.socket
        if socket is None:
            raise HTTPException(
                status_code=503,
                detail="The Mac coding agent is not connected. Is the laptop awake?",
            )

        request_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self.pending[request_id] = future
        try:
            await socket.send_json({"command": command, "request_id": request_id, **fields})
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504, detail=f"The Mac agent did not answer '{command}' in time."
            )
        finally:
            self.pending.pop(request_id, None)

    def resolve(self, request_id: str, result: Any, error: str | None = None) -> None:
        future = self.pending.get(request_id)
        if future is None or future.done():
            return
        if error is not None:
            future.set_exception(HTTPException(status_code=502, detail=error))
        else:
            future.set_result(result)


link = AgentLink()
# On the class, not this instance: every tool call builds its own
# CodingService, and each one has to see the same socket.
CodingService.bind_link(link)


def _authorized(websocket: WebSocket) -> bool:
    """
    Gate the socket on the shared token.

    /ws/face has no auth because the worst case is an animated face. This one
    executes code changes on Nate's machine, so an unauthenticated connection
    is a remote shell. A missing NOVA_CODE_TOKEN on the server means the
    feature is not configured, and the socket is refused rather than opened
    wide — failing closed is the only safe default for this one.
    """
    expected = (os.getenv("NOVA_CODE_TOKEN") or "").strip()
    if not expected:
        return False
    header = websocket.headers.get("authorization", "")
    presented = header[7:].strip() if header.lower().startswith("bearer ") else ""
    return bool(presented) and presented == expected


@router.websocket("/ws/coding")
async def coding_socket(websocket: WebSocket) -> None:
    if not _authorized(websocket):
        await websocket.close(code=4401)
        return

    await websocket.accept()

    # A reconnect usually arrives before the tower has noticed the old socket
    # died, so the newcomer wins rather than being turned away.
    previous = link.socket
    link.socket = websocket
    if previous is not None:
        try:
            await previous.close()
        except Exception:
            pass

    print("Mac coding agent connected.")
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if event.get("type") == "ack":
                link.resolve(event.get("request_id", ""), event.get("result"))
                continue

            if event.get("type") == "error" and event.get("request_id"):
                link.resolve(
                    event["request_id"], None, error=event.get("detail") or "agent error"
                )
                continue

            await asyncio.to_thread(coding_service.record_event, event)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        print(f"Coding socket failed: {exc}")
    finally:
        if link.socket is websocket:
            link.socket = None
        print("Mac coding agent disconnected.")


# ---------- read side, for the UI ----------


@router.get("/coding/status")
async def coding_status() -> dict:
    """Whether the Mac is reachable — the UI greys itself out when it is not."""
    return {"agentConnected": link.connected}


@router.get("/coding/sessions")
async def list_coding_sessions(limit: int = Query(20, ge=1, le=100)) -> dict:
    sessions = await asyncio.to_thread(coding_service.list_sessions, limit)
    return {"sessions": sessions, "agentConnected": link.connected}


@router.get("/coding/sessions/{session_id}")
async def get_coding_session(session_id: str, afterSeq: int = Query(0, ge=0)) -> dict:
    try:
        parsed = UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session id.")
    detail = await asyncio.to_thread(coding_service.get_session_detail, parsed, afterSeq)
    if detail is None:
        raise HTTPException(status_code=404, detail="No such coding session.")
    return {**detail, "agentConnected": link.connected}


@router.post("/coding/sessions")
async def start_coding_session(payload: dict = Body(...)) -> dict:
    repo = (payload.get("repo") or "").strip()
    instructions = (payload.get("instructions") or "").strip()
    if not repo or not instructions:
        raise HTTPException(status_code=400, detail="'repo' and 'instructions' are required.")
    return await coding_service.start(
        repo=repo,
        instructions=instructions,
        title=payload.get("title"),
        project_id=payload.get("projectId"),
    )


@router.post("/coding/sessions/{session_id}/feedback")
async def send_coding_feedback(session_id: str, payload: dict = Body(...)) -> dict:
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="'text' is required.")
    try:
        parsed = UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session id.")
    return await coding_service.feedback(parsed, text, steer=bool(payload.get("steer")))


@router.post("/coding/sessions/{session_id}/stop")
async def stop_coding_session(session_id: str) -> dict:
    try:
        parsed = UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session id.")
    return await coding_service.stop(parsed)
