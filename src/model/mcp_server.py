from datetime import datetime, timezone

from sqlmodel import SQLModel, Field


class McpServer(SQLModel, table=True):
    """A remote MCP server Nova can use through Claude's MCP connector."""

    __tablename__ = "mcp_server"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    url: str = Field(default="")

    # How the server authenticates: 'none', 'bearer' (static token in
    # auth_token), or 'oauth' (tokens below, obtained via the connect flow).
    auth_kind: str = Field(default="none")
    auth_token: str | None = Field(default=None)

    # OAuth 2.1 state, populated by McpOAuthService. The client is registered
    # dynamically (RFC 7591) against the server's advertised endpoints, then
    # tokens are minted via authorization-code + PKCE and refreshed as needed.
    oauth_client_id: str | None = Field(default=None)
    oauth_client_secret: str | None = Field(default=None)
    oauth_token_auth_method: str | None = Field(default=None)
    oauth_authorization_endpoint: str | None = Field(default=None)
    oauth_token_endpoint: str | None = Field(default=None)
    oauth_registration_endpoint: str | None = Field(default=None)
    oauth_scope: str | None = Field(default=None)
    # Canonical resource identifier advertised by the server's
    # protected-resource metadata (RFC 9728). May differ from the URL the
    # user typed — e.g. Pipedream serves MCP at /v2 but its authorization
    # server only accepts the bare origin as the resource.
    oauth_resource: str | None = Field(default=None)
    oauth_access_token: str | None = Field(default=None)
    oauth_refresh_token: str | None = Field(default=None)
    oauth_expires_at: datetime | None = Field(default=None)
    # In-flight authorization handshake (cleared on completion).
    oauth_state: str | None = Field(default=None)
    oauth_code_verifier: str | None = Field(default=None)

    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_payload(self) -> dict:
        return self.model_dump(
            exclude={"id"},
            exclude_none=True,
            mode="json",
        )
