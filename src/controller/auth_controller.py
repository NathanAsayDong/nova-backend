"""
Login, sign-out, and the devices list.

/auth/login is the one route here the gate leaves open. Everything else runs
behind it, so by the time these handlers see a request, request.state.session
is the live NovaSession the gate found.
"""

import asyncio

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse

from src.service.auth_service import (
    AuthNotConfigured,
    AuthService,
    BadCredentials,
    LockedOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])

auth_service = AuthService()


def _client_ip(request: Request) -> str | None:
    """
    Who is really calling.

    Behind the Cloudflare tunnel every connection arrives from localhost, and
    the caller's address is in CF-Connecting-IP. Only Cloudflare can reach the
    origin through the tunnel, so that header can be trusted where a generic
    X-Forwarded-For could not.
    """
    forwarded = (request.headers.get("cf-connecting-ip") or "").strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else None


@router.post("/login")
async def login(request: Request, payload: dict = Body(...)) -> JSONResponse:
    username = str(payload.get("username") or "")
    password = str(payload.get("password") or "")
    try:
        token, session = await asyncio.to_thread(
            auth_service.login,
            username,
            password,
            _client_ip(request),
            request.headers.get("user-agent"),
        )
    except AuthNotConfigured:
        raise HTTPException(
            status_code=503,
            detail="Login is not configured on this server. "
            "Set NOVA_AUTH_USERNAME and NOVA_AUTH_PASSWORD and restart.",
        )
    except LockedOut as exc:
        return JSONResponse(
            status_code=429,
            content={"detail": str(exc), "retryAfter": exc.retry_after},
            headers={"Retry-After": str(exc.retry_after)},
        )
    except BadCredentials:
        raise HTTPException(status_code=401, detail="Wrong username or password.")

    return JSONResponse({"token": token, "session": session.public()})


@router.get("/session")
async def current_session(request: Request) -> dict:
    """Is this token still good, and what does the server know about it."""
    return {"session": request.state.session.public()}


@router.get("/sessions")
async def list_sessions(request: Request) -> dict:
    sessions = await asyncio.to_thread(auth_service.list_sessions)
    return {
        "sessions": [item.public() for item in sessions],
        "currentId": str(request.state.session.id),
    }


@router.post("/logout")
async def logout(request: Request) -> dict:
    await asyncio.to_thread(auth_service.logout, request.state.session.token_hash)
    return {"ok": True}


@router.post("/logout-all")
async def logout_all() -> dict:
    """Sign out every device, this one included."""
    revoked = await asyncio.to_thread(auth_service.logout_all)
    return {"ok": True, "revoked": revoked}
