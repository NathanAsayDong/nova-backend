"""
Login for the one user Nova has.

The username and password live in the API's environment (NOVA_AUTH_USERNAME,
NOVA_AUTH_PASSWORD) and never in the database: there is exactly one account,
it changes by editing .env and restarting, and a secret that lives in one
place has one place to leak from. What the database holds is the set of
sessions that password has opened — the part that has to survive a restart so
a phone does not get logged out every time the tower reboots.

A session is a random bearer token. The browser keeps the token; the table
keeps its SHA-256, so the table alone cannot be replayed. Sessions slide: use
within the window refreshes the expiry, so a device in daily use stays signed
in for as long as it is in daily use.

The login endpoint is public on the internet, so it is rate-limited: five
failures from one address, or twenty from anywhere, lock the endpoint for
fifteen minutes. The counters are in memory — the API is one long-lived
process on one machine, and a restart clearing them costs nothing.

Missing credentials fail closed. If the two env vars are not set, nothing can
log in and every gated route refuses, rather than the API quietly opening up.
"""

import hashlib
import hmac
import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

from src.dao.nova_session_dao import NovaSessionDao
from src.model.nova_session import NovaSession

USERNAME_ENV = "NOVA_AUTH_USERNAME"
PASSWORD_ENV = "NOVA_AUTH_PASSWORD"
SESSION_DAYS_ENV = "NOVA_SESSION_DAYS"

_DEFAULT_SESSION_DAYS = 30

# Brute-force lockout. Per-address covers the ordinary case; the global cap
# covers an attacker rotating addresses, at the cost that they can lock the
# real user out too — for a single-user app that is the right trade.
LOCKOUT_PER_IP = 5
LOCKOUT_GLOBAL = 20
LOCKOUT_SECONDS = 15 * 60

# How often a busy session's expiry is actually rewritten. Every request
# extending it would be a database write per API call for nothing; once every
# fifteen minutes slides it just as well.
TOUCH_INTERVAL_SECONDS = 15 * 60

# Validated sessions are remembered briefly so a burst of requests (a page
# load fans out to half a dozen) costs one lookup, not six. Sign-out clears it.
CACHE_TTL_SECONDS = 60


class AuthNotConfigured(Exception):
    """NOVA_AUTH_USERNAME or NOVA_AUTH_PASSWORD is not set."""


class BadCredentials(Exception):
    """Wrong username or password."""


class LockedOut(Exception):
    """Too many recent failures; try again after `retry_after` seconds."""

    def __init__(self, retry_after: int):
        super().__init__(f"Too many failed attempts. Try again in {retry_after} seconds.")
        self.retry_after = retry_after


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AuthService:
    # Class-level on purpose, same reason as SettingsService: the controller
    # and the middleware each hold an instance, and both have to see the same
    # failure counters and the same cache.
    _failures: dict[str, list[float]] = {}
    _cache: dict[str, tuple[NovaSession, float]] = {}
    _lock = threading.Lock()

    def __init__(self, dao: NovaSessionDao | None = None):
        # Built lazily so importing this module (and the middleware) does not
        # need Supabase credentials — tests inject a fake instead.
        self._dao = dao

    @property
    def dao(self) -> NovaSessionDao:
        if self._dao is None:
            self._dao = NovaSessionDao()
        return self._dao

    # ---------- configuration ----------

    @staticmethod
    def configured() -> bool:
        return bool((os.getenv(USERNAME_ENV) or "").strip()) and bool(
            os.getenv(PASSWORD_ENV) or ""
        )

    @staticmethod
    def session_lifetime() -> timedelta:
        raw = (os.getenv(SESSION_DAYS_ENV) or "").strip()
        try:
            days = int(raw) if raw else _DEFAULT_SESSION_DAYS
        except ValueError:
            days = _DEFAULT_SESSION_DAYS
        return timedelta(days=max(1, days))

    # ---------- login ----------

    def login(
        self,
        username: str,
        password: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, NovaSession]:
        """
        Check the credentials and open a session.

        Returns the raw token (the only time it exists server-side) and the
        stored row. Raises AuthNotConfigured, LockedOut, or BadCredentials.
        """
        if not self.configured():
            raise AuthNotConfigured()

        key = ip or "unknown"
        retry_after = self._locked_for(key)
        if retry_after:
            raise LockedOut(retry_after)

        expected_user = (os.getenv(USERNAME_ENV) or "").strip()
        expected_pass = os.getenv(PASSWORD_ENV) or ""
        # Both comparisons always run (bitwise and, not boolean), so the time
        # taken does not say which half was wrong.
        user_ok = hmac.compare_digest(
            (username or "").strip().encode("utf-8"), expected_user.encode("utf-8")
        )
        pass_ok = hmac.compare_digest(
            (password or "").encode("utf-8"), expected_pass.encode("utf-8")
        )
        if not (user_ok & pass_ok):
            self._record_failure(key)
            raise BadCredentials()

        self._clear_failures(key)

        token = secrets.token_urlsafe(32)
        now = _now()
        session = NovaSession(
            token_hash=_hash_token(token),
            created_at=now,
            expires_at=now + self.session_lifetime(),
            last_seen_at=now,
            user_agent=(user_agent or "")[:512] or None,
            ip=ip,
        )
        stored = self.dao.create(session)
        with self._lock:
            self._cache[stored.token_hash] = (stored, time.monotonic())
        return token, stored

    # ---------- per-request check ----------

    def authenticate(self, token: str | None) -> NovaSession | None:
        """The live session this token names, or None."""
        if not token or not self.configured():
            return None

        token_hash = _hash_token(token)
        now = _now()

        with self._lock:
            cached = self._cache.get(token_hash)
        if cached:
            session, cached_at = cached
            if time.monotonic() - cached_at < CACHE_TTL_SECONDS and session.is_active(now):
                return session

        session = self.dao.get_by_token_hash(token_hash)
        if session is None or not session.is_active(now):
            with self._lock:
                self._cache.pop(token_hash, None)
            return None

        if (now - session.last_seen_at).total_seconds() >= TOUCH_INTERVAL_SECONDS:
            session.last_seen_at = now
            session.expires_at = now + self.session_lifetime()
            try:
                self.dao.touch(token_hash, session.last_seen_at, session.expires_at)
            except Exception as exc:
                # Sliding the expiry is a nicety; refusing a valid session
                # because the write failed would not be.
                print(f"Could not refresh session expiry: {exc}")

        with self._lock:
            self._cache[token_hash] = (session, time.monotonic())
        return session

    # ---------- sign out ----------

    def logout(self, token_hash: str) -> None:
        self.dao.revoke(token_hash)
        with self._lock:
            self._cache.pop(token_hash, None)

    def logout_all(self) -> int:
        count = self.dao.revoke_all()
        with self._lock:
            self._cache.clear()
        return count

    def list_sessions(self) -> list[NovaSession]:
        return self.dao.list_active()

    def purge_expired(self) -> int:
        return self.dao.purge_expired()

    # ---------- lockout bookkeeping ----------

    @classmethod
    def _prune(cls, now: float) -> None:
        cutoff = now - LOCKOUT_SECONDS
        for key in list(cls._failures):
            recent = [stamp for stamp in cls._failures[key] if stamp > cutoff]
            if recent:
                cls._failures[key] = recent
            else:
                del cls._failures[key]

    @classmethod
    def _locked_for(cls, key: str) -> int:
        """Seconds until this address may try again, or 0."""
        now = time.monotonic()
        with cls._lock:
            cls._prune(now)
            mine = cls._failures.get(key, [])
            everyone = [stamp for stamps in cls._failures.values() for stamp in stamps]
            if len(mine) >= LOCKOUT_PER_IP:
                oldest = min(mine)
            elif len(everyone) >= LOCKOUT_GLOBAL:
                oldest = min(everyone)
            else:
                return 0
            return max(1, int(oldest + LOCKOUT_SECONDS - now))

    @classmethod
    def _record_failure(cls, key: str) -> None:
        with cls._lock:
            cls._failures.setdefault(key, []).append(time.monotonic())

    @classmethod
    def _clear_failures(cls, key: str) -> None:
        with cls._lock:
            cls._failures.pop(key, None)

    @classmethod
    def reset_state(cls) -> None:
        """Forget every counter and cached session. For tests."""
        with cls._lock:
            cls._failures.clear()
            cls._cache.clear()
