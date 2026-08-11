"""
OAuth 2.1 for remote MCP servers, per the MCP authorization spec.

The whole flow is provider-generic — no per-provider app registration:

1. Discovery: the MCP server advertises its authorization server via
   /.well-known/oauth-protected-resource (falling back to treating the
   server's own origin as the issuer), and the authorization server
   publishes its endpoints via RFC 8414 metadata.
2. Dynamic client registration (RFC 7591): we register "Nova" as an OAuth
   client at the advertised registration endpoint, so the user never has
   to create an app in the provider's console.
3. Authorization code + PKCE: begin() builds the consent URL the user
   opens in a browser; the provider redirects to our callback, and
   complete() exchanges the code for tokens.
4. Refresh: ensure_fresh() transparently refreshes near-expiry tokens so
   the agent loop always attaches a live access token.

Tokens live on the mcp_server row and never leave the backend.
"""

import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode, urlsplit

import requests

from src.dao.mcp_server_dao import McpServerDao
from src.model.mcp_server import McpServer

OAUTH_CALLBACK_PATH = "/mcp-servers/oauth/callback"

# Refresh when the access token has less than this long to live, so a token
# can't expire mid-turn between our check and Anthropic's MCP round-trip.
_REFRESH_MARGIN_SECONDS = 120
_HTTP_TIMEOUT = 20


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _path(url: str) -> str:
    return urlsplit(url).path.rstrip("/")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_expiry(value: datetime | str | None) -> datetime | None:
    """Rows read back from Supabase carry ISO strings, not datetimes."""
    if value is None or isinstance(value, datetime):
        return value if value is None or value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class McpOAuthService:
    def __init__(self, dao: McpServerDao | None = None) -> None:
        self.dao = dao or McpServerDao()

    @staticmethod
    def redirect_uri() -> str:
        base = os.getenv("MCP_OAUTH_REDIRECT_BASE", "http://localhost:8000")
        return base.rstrip("/") + OAUTH_CALLBACK_PATH

    # ---------- discovery + registration ----------

    def _get_json(self, url: str) -> dict | None:
        try:
            response = requests.get(
                url, headers={"Accept": "application/json"}, timeout=_HTTP_TIMEOUT
            )
            if response.ok:
                payload = response.json()
                if isinstance(payload, dict):
                    return payload
        except Exception:
            pass
        return None

    def _discover(self, server_url: str) -> tuple[dict[str, Any], str | None]:
        """
        Resolve the authorization server's endpoints for an MCP server URL.

        Tries the protected-resource metadata first (the spec'd path), then
        falls back to treating the MCP server's own origin as the issuer.
        Returns (authorization server metadata, canonical resource) — the
        resource identifier the metadata advertises is what MUST go in the
        OAuth `resource` parameter, and it can differ from the URL the user
        typed (e.g. Pipedream serves MCP at /v2 but the resource is the bare
        origin; sending anything else is rejected as invalid_request).
        """
        origin = _origin(server_url)
        path = _path(server_url)

        issuer = None
        canonical_resource: str | None = None
        for candidate in (
            f"{origin}/.well-known/oauth-protected-resource{path}",
            f"{origin}/.well-known/oauth-protected-resource",
        ):
            payload = self._get_json(candidate)
            if payload and payload.get("authorization_servers"):
                issuer = payload["authorization_servers"][0]
                canonical_resource = payload.get("resource")
                break
        if issuer is None:
            issuer = origin

        issuer_origin = _origin(issuer)
        issuer_path = _path(issuer)
        for candidate in (
            f"{issuer_origin}/.well-known/oauth-authorization-server{issuer_path}",
            f"{issuer_origin}/.well-known/oauth-authorization-server",
            f"{issuer_origin}/.well-known/openid-configuration",
        ):
            metadata = self._get_json(candidate)
            if (
                metadata
                and metadata.get("authorization_endpoint")
                and metadata.get("token_endpoint")
            ):
                return metadata, canonical_resource

        raise ValueError(
            "Could not discover OAuth endpoints for this MCP server — it may "
            "not support the MCP authorization spec. Use a bearer token or an "
            "aggregator (Zapier/Composio) for this one."
        )

    def _register_client(self, metadata: dict[str, Any]) -> dict[str, Any]:
        registration_endpoint = metadata.get("registration_endpoint")
        if not registration_endpoint:
            raise ValueError(
                "This authorization server does not support automatic client "
                "registration. Register an OAuth client with the provider "
                "manually, then set oauth_client_id / oauth_client_secret on "
                "the mcp_server row."
            )

        response = requests.post(
            registration_endpoint,
            json={
                "client_name": "Nova",
                "redirect_uris": [self.redirect_uri()],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
            },
            headers={"Accept": "application/json"},
            timeout=_HTTP_TIMEOUT,
        )
        if not response.ok:
            raise ValueError(
                f"OAuth client registration failed ({response.status_code}): "
                f"{response.text[:300]}"
            )
        return response.json()

    # ---------- the flow ----------

    def begin(self, server_id: int) -> dict[str, Any]:
        """
        Start the consent flow; returns the authorization URL to open.

        Discovery and client registration run once per server and are cached
        on the row, so reconnecting after token loss skips straight to the
        consent redirect.
        """
        server = self.dao.get(int(server_id))
        if server is None:
            raise ValueError(f"MCP server {server_id} does not exist.")
        if server.auth_kind != "oauth":
            raise ValueError(f"MCP server '{server.name}' is not an OAuth server.")

        columns: dict[str, Any] = {}
        if not (server.oauth_client_id and server.oauth_token_endpoint):
            metadata, canonical_resource = self._discover(server.url)
            client = self._register_client(metadata)
            columns.update(
                {
                    "oauth_authorization_endpoint": metadata["authorization_endpoint"],
                    "oauth_token_endpoint": metadata["token_endpoint"],
                    "oauth_registration_endpoint": metadata.get("registration_endpoint"),
                    "oauth_resource": canonical_resource,
                    "oauth_client_id": client["client_id"],
                    "oauth_client_secret": client.get("client_secret"),
                    "oauth_token_auth_method": client.get(
                        "token_endpoint_auth_method", "none"
                    ),
                }
            )
            server = self.dao.update(server.id, columns) or server
            columns = {}

        verifier = secrets.token_urlsafe(48)
        challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
        state = secrets.token_urlsafe(32)
        columns["oauth_code_verifier"] = verifier
        columns["oauth_state"] = state
        self.dao.update(server.id, columns)

        params = {
            "response_type": "code",
            "client_id": server.oauth_client_id,
            "redirect_uri": self.redirect_uri(),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            # RFC 8707 resource indicator — the MCP spec asks clients to bind
            # tokens to the server they're for. Must be the canonical value
            # from the protected-resource metadata, not the typed URL.
            "resource": server.oauth_resource or server.url,
        }
        if server.oauth_scope:
            params["scope"] = server.oauth_scope

        return {
            "authorization_url": (
                f"{server.oauth_authorization_endpoint}?{urlencode(params)}"
            ),
            "server": server.name,
        }

    def _token_request(self, server: McpServer, data: dict[str, Any]) -> dict[str, Any]:
        auth = None
        method = server.oauth_token_auth_method or "none"
        if method == "client_secret_basic" and server.oauth_client_secret:
            auth = (server.oauth_client_id, server.oauth_client_secret)
        else:
            data["client_id"] = server.oauth_client_id
            if method == "client_secret_post" and server.oauth_client_secret:
                data["client_secret"] = server.oauth_client_secret

        response = requests.post(
            server.oauth_token_endpoint,
            data=data,
            auth=auth,
            headers={"Accept": "application/json"},
            timeout=_HTTP_TIMEOUT,
        )
        if not response.ok:
            raise ValueError(
                f"Token request failed ({response.status_code}): {response.text[:300]}"
            )
        return response.json()

    @staticmethod
    def _token_columns(payload: dict[str, Any]) -> dict[str, Any]:
        expires_in = int(payload.get("expires_in") or 3600)
        columns: dict[str, Any] = {
            "oauth_access_token": payload["access_token"],
            "oauth_expires_at": (_now() + timedelta(seconds=expires_in)).isoformat(),
        }
        if payload.get("refresh_token"):
            columns["oauth_refresh_token"] = payload["refresh_token"]
        return columns

    def complete(self, state: str, code: str) -> dict[str, Any]:
        """Finish the consent flow: exchange the code and store tokens."""
        server = self.dao.get_by_oauth_state(state)
        if server is None:
            raise ValueError("Unknown or expired OAuth state — restart the connect flow.")

        payload = self._token_request(
            server,
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri(),
                "code_verifier": server.oauth_code_verifier,
                "resource": server.oauth_resource or server.url,
            },
        )

        columns = self._token_columns(payload)
        columns["oauth_state"] = None
        columns["oauth_code_verifier"] = None
        self.dao.update(server.id, columns)
        return {"status": "connected", "server": server.name}

    def ensure_fresh(self, server: McpServer) -> str | None:
        """
        A live access token for the request being built, or None if this
        server can't participate this turn (never connected, or refresh
        failed on an expired token).
        """
        if not server.oauth_access_token:
            return None

        expires_at = _parse_expiry(server.oauth_expires_at)
        expired = expires_at is not None and expires_at <= _now()
        expiring = expires_at is not None and expires_at <= _now() + timedelta(
            seconds=_REFRESH_MARGIN_SECONDS
        )

        if not expiring:
            return server.oauth_access_token
        if not server.oauth_refresh_token:
            return None if expired else server.oauth_access_token

        try:
            payload = self._token_request(
                server,
                {
                    "grant_type": "refresh_token",
                    "refresh_token": server.oauth_refresh_token,
                    "resource": server.oauth_resource or server.url,
                },
            )
            self.dao.update(server.id, self._token_columns(payload))
            return payload["access_token"]
        except Exception as exc:
            print(f"OAuth refresh failed for MCP server '{server.name}': {exc}")
            return None if expired else server.oauth_access_token
