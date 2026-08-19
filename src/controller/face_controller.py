"""
Face feed: relays the main app tab's live state to face-display tabs.

This is a personal single-user deployment, so the design is deliberately
minimal: the main app tab connects once as the *publisher* (`?role=pub`) and
pushes tiny JSON events — the current face mode (idle / listening / thinking /
talking / meeting / off) and, while Nova is speaking, the playback amplitude
level. Any number of viewer tabs (`/face`) connect without a role and just
receive the relay. No auth, no rooms, no history: there is only ever one
conversation happening at a time.
"""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

router = APIRouter()

_viewers: set[WebSocket] = set()

# The most recent publisher connection. Reconnects overlap (a new app-tab
# socket can open before the dying one is noticed), so only the *current*
# publisher going away should put the face to sleep.
_current_publisher: WebSocket | None = None

# Snapshot for late-joining viewers. Starts (and resets) to "off": with no
# publisher connected there is no app tab playing audio, so a sleeping face is
# the honest default.
_last_mode_event: dict = {"type": "face_state", "mode": "off"}


async def _broadcast(event: dict) -> None:
    for viewer in list(_viewers):
        try:
            await viewer.send_json(event)
        except Exception:
            _viewers.discard(viewer)


@router.websocket("/ws/face")
async def face_socket(websocket: WebSocket, role: str = Query("view")) -> None:
    global _last_mode_event, _current_publisher
    await websocket.accept()

    if role == "pub":
        _current_publisher = websocket
        try:
            while True:
                data = await websocket.receive_json()
                event_type = data.get("type")
                if event_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif event_type == "face_state":
                    _last_mode_event = data
                    await _broadcast(data)
                elif event_type == "face_level":
                    await _broadcast(data)
        except WebSocketDisconnect:
            pass
        finally:
            # The app tab is gone, so nothing can be talking: put the face to
            # sleep rather than leaving it frozen mid-expression. A stale
            # socket superseded by a reconnect must not clobber the live one.
            if _current_publisher is websocket:
                _current_publisher = None
                _last_mode_event = {"type": "face_state", "mode": "off"}
                await _broadcast(_last_mode_event)
        return

    _viewers.add(websocket)
    try:
        await websocket.send_json(_last_mode_event)
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        _viewers.discard(websocket)
