from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

load_dotenv()

from src.controller.conversation_controller import router as conversation_router
from src.controller.nova_controller import router as nova_router
from src.controller.project_controller import router as project_router
from src.controller.tool_controller import router as tool_router
from src.controller.mcp_server_controller import router as mcp_server_router
from src.controller.update_controller import router as update_router

app = FastAPI(title="Nova Voice Backend")

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
app.include_router(mcp_server_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Nova backend online"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
