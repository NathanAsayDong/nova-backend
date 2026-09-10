"""
Coverage for login: credential checking, session lifetime, and the lockout.

No database. A dict-backed fake stands in for NovaSessionDao, and the two env
vars are set per test, because the interesting behaviour — fail closed when
unconfigured, lock after repeated failures, slide the expiry on use — is all
in the service.
"""

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from src.dao.nova_session_dao import row_to_session
from src.model.nova_session import NovaSession
from src.service import auth_service as module
from src.service.auth_service import (
    AuthNotConfigured,
    AuthService,
    BadCredentials,
    LockedOut,
    LOCKOUT_GLOBAL,
    LOCKOUT_PER_IP,
    PASSWORD_ENV,
    TOUCH_INTERVAL_SECONDS,
    USERNAME_ENV,
)


class FakeDao:
    def __init__(self):
        self.rows: dict[str, NovaSession] = {}
        self.touches = 0

    def create(self, session):
        self.rows[session.token_hash] = session
        return session

    def get_by_token_hash(self, token_hash):
        return self.rows.get(token_hash)

    def touch(self, token_hash, last_seen_at, expires_at):
        self.touches += 1
        row = self.rows[token_hash]
        row.last_seen_at = last_seen_at
        row.expires_at = expires_at

    def revoke(self, token_hash):
        row = self.rows.get(token_hash)
        if row and row.revoked_at is None:
            row.revoked_at = datetime.now(timezone.utc)

    def revoke_all(self):
        live = [row for row in self.rows.values() if row.revoked_at is None]
        for row in live:
            row.revoked_at = datetime.now(timezone.utc)
        return len(live)

    def list_active(self):
        now = datetime.now(timezone.utc)
        return [row for row in self.rows.values() if row.is_active(now)]

    def purge_expired(self):
        return 0


class AuthServiceTestCase(unittest.TestCase):
    def setUp(self):
        AuthService.reset_state()
        self.dao = FakeDao()
        self.service = AuthService(dao=self.dao)
        self.env = patch.dict(os.environ, {USERNAME_ENV: "nate", PASSWORD_ENV: "hunter2"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        AuthService.reset_state()


class RowConversionTests(unittest.TestCase):
    """
    Supabase hands timestamps back as ISO strings and SQLModel table models do
    not validate, so the DAO has to parse them itself. The first real login
    500'd on exactly this: session.public() called .isoformat() on a str.
    """

    def test_strings_become_aware_datetimes(self):
        session = row_to_session(
            {
                "id": "0b1f9c8e-0d8a-4a2b-9a5e-3b2e6c1d7f10",
                "token_hash": "abc",
                "created_at": "2026-09-10T17:05:43.123456+00:00",
                "expires_at": "2026-10-10T17:05:43.123456Z",
                "last_seen_at": "2026-09-10T17:05:43.123456",
                "user_agent": None,
                "ip": None,
                "revoked_at": None,
            }
        )
        for value in (session.created_at, session.expires_at, session.last_seen_at):
            self.assertIsInstance(value, datetime)
            self.assertIsNotNone(value.tzinfo)
        self.assertIsNone(session.revoked_at)
        # The things that broke: comparison and rendering.
        self.assertTrue(session.is_active(datetime(2026, 9, 11, tzinfo=timezone.utc)))
        self.assertEqual(session.public()["expiresAt"], "2026-10-10T17:05:43.123456+00:00")

    def test_real_datetimes_pass_through(self):
        now = datetime.now(timezone.utc)
        session = row_to_session(
            {"token_hash": "abc", "created_at": now, "expires_at": now, "last_seen_at": now}
        )
        self.assertEqual(session.created_at, now)


class ConfigurationTests(AuthServiceTestCase):
    def test_unconfigured_refuses_login(self):
        with patch.dict(os.environ, {USERNAME_ENV: "", PASSWORD_ENV: ""}):
            self.assertFalse(AuthService.configured())
            with self.assertRaises(AuthNotConfigured):
                self.service.login("nate", "hunter2")

    def test_unconfigured_refuses_every_token(self):
        token, _ = self.service.login("nate", "hunter2")
        with patch.dict(os.environ, {PASSWORD_ENV: ""}):
            self.assertIsNone(self.service.authenticate(token))

    def test_lifetime_defaults_and_clamps(self):
        self.assertEqual(AuthService.session_lifetime(), timedelta(days=30))
        with patch.dict(os.environ, {"NOVA_SESSION_DAYS": "7"}):
            self.assertEqual(AuthService.session_lifetime(), timedelta(days=7))
        with patch.dict(os.environ, {"NOVA_SESSION_DAYS": "0"}):
            self.assertEqual(AuthService.session_lifetime(), timedelta(days=1))
        with patch.dict(os.environ, {"NOVA_SESSION_DAYS": "lots"}):
            self.assertEqual(AuthService.session_lifetime(), timedelta(days=30))


class LoginTests(AuthServiceTestCase):
    def test_right_credentials_open_a_session(self):
        token, session = self.service.login("nate", "hunter2", ip="1.2.3.4", user_agent="UA")
        self.assertTrue(token)
        self.assertNotIn(token, self.dao.rows, "the raw token must not be stored")
        self.assertEqual(session.ip, "1.2.3.4")
        self.assertEqual(session.user_agent, "UA")
        self.assertIs(self.service.authenticate(token), session)

    def test_username_is_trimmed_password_is_not(self):
        self.service.login("  nate ", "hunter2")
        with self.assertRaises(BadCredentials):
            self.service.login("nate", " hunter2")

    def test_wrong_credentials_fail(self):
        with self.assertRaises(BadCredentials):
            self.service.login("nate", "wrong")
        with self.assertRaises(BadCredentials):
            self.service.login("someone", "hunter2")
        self.assertEqual(self.dao.rows, {})


class LockoutTests(AuthServiceTestCase):
    def test_per_ip_lockout_after_repeated_failures(self):
        for _ in range(LOCKOUT_PER_IP):
            with self.assertRaises(BadCredentials):
                self.service.login("nate", "wrong", ip="9.9.9.9")
        with self.assertRaises(LockedOut) as caught:
            self.service.login("nate", "hunter2", ip="9.9.9.9")
        self.assertGreater(caught.exception.retry_after, 0)
        # A different address is unaffected.
        self.service.login("nate", "hunter2", ip="8.8.8.8")

    def test_global_lockout_across_addresses(self):
        for index in range(LOCKOUT_GLOBAL):
            with self.assertRaises(BadCredentials):
                self.service.login("nate", "wrong", ip=f"10.0.0.{index}")
        with self.assertRaises(LockedOut):
            self.service.login("nate", "hunter2", ip="fresh")

    def test_success_clears_that_address(self):
        for _ in range(LOCKOUT_PER_IP - 1):
            with self.assertRaises(BadCredentials):
                self.service.login("nate", "wrong", ip="9.9.9.9")
        self.service.login("nate", "hunter2", ip="9.9.9.9")
        for _ in range(LOCKOUT_PER_IP - 1):
            with self.assertRaises(BadCredentials):
                self.service.login("nate", "wrong", ip="9.9.9.9")
        # Still one short of the threshold: the earlier failures were forgotten.
        self.service.login("nate", "hunter2", ip="9.9.9.9")

    def test_lockout_expires(self):
        with patch.object(module.time, "monotonic", return_value=1000.0):
            for _ in range(LOCKOUT_PER_IP):
                with self.assertRaises(BadCredentials):
                    self.service.login("nate", "wrong", ip="9.9.9.9")
        with patch.object(
            module.time, "monotonic", return_value=1000.0 + module.LOCKOUT_SECONDS + 1
        ):
            self.service.login("nate", "hunter2", ip="9.9.9.9")


class AuthenticateTests(AuthServiceTestCase):
    def test_unknown_token_is_refused(self):
        self.assertIsNone(self.service.authenticate("nope"))
        self.assertIsNone(self.service.authenticate(""))
        self.assertIsNone(self.service.authenticate(None))

    def test_expired_session_is_refused(self):
        token, session = self.service.login("nate", "hunter2")
        session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.assertIsNone(self.service.authenticate(token))

    def test_revoked_session_is_refused(self):
        token, session = self.service.login("nate", "hunter2")
        self.service.logout(session.token_hash)
        self.assertIsNone(self.service.authenticate(token))

    def test_expiry_slides_on_use_but_not_every_request(self):
        token, session = self.service.login("nate", "hunter2")
        self.service.authenticate(token)
        self.assertEqual(self.dao.touches, 0, "a fresh session is not rewritten")

        # Age the row past the touch interval and bypass the cache.
        AuthService.reset_state()
        old = datetime.now(timezone.utc) - timedelta(seconds=TOUCH_INTERVAL_SECONDS + 5)
        session.last_seen_at = old
        session.expires_at = old + timedelta(days=30)
        before = session.expires_at

        self.service.authenticate(token)
        self.assertEqual(self.dao.touches, 1)
        self.assertGreater(session.expires_at, before)

    def test_cache_saves_lookups_and_sign_out_all_clears_it(self):
        token, _ = self.service.login("nate", "hunter2")
        with patch.object(self.dao, "get_by_token_hash", wraps=self.dao.get_by_token_hash) as spy:
            self.service.authenticate(token)
            self.service.authenticate(token)
            self.assertEqual(spy.call_count, 0, "login primed the cache")

        self.assertEqual(self.service.logout_all(), 1)
        self.assertIsNone(self.service.authenticate(token))

    def test_list_sessions_omits_revoked(self):
        token_a, session_a = self.service.login("nate", "hunter2")
        token_b, _ = self.service.login("nate", "hunter2")
        self.service.logout(session_a.token_hash)
        active = self.service.list_sessions()
        self.assertEqual(len(active), 1)
        self.assertNotEqual(active[0].token_hash, session_a.token_hash)

    def test_public_view_has_no_hash(self):
        _, session = self.service.login("nate", "hunter2")
        view = session.public()
        self.assertNotIn("token_hash", view)
        self.assertNotIn("tokenHash", view)
        self.assertIn("expiresAt", view)


if __name__ == "__main__":
    unittest.main()
