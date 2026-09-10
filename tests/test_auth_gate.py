"""
Coverage for the request gate, on a tiny app rather than main.py.

The gate is raw ASGI, so what matters is checked end to end through Starlette's
test client: exempt paths pass, everything else needs a token, sockets take it
from the query string, a 401 still carries CORS headers, and streaming bodies
are not buffered on the way through.
"""

import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from src.middleware.auth_gate import AuthGate, bearer_token, is_exempt
from src.service.auth_service import AuthService, PASSWORD_ENV, USERNAME_ENV
from tests.test_auth_service import FakeDao


def build_app(service: AuthService) -> FastAPI:
    app = FastAPI()
    app.add_middleware(AuthGate, auth_service=service)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://nova.web.app"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/secret")
    async def secret(request: Request):
        return {"session": str(request.state.session.id)}

    @app.get("/stream")
    async def stream():
        async def chunks():
            yield b"one\n"
            yield b"two\n"

        return StreamingResponse(chunks(), media_type="text/plain")

    @app.websocket("/ws/transcribe")
    async def transcribe(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_json({"hello": str(websocket.state.session.id)})
        await websocket.close()

    @app.websocket("/ws/face")
    async def face(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_json({"open": True})
        await websocket.close()

    return app


class GateTestCase(unittest.TestCase):
    def setUp(self):
        AuthService.reset_state()
        self.service = AuthService(dao=FakeDao())
        self.env = patch.dict(os.environ, {USERNAME_ENV: "nate", PASSWORD_ENV: "hunter2"})
        self.env.start()
        self.client = TestClient(build_app(self.service))
        self.token, _ = self.service.login("nate", "hunter2")

    def tearDown(self):
        self.env.stop()
        AuthService.reset_state()

    def auth(self):
        return {"Authorization": f"Bearer {self.token}"}


class ExemptionTests(unittest.TestCase):
    def test_exempt_list(self):
        for path in ["/", "/health", "/auth/login", "/calls/answer", "/sms/inbound",
                     "/ws/coding", "/ws/face", "/mcp-servers/oauth/callback"]:
            self.assertTrue(is_exempt(path), path)
        for path in ["/auth/logout", "/auth/session", "/chat/stream", "/ws/transcribe",
                     "/mcp-servers", "/mcp-servers/3/oauth/start", "/conversations/1",
                     "/docs", "/openapi.json"]:
            self.assertFalse(is_exempt(path), path)

    def test_bearer_token_sources(self):
        http = {"type": "http", "headers": [(b"authorization", b"Bearer abc")]}
        self.assertEqual(bearer_token(http), "abc")
        self.assertIsNone(bearer_token({"type": "http", "headers": [(b"authorization", b"Basic x")]}))
        # The query string only counts for sockets.
        self.assertIsNone(bearer_token({"type": "http", "headers": [], "query_string": b"token=abc"}))
        ws = {"type": "websocket", "headers": [], "query_string": b"role=pub&token=xyz"}
        self.assertEqual(bearer_token(ws), "xyz")


class HttpGateTests(GateTestCase):
    def test_health_is_open(self):
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_gated_route_without_token_is_401(self):
        response = self.client.get("/secret")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_gated_route_with_bad_token_is_401(self):
        self.assertEqual(
            self.client.get("/secret", headers={"Authorization": "Bearer nope"}).status_code, 401
        )

    def test_gated_route_with_token_passes_and_exposes_session(self):
        response = self.client.get("/secret", headers=self.auth())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["session"])

    def test_401_carries_cors_headers(self):
        response = self.client.get("/secret", headers={"Origin": "https://nova.web.app"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"), "https://nova.web.app"
        )

    def test_preflight_never_needs_a_token(self):
        response = self.client.options(
            "/secret",
            headers={
                "Origin": "https://nova.web.app",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_unconfigured_server_says_so(self):
        with patch.dict(os.environ, {PASSWORD_ENV: ""}):
            response = self.client.get("/secret", headers=self.auth())
        self.assertEqual(response.status_code, 503)
        self.assertIn("NOVA_AUTH_PASSWORD", response.json()["detail"])

    def test_streaming_passes_through(self):
        response = self.client.get("/stream", headers=self.auth())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "one\ntwo\n")

    def test_revoked_token_is_refused_immediately(self):
        self.assertEqual(self.client.get("/secret", headers=self.auth()).status_code, 200)
        self.service.logout_all()
        self.assertEqual(self.client.get("/secret", headers=self.auth()).status_code, 401)


class WebSocketGateTests(GateTestCase):
    def test_socket_with_query_token_connects(self):
        with self.client.websocket_connect(f"/ws/transcribe?token={self.token}") as ws:
            self.assertTrue(ws.receive_json()["hello"])

    def test_socket_without_token_is_refused(self):
        with self.assertRaises(Exception):
            with self.client.websocket_connect("/ws/transcribe"):
                pass

    def test_face_socket_stays_open(self):
        with self.client.websocket_connect("/ws/face?role=pub") as ws:
            self.assertEqual(ws.receive_json(), {"open": True})


if __name__ == "__main__":
    unittest.main()
