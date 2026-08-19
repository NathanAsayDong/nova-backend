import asyncio
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
    yield


app = FastAPI(title="Nova Voice Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nova_router)
app.include_router(conversation_router)
app.include_router(project_router)
app.include_router(tool_router)
app.include_router(update_router)
app.include_router(meeting_router)
app.include_router(mcp_server_router)
app.include_router(face_router)
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

#NOTE: Run ngrok http 8000 to get a public URL for the backend
