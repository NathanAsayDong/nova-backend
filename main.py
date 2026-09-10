import asyncio
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

load_dotenv()

from src.controller.call_controller import router as call_router
from src.controller.sms_controller import router as sms_router
from src.controller.conversation_controller import router as conversation_router
from src.controller.meeting_controller import router as meeting_router
from src.controller.nova_controller import router as nova_router
from src.controller.project_controller import router as project_router
from src.controller.tool_controller import router as tool_router
from src.controller.mcp_server_controller import router as mcp_server_router
from src.controller.update_controller import router as update_router
from src.controller.face_controller import router as face_router
from src.controller.coding_controller import router as coding_router
from src.controller.settings_controller import router as settings_router
from src.controller.auth_controller import router as auth_router, auth_service
from src.middleware.auth_gate import AuthGate

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Fail any meeting left recording by a previous run.

    Only one meeting may record at a time, so a row abandoned by a crash would
    block every future meeting with a baffling "already recording".
    """
    from src.controller.meeting_controller import meeting_service

    try:
        await asyncio.to_thread(meeting_service.recover_stale_meetings)
    except Exception as exc:
        print(f"Could not recover stale meetings: {exc}")

    # The coding tools run on the agent loop's worker thread but have to talk
    # to the Mac over a websocket that lives here. Hand them this loop so they
    # can schedule onto it instead of trying to await from a thread.
    from src.controller.coding_controller import coding_service

    coding_service.bind_loop(asyncio.get_running_loop())

    # Expired login sessions are dead weight; sweep them on each start.
    try:
        await asyncio.to_thread(auth_service.purge_expired)
    except Exception as exc:
        print(f"Could not purge expired sessions: {exc}")

    yield


def _allowed_origins() -> list[str]:
    """
    Where the browser client is allowed to call from.

    The Vite dev server is always allowed. The hosted frontend's origin(s)
    come from NOVA_ALLOWED_ORIGINS, comma-separated, e.g.
        NOVA_ALLOWED_ORIGINS=https://nova-xyz.web.app,https://nova-xyz.firebaseapp.com
    """
    dev = ["http://localhost:5173", "http://127.0.0.1:5173"]
    configured = [
        origin.strip().rstrip("/")
        for origin in (os.getenv("NOVA_ALLOWED_ORIGINS") or "").split(",")
        if origin.strip()
    ]
    return list(dict.fromkeys(dev + configured))


app = FastAPI(title="Nova Voice Backend", lifespan=lifespan)

# Order matters: the last middleware added is the outermost. CORS has to wrap
# the gate so that a 401 still carries the CORS headers the browser needs to
# read it, and so preflight never reaches the gate at all.
app.add_middleware(AuthGate, auth_service=auth_service)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(nova_router)
app.include_router(conversation_router)
app.include_router(project_router)
app.include_router(tool_router)
app.include_router(update_router)
app.include_router(meeting_router)
app.include_router(mcp_server_router)
app.include_router(face_router)
app.include_router(coding_router)
app.include_router(settings_router)
# Twilio's webhooks, not the browser client's — CORS above does not apply to
# them, and they are gated on Twilio's request signature instead.
app.include_router(call_router)
app.include_router(sms_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Nova backend online"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

# NOTE: In production the tower exposes this through a Cloudflare Tunnel
# (see docs/HOSTING.md). For Twilio-only local testing, `ngrok http 8000`.
