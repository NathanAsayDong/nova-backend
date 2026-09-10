"""
A login session: one browser that has presented the right password.

The raw bearer token never touches this model. The row carries its SHA-256,
so the table alone cannot be replayed against the API.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class NovaSession(SQLModel, table=True):
    __tablename__ = "nova_sessions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    token_hash: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_agent: str | None = None
    ip: str | None = None
    revoked_at: datetime | None = None

    def is_active(self, now: datetime | None = None) -> bool:
        """Neither revoked nor expired as of `now`."""
        now = now or datetime.now(timezone.utc)
        return self.revoked_at is None and self.expires_at > now

    def public(self) -> dict:
        """What the browser is allowed to see about a session. No hash."""
        return {
            "id": str(self.id),
            "createdAt": self.created_at.isoformat(),
            "expiresAt": self.expires_at.isoformat(),
            "lastSeenAt": self.last_seen_at.isoformat(),
            "userAgent": self.user_agent,
            "ip": self.ip,
        }
