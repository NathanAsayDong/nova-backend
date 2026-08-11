"""
MCP server registry: remote tool servers Nova reaches through Claude's
MCP connector.

Anthropic executes the MCP round-trip server-side — we only declare the
servers on the request (see ClaudeService) and handle the resulting
mcp_tool_use / mcp_tool_result blocks in the agent loop. This service owns
the registry table so servers can be added or toggled at runtime without a
redeploy, and it is the only layer that ever sees auth tokens: everything
returned to the client masks them down to a has_token flag.
"""

import re

from src.dao.mcp_server_dao import McpServerDao
from src.model.mcp_server import McpServer
from src.service.mcp_oauth_service import McpOAuthService

# Server names become tool-name prefixes on the Anthropic side; keep them
# short and unambiguous.
_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

_AUTH_KINDS = {"none", "bearer", "oauth"}


class McpServerService:
    def __init__(self) -> None:
        self.mcp_server_dao = McpServerDao()
        self.oauth_service = McpOAuthService(self.mcp_server_dao)

    @staticmethod
    def _to_dict(server: McpServer) -> dict:
        """Client-safe view. Tokens and OAuth secrets never leave the backend."""
        expires_at = server.oauth_expires_at
        return {
            "id": server.id,
            "name": server.name,
            "url": server.url,
            "enabled": server.enabled,
            "auth_kind": server.auth_kind or "none",
            "has_token": bool(server.auth_token),
            "oauth_connected": bool(server.oauth_access_token),
            "oauth_expires_at": (
                expires_at.isoformat()
                if hasattr(expires_at, "isoformat")
                else expires_at
            ),
            "created_at": (
                server.created_at.isoformat()
                if hasattr(server.created_at, "isoformat")
                else server.created_at
            ),
        }

    @staticmethod
    def _validate_name(name: str) -> str:
        name = (name or "").strip()
        if not _NAME_PATTERN.match(name):
            raise ValueError(
                "Server name must be 1-64 characters of letters, digits, "
                "hyphens, or underscores (it becomes the tool prefix)."
            )
        return name

    @staticmethod
    def _validate_url(url: str) -> str:
        url = (url or "").strip()
        if not url.startswith(("http://", "https://")):
            raise ValueError("Server URL must start with http:// or https://.")
        return url

    def list_servers(self) -> list[dict]:
        return [self._to_dict(server) for server in self.mcp_server_dao.get_all()]

    def create_server(
        self,
        name: str,
        url: str,
        auth_token: str | None = None,
        enabled: bool = True,
        auth_kind: str | None = None,
    ) -> dict:
        name = self._validate_name(name)
        url = self._validate_url(url)
        if self.mcp_server_dao.get_by_name(name) is not None:
            raise ValueError(f"An MCP server named '{name}' already exists.")

        auth_token = (auth_token or "").strip() or None
        if auth_kind is None:
            auth_kind = "bearer" if auth_token else "none"
        auth_kind = str(auth_kind).strip().lower()
        if auth_kind not in _AUTH_KINDS:
            raise ValueError(f"auth_kind must be one of {sorted(_AUTH_KINDS)}.")
        if auth_kind == "oauth":
            # Tokens come from the connect flow, never typed in by hand.
            auth_token = None

        created = self.mcp_server_dao.create(
            McpServer(
                name=name,
                url=url,
                auth_kind=auth_kind,
                auth_token=auth_token,
                enabled=bool(enabled),
            )
        )
        return self._to_dict(created)

    def update_server(
        self,
        server_id: int,
        name: str | None = None,
        url: str | None = None,
        auth_token: str | None = None,
        enabled: bool | None = None,
    ) -> dict:
        """Partial update; omitted fields are left unchanged."""
        server = self.mcp_server_dao.get(int(server_id))
        if server is None:
            raise ValueError(f"MCP server {server_id} does not exist.")

        columns: dict = {}
        if name is not None:
            name = self._validate_name(name)
            existing = self.mcp_server_dao.get_by_name(name)
            if existing is not None and existing.id != server.id:
                raise ValueError(f"An MCP server named '{name}' already exists.")
            columns["name"] = name
        if url is not None:
            columns["url"] = self._validate_url(url)
        if auth_token is not None:
            # Empty string means "clear the token"; anything else replaces it.
            columns["auth_token"] = auth_token.strip() or None
        if enabled is not None:
            columns["enabled"] = bool(enabled)

        if not columns:
            return self._to_dict(server)

        updated = self.mcp_server_dao.update(server.id, columns)
        if updated is None:
            raise ValueError(f"MCP server {server_id} could not be updated.")
        return self._to_dict(updated)

    def delete_server(self, server_id: int) -> dict:
        server = self.mcp_server_dao.get(int(server_id))
        if server is None:
            raise ValueError(f"MCP server {server_id} does not exist.")
        self.mcp_server_dao.delete(server.id)
        return {"status": "deleted", "server": self._to_dict(server)}

    def connector_servers(self) -> list[dict]:
        """
        Enabled servers in the shape ClaudeService attaches to requests:
        {name, url, authorization_token?}. Sorted by name so the request's
        tool list (which the toolset entries join) stays byte-stable for
        prompt caching.

        OAuth servers get a freshly-refreshed access token; ones that were
        never connected (or whose refresh failed on an expired token) are
        skipped for the turn rather than sent without credentials.
        """
        servers = []
        for server in self.mcp_server_dao.get_enabled():
            entry: dict = {"name": server.name, "url": server.url}
            if server.auth_kind == "oauth":
                token = self.oauth_service.ensure_fresh(server)
                if not token:
                    continue
                entry["authorization_token"] = token
            elif server.auth_token:
                entry["authorization_token"] = server.auth_token
            servers.append(entry)
        servers.sort(key=lambda entry: entry["name"])
        return servers
