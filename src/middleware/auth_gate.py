"""
The login gate: every route needs a session unless it is on the short list.

Written as raw ASGI rather than Starlette's BaseHTTPMiddleware because this
has to cover WebSockets too, and because BaseHTTPMiddleware buffers streaming
responses — /chat/stream would stop streaming the moment it was wrapped.

HTTP requests present the token as `Authorization: Bearer <token>`. Browsers
cannot set headers on a WebSocket, so sockets carry it as `?token=` instead
(over TLS the query string is inside the encrypted stream, and the tower logs
paths without it). A refused socket is closed before the handshake completes,
which the browser sees as a failed connection.

What is exempt, and why each one is:

  /               /health              liveness, say nothing
  /auth/login                          how you get a session
  /calls/*        /sms/*               Twilio's webhooks, gated on Twilio's
                                       request signature instead
  /ws/coding                           the Mac agent's socket, gated on its
                                       own shared token
  /ws/face                             the face display, deliberately open
  /mcp-servers/oauth/callback          the OAuth provider redirects a bare
                                       browser here; it carries a state
                                       nonce and nothing else can use it
"""

import asyncio
import json
from urllib.parse import parse_qs

from src.service.auth_service import AuthService

EXEMPT_EXACT = frozenset({"/", "/health", "/auth/login"})
EXEMPT_PREFIXES = (
    "/calls/",
    "/sms/",
    "/ws/coding",
    "/ws/face",
    "/mcp-servers/oauth/callback",
)


def is_exempt(path: str) -> bool:
    if path in EXEMPT_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES)


def _header(scope: dict, name: bytes) -> str:
    for key, value in scope.get("headers") or []:
        if key == name:
            return value.decode("latin-1")
    return ""


def bearer_token(scope: dict) -> str | None:
    """The token this request presents, from the header or (sockets) the query."""
    header = _header(scope, b"authorization")
    if header.lower().startswith("bearer "):
        presented = header[7:].strip()
        if presented:
            return presented
    if scope["type"] == "websocket":
        query = parse_qs((scope.get("query_string") or b"").decode("latin-1"))
        values = query.get("token")
        if values and values[0]:
            return values[0]
    return None


class AuthGate:
    def __init__(self, app, auth_service: AuthService):
        self.app = app
        self.auth = auth_service

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Preflight carries no credentials by definition; CORS answers it.
        if scope["type"] == "http" and scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return

        if is_exempt(scope["path"]):
            await self.app(scope, receive, send)
            return

        token = bearer_token(scope)
        session = None
        if token:
            session = await asyncio.to_thread(self.auth.authenticate, token)

        if session is None:
            await self._reject(scope, send)
            return

        # Request.state reads scope["state"]; the auth controller uses this
        # to know which session "sign out" means.
        scope.setdefault("state", {})["session"] = session
        await self.app(scope, receive, send)

    async def _reject(self, scope, send) -> None:
        if scope["type"] == "websocket":
            # Closing before accept refuses the handshake outright.
            await send({"type": "websocket.close", "code": 4401, "reason": "Not authenticated"})
            return

        if not self.auth.configured():
            status = 503
            body = {
                "detail": "Login is not configured on this server. "
                "Set NOVA_AUTH_USERNAME and NOVA_AUTH_PASSWORD and restart."
            }
        else:
            status = 401
            body = {"detail": "Not authenticated"}

        payload = json.dumps(body).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(payload)).encode("ascii")),
                    (b"www-authenticate", b"Bearer"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": payload})
