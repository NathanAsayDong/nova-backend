import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from src.model.mcp_server import McpServer
from src.service.mcp_oauth_service import McpOAuthService
from src.service.mcp_server_service import McpServerService


class FakeDao:
    def __init__(self, servers=()):
        self.servers = {s.id: s for s in servers}

    def get(self, id):
        return self.servers.get(int(id))

    def get_by_oauth_state(self, state):
        return next(
            (s for s in self.servers.values() if s.oauth_state == state), None
        )

    def get_enabled(self):
        return sorted(
            (s for s in self.servers.values() if s.enabled), key=lambda s: s.name
        )

    def update(self, id, columns):
        server = self.servers.get(int(id))
        if server is None:
            return None
        for key, value in columns.items():
            setattr(server, key, value)
        return server


class FakeResponse:
    def __init__(self, payload=None, status=200, text=""):
        self.payload = payload
        self.ok = status < 400
        self.status_code = status
        self.text = text or str(payload)

    def json(self):
        return self.payload


def oauth_server(**overrides) -> McpServer:
    defaults = dict(
        id=1,
        name="notion",
        url="https://mcp.example.com/mcp",
        auth_kind="oauth",
        enabled=True,
    )
    defaults.update(overrides)
    return McpServer(**defaults)


class BeginFlowTests(unittest.TestCase):
    def _run_begin(self, get_responses):
        dao = FakeDao([oauth_server()])
        service = McpOAuthService(dao)

        def fake_get(url, **kwargs):
            return get_responses.get(url, FakeResponse(status=404))

        def fake_post(url, **kwargs):
            self.assertEqual(url, "https://auth.example.com/register")
            body = kwargs["json"]
            self.assertEqual(body["redirect_uris"], [service.redirect_uri()])
            return FakeResponse({"client_id": "client-123"})

        with mock.patch("src.service.mcp_oauth_service.requests") as fake_requests:
            fake_requests.get.side_effect = fake_get
            fake_requests.post.side_effect = fake_post
            result = service.begin(1)
        return dao.servers[1], result

    def test_begin_discovers_registers_and_builds_pkce_url(self):
        metadata = {
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "registration_endpoint": "https://auth.example.com/register",
        }
        server, result = self._run_begin(
            {
                "https://mcp.example.com/.well-known/oauth-protected-resource/mcp": FakeResponse(
                    {"authorization_servers": ["https://auth.example.com"]}
                ),
                "https://auth.example.com/.well-known/oauth-authorization-server": FakeResponse(
                    metadata
                ),
            }
        )

        self.assertEqual(server.oauth_client_id, "client-123")
        self.assertEqual(server.oauth_token_endpoint, "https://auth.example.com/token")

        parts = urlsplit(result["authorization_url"])
        params = {k: v[0] for k, v in parse_qs(parts.query).items()}
        self.assertEqual(f"{parts.scheme}://{parts.netloc}{parts.path}",
                         "https://auth.example.com/authorize")
        self.assertEqual(params["response_type"], "code")
        self.assertEqual(params["client_id"], "client-123")
        self.assertEqual(params["code_challenge_method"], "S256")
        self.assertEqual(params["resource"], "https://mcp.example.com/mcp")
        self.assertEqual(params["state"], server.oauth_state)
        self.assertTrue(server.oauth_code_verifier)

    def test_begin_uses_canonical_resource_from_metadata(self):
        """
        Pipedream regression: the MCP endpoint lives at /v2 but the
        protected-resource metadata advertises the bare origin as the
        resource — sending the typed URL gets invalid_request.
        """
        metadata = {
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "registration_endpoint": "https://auth.example.com/register",
        }
        server, result = self._run_begin(
            {
                "https://mcp.example.com/.well-known/oauth-protected-resource": FakeResponse(
                    {
                        "resource": "https://mcp.example.com",
                        "authorization_servers": ["https://auth.example.com"],
                    }
                ),
                "https://auth.example.com/.well-known/oauth-authorization-server": FakeResponse(
                    metadata
                ),
            }
        )
        params = {
            k: v[0]
            for k, v in parse_qs(urlsplit(result["authorization_url"]).query).items()
        }
        self.assertEqual(params["resource"], "https://mcp.example.com")
        self.assertEqual(server.oauth_resource, "https://mcp.example.com")

    def test_begin_falls_back_to_origin_issuer(self):
        metadata = {
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "registration_endpoint": "https://auth.example.com/register",
        }
        # No protected-resource metadata anywhere; origin serves AS metadata.
        server, result = self._run_begin(
            {
                "https://mcp.example.com/.well-known/oauth-authorization-server": FakeResponse(
                    metadata
                ),
            }
        )
        self.assertIn("authorization_url", result)
        self.assertEqual(server.oauth_client_id, "client-123")

    def test_begin_rejects_non_oauth_server(self):
        dao = FakeDao([oauth_server(auth_kind="bearer")])
        with self.assertRaises(ValueError):
            McpOAuthService(dao).begin(1)


class CompleteAndRefreshTests(unittest.TestCase):
    def test_complete_exchanges_code_and_stores_tokens(self):
        dao = FakeDao(
            [
                oauth_server(
                    oauth_client_id="client-123",
                    oauth_token_endpoint="https://auth.example.com/token",
                    oauth_token_auth_method="none",
                    oauth_state="state-abc",
                    oauth_code_verifier="verifier-xyz",
                )
            ]
        )
        service = McpOAuthService(dao)
        captured = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs["data"])
            return FakeResponse(
                {
                    "access_token": "at-1",
                    "refresh_token": "rt-1",
                    "expires_in": 3600,
                }
            )

        with mock.patch("src.service.mcp_oauth_service.requests") as fake_requests:
            fake_requests.post.side_effect = fake_post
            result = service.complete("state-abc", "code-1")

        self.assertEqual(result["status"], "connected")
        self.assertEqual(captured["grant_type"], "authorization_code")
        self.assertEqual(captured["code_verifier"], "verifier-xyz")
        self.assertEqual(captured["client_id"], "client-123")

        server = dao.servers[1]
        self.assertEqual(server.oauth_access_token, "at-1")
        self.assertEqual(server.oauth_refresh_token, "rt-1")
        self.assertIsNone(server.oauth_state)
        self.assertIsNone(server.oauth_code_verifier)

    def test_complete_with_unknown_state_fails(self):
        service = McpOAuthService(FakeDao())
        with self.assertRaises(ValueError):
            service.complete("nope", "code")

    def test_ensure_fresh_returns_live_token_without_network(self):
        server = oauth_server(
            oauth_access_token="at-live",
            oauth_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        service = McpOAuthService(FakeDao([server]))
        with mock.patch("src.service.mcp_oauth_service.requests") as fake_requests:
            token = service.ensure_fresh(server)
            fake_requests.post.assert_not_called()
        self.assertEqual(token, "at-live")

    def test_ensure_fresh_refreshes_expiring_token(self):
        dao = FakeDao(
            [
                oauth_server(
                    oauth_client_id="client-123",
                    oauth_token_endpoint="https://auth.example.com/token",
                    oauth_token_auth_method="none",
                    oauth_access_token="at-old",
                    oauth_refresh_token="rt-old",
                    oauth_expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
                )
            ]
        )
        service = McpOAuthService(dao)

        def fake_post(url, **kwargs):
            self.assertEqual(kwargs["data"]["grant_type"], "refresh_token")
            self.assertEqual(kwargs["data"]["refresh_token"], "rt-old")
            return FakeResponse(
                {"access_token": "at-new", "refresh_token": "rt-new", "expires_in": 3600}
            )

        with mock.patch("src.service.mcp_oauth_service.requests") as fake_requests:
            fake_requests.post.side_effect = fake_post
            token = service.ensure_fresh(dao.servers[1])

        self.assertEqual(token, "at-new")
        self.assertEqual(dao.servers[1].oauth_refresh_token, "rt-new")

    def test_ensure_fresh_expired_and_unrefreshable_returns_none(self):
        server = oauth_server(
            oauth_access_token="at-dead",
            oauth_expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        service = McpOAuthService(FakeDao([server]))
        self.assertIsNone(service.ensure_fresh(server))


class ConnectorFilteringTests(unittest.TestCase):
    def _service(self, servers):
        service = McpServerService.__new__(McpServerService)
        service.mcp_server_dao = FakeDao(servers)
        service.oauth_service = McpOAuthService(service.mcp_server_dao)
        return service

    def test_unconnected_oauth_server_is_skipped(self):
        service = self._service(
            [
                oauth_server(id=1, name="notion"),
                McpServer(id=2, name="deepwiki", url="https://d.example",
                          auth_kind="none", enabled=True),
            ]
        )
        servers = service.connector_servers()
        self.assertEqual([s["name"] for s in servers], ["deepwiki"])

    def test_connected_oauth_server_carries_fresh_token(self):
        service = self._service(
            [
                oauth_server(
                    id=1,
                    name="notion",
                    oauth_access_token="at-live",
                    oauth_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                )
            ]
        )
        servers = service.connector_servers()
        self.assertEqual(servers[0]["authorization_token"], "at-live")


if __name__ == "__main__":
    unittest.main()
