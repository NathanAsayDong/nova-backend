"""
MCP server registry — the admin surface for Claude's MCP connector.

Servers registered here become tool surfaces for Nova on the next turn: the
agent loop reads the enabled set per request, so adding or toggling a server
needs no redeploy. Auth tokens are write-only; responses carry has_token.
"""

import asyncio
import html

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import HTMLResponse

from src.service.mcp_oauth_service import McpOAuthService
from src.service.mcp_server_service import McpServerService

router = APIRouter(prefix="/mcp-servers", tags=["mcp-servers"])

mcp_server_service = McpServerService()
mcp_oauth_service = McpOAuthService(mcp_server_service.mcp_server_dao)


def _callback_page(title: str, detail: str) -> str:
    return (
        "<!doctype html><html><body style='font-family: system-ui; "
        "display: grid; place-items: center; height: 90vh;'><div "
        "style='text-align: center; max-width: 32rem;'>"
        f"<h2>{html.escape(title)}</h2><p>{html.escape(detail)}</p>"
        "</div></body></html>"
    )


@router.get("")
async def list_mcp_servers() -> list[dict]:
    return await asyncio.to_thread(mcp_server_service.list_servers)


@router.post("/{server_id}/oauth/start")
async def start_mcp_oauth(server_id: int) -> dict:
    """Begin the consent flow; the client opens the returned URL in a tab."""
    try:
        return await asyncio.to_thread(mcp_oauth_service.begin, server_id)
    except ValueError as exc:
        status = 404 if "does not exist" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc))


@router.get("/oauth/callback")
async def mcp_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> HTMLResponse:
    """
    Where the provider sends the user after consent. Renders a human page
    because a browser lands here, not the SPA.
    """
    if error:
        return HTMLResponse(
            _callback_page(
                "Connection failed", error_description or error
            ),
            status_code=400,
        )
    if not code or not state:
        return HTMLResponse(
            _callback_page("Connection failed", "Missing code or state."),
            status_code=400,
        )
    try:
        result = await asyncio.to_thread(mcp_oauth_service.complete, state, code)
    except Exception as exc:
        return HTMLResponse(
            _callback_page("Connection failed", str(exc)), status_code=400
        )
    return HTMLResponse(
        _callback_page(
            f"✅ {result['server']} connected",
            "Nova can use this server on its next turn. You can close this tab.",
        )
    )


@router.post("")
async def create_mcp_server(payload: dict = Body(...)) -> dict:
    try:
        return await asyncio.to_thread(
            mcp_server_service.create_server,
            payload.get("name", ""),
            payload.get("url", ""),
            payload.get("authToken"),
            payload.get("enabled", True),
            payload.get("authKind"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/{server_id}")
async def update_mcp_server(server_id: int, payload: dict = Body(...)) -> dict:
    try:
        return await asyncio.to_thread(
            mcp_server_service.update_server,
            server_id,
            payload.get("name"),
            payload.get("url"),
            payload.get("authToken"),
            payload.get("enabled"),
        )
    except ValueError as exc:
        status = 404 if "does not exist" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc))


@router.delete("/{server_id}")
async def delete_mcp_server(server_id: int) -> dict:
    try:
        return await asyncio.to_thread(mcp_server_service.delete_server, server_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
