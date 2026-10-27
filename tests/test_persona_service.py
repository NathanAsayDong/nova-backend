"""
Coverage for PersonaService: the persona now lives in the database so an
agent tool can change it live, but it must never be the reason a
conversation fails to start. These tests pin down loading, the fallback to
the shipped markdown file, the short-TTL cache and its invalidation on
write, versioning, and rollback — all against a FakePersonaDao, never a
real database.
"""

import time
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from prompting.prompt_enums import PromptEnums
from src.model.persona_prompt import PersonaPrompt
from src.service.persona_service import (
    CACHE_TTL_SECONDS,
    MAX_CONTENT_LENGTH,
    MIN_CONTENT_LENGTH,
    PersonaService,
    PersonaValidationError,
)

_FILE_CONTENT = PromptEnums.NOVA_PERSONA_PROMPT.load()
_LONG_ENOUGH = "x" * (MIN_CONTENT_LENGTH + 10)


class FakePersonaDao:
    """
    In-memory stand-in for PersonaPromptDao, emulating the same invariant the
    real create_persona_version/activate_persona_version Postgres functions
    enforce: exactly one active row per name, versions increment per name.
    """

    def __init__(self, rows=() ):
        self.rows: dict[int, PersonaPrompt] = {row.id: row for row in rows}
        self._next_id = max(self.rows, default=0) + 1
        self.get_active_calls = 0

    def get_active(self, name: str = "nova"):
        self.get_active_calls += 1
        for row in self.rows.values():
            if row.name == name and row.is_active:
                return row
        return None

    def get_by_version(self, version: int, name: str = "nova"):
        for row in self.rows.values():
            if row.name == name and row.version == version:
                return row
        return None

    def get(self, id: int):
        return self.rows.get(id)

    def list_versions(self, name: str = "nova"):
        return sorted(
            (row for row in self.rows.values() if row.name == name),
            key=lambda row: row.version,
            reverse=True,
        )

    def create_version(self, content, name="nova", created_by=None, notes=None):
        existing = [row.version for row in self.rows.values() if row.name == name]
        next_version = (max(existing) + 1) if existing else 1
        for row in self.rows.values():
            if row.name == name and row.is_active:
                row.is_active = False
        created = PersonaPrompt(
            id=self._next_id,
            name=name,
            content=content,
            version=next_version,
            is_active=True,
            created_by=created_by,
            notes=notes,
            created_at=datetime.now(timezone.utc),
        )
        self.rows[created.id] = created
        self._next_id += 1
        return created

    def activate_version(self, id: int):
        target = self.rows.get(id)
        if target is None:
            return None
        for row in self.rows.values():
            if row.name == target.name and row.is_active:
                row.is_active = False
        target.is_active = True
        return target


def seed_row(id=1, name="nova", version=1, content="Seeded persona content.", is_active=True):
    return PersonaPrompt(
        id=id,
        name=name,
        content=content,
        version=version,
        is_active=is_active,
        created_by="migration",
        notes="seed",
        created_at=datetime.now(timezone.utc),
    )


def build_service(dao=None) -> PersonaService:
    service = PersonaService.__new__(PersonaService)
    service._dao = dao
    return service


class _ResetsSharedCache:
    """The persona cache lives on the class, so tests must not leak into each other."""

    def setUp(self):
        self._saved = (dict(PersonaService._cache), dict(PersonaService._cached_at))
        PersonaService._cache = {}
        PersonaService._cached_at = {}

    def tearDown(self):
        cache, cached_at = self._saved
        PersonaService._cache = cache
        PersonaService._cached_at = cached_at


class LoadingTests(_ResetsSharedCache, unittest.TestCase):
    def test_loads_active_content_from_the_database(self):
        dao = FakePersonaDao([seed_row(content="DB persona text.")])
        service = build_service(dao)

        self.assertEqual(service.get_active_content(), "DB persona text.")

    def test_active_version_is_reported(self):
        dao = FakePersonaDao([seed_row(version=3)])
        service = build_service(dao)

        self.assertEqual(service.get_active_version(), 3)

    def test_no_rows_at_all_reports_no_version(self):
        service = build_service(FakePersonaDao([]))
        self.assertIsNone(service.get_active_version())


class FallbackTests(_ResetsSharedCache, unittest.TestCase):
    def test_falls_back_to_file_when_store_is_unavailable(self):
        """Mirrors a missing SUPABASE_URL or an unreachable database."""
        service = build_service(None)
        with patch.object(PersonaService, "_get_dao", return_value=None):
            self.assertEqual(service.get_active_content(), _FILE_CONTENT)

    def test_falls_back_to_file_when_there_is_no_active_row(self):
        dao = FakePersonaDao([seed_row(is_active=False)])
        service = build_service(dao)

        self.assertEqual(service.get_active_content(), _FILE_CONTENT)

    def test_a_blank_active_row_falls_back_to_file_too(self):
        """An active row with empty content must not blank out the persona."""
        dao = FakePersonaDao([seed_row(content="   ")])
        service = build_service(dao)

        self.assertEqual(service.get_active_content(), _FILE_CONTENT)

    def test_a_database_error_falls_back_to_file_when_nothing_is_cached(self):
        service = build_service(None)
        with patch.object(PersonaService, "_get_dao") as get_dao:
            get_dao.return_value.get_active.side_effect = RuntimeError("network down")
            self.assertEqual(service.get_active_content(), _FILE_CONTENT)

    def test_a_stale_cache_beats_the_fallback(self):
        """Same contract as SettingsService's model list: serve stale over nothing."""
        dao = FakePersonaDao([seed_row(content="Cached persona.")])
        service = build_service(dao)
        service.get_active_content()  # warms the cache

        PersonaService._cached_at["nova"] -= CACHE_TTL_SECONDS + 1
        with patch.object(PersonaService, "_get_dao", return_value=None):
            self.assertEqual(service.get_active_content(), "Cached persona.")


class CachingTests(_ResetsSharedCache, unittest.TestCase):
    def test_the_active_row_is_fetched_once_within_the_ttl(self):
        dao = FakePersonaDao([seed_row()])
        service = build_service(dao)

        service.get_active_content()
        service.get_active_content()
        service.get_active_content()

        self.assertEqual(dao.get_active_calls, 1)

    def test_an_expired_cache_is_refetched(self):
        dao = FakePersonaDao([seed_row()])
        service = build_service(dao)

        service.get_active_content()
        PersonaService._cached_at["nova"] -= CACHE_TTL_SECONDS + 1
        service.get_active_content()

        self.assertEqual(dao.get_active_calls, 2)

    def test_refresh_bypasses_the_cache(self):
        dao = FakePersonaDao([seed_row()])
        service = build_service(dao)

        service.get_active_prompt()
        service.get_active_prompt(refresh=True)

        self.assertEqual(dao.get_active_calls, 2)

    def test_a_failed_fetch_is_retried_next_call_not_frozen(self):
        dao = FakePersonaDao([seed_row()])
        service = build_service(dao)
        service.get_active_content()
        PersonaService._cached_at["nova"] -= CACHE_TTL_SECONDS + 1

        with patch.object(PersonaService, "_get_dao") as get_dao:
            get_dao.return_value.get_active.side_effect = RuntimeError("down")
            service.get_active_content()
            service.get_active_content()
            self.assertEqual(get_dao.return_value.get_active.call_count, 2)

    def test_invalidate_cache_forces_a_refetch(self):
        dao = FakePersonaDao([seed_row()])
        service = build_service(dao)
        service.get_active_content()

        PersonaService.invalidate_cache()
        service.get_active_content()

        self.assertEqual(dao.get_active_calls, 2)


class GuardrailTests(_ResetsSharedCache, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.service = build_service(FakePersonaDao([seed_row()]))

    def test_empty_content_is_rejected(self):
        with self.assertRaises(PersonaValidationError):
            self.service.update_persona(content="", change_note="note")

    def test_whitespace_only_content_is_rejected(self):
        with self.assertRaises(PersonaValidationError):
            self.service.update_persona(content="   ", change_note="note")

    def test_content_below_the_minimum_length_is_rejected(self):
        with self.assertRaises(PersonaValidationError):
            self.service.update_persona(content="too short", change_note="note")

    def test_content_over_the_maximum_length_is_rejected(self):
        with self.assertRaises(PersonaValidationError):
            self.service.update_persona(
                content="x" * (MAX_CONTENT_LENGTH + 1), change_note="note"
            )

    def test_a_missing_change_note_is_rejected(self):
        with self.assertRaises(PersonaValidationError):
            self.service.update_persona(content=_LONG_ENOUGH, change_note="")

    def test_a_blank_change_note_is_rejected(self):
        with self.assertRaises(PersonaValidationError):
            self.service.update_persona(content=_LONG_ENOUGH, change_note="   ")

    def test_a_valid_update_is_accepted(self):
        created = self.service.update_persona(
            content=_LONG_ENOUGH, change_note="Testing a valid update."
        )
        self.assertEqual(created.content, _LONG_ENOUGH)

    def test_update_with_no_persona_store_raises_rather_than_pretending_to_save(self):
        service = build_service(None)
        with patch.object(PersonaService, "_get_dao", return_value=None):
            with self.assertRaises(PersonaValidationError):
                service.update_persona(content=_LONG_ENOUGH, change_note="note")


class VersioningAndRollbackTests(_ResetsSharedCache, unittest.TestCase):
    def test_update_creates_a_new_incrementing_version_and_deactivates_the_old_one(self):
        dao = FakePersonaDao([seed_row(version=1, content="v1")])
        service = build_service(dao)

        created = service.update_persona(content=_LONG_ENOUGH, change_note="v2")

        self.assertEqual(created.version, 2)
        self.assertTrue(created.is_active)
        old = dao.get_by_version(1)
        self.assertFalse(old.is_active)

    def test_only_one_row_is_ever_active(self):
        dao = FakePersonaDao([seed_row(version=1)])
        service = build_service(dao)

        service.update_persona(content=_LONG_ENOUGH, change_note="v2")
        service.update_persona(content=_LONG_ENOUGH + "!", change_note="v3")

        active = [row for row in dao.rows.values() if row.is_active]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].version, 3)

    def test_update_invalidates_the_cache_immediately(self):
        dao = FakePersonaDao([seed_row(content="old")])
        service = build_service(dao)
        service.get_active_content()  # warm the cache with "old"

        service.update_persona(content=_LONG_ENOUGH, change_note="swap it")

        # No TTL wait needed: the write updates the cache directly.
        self.assertEqual(service.get_active_content(), _LONG_ENOUGH)
        self.assertEqual(dao.get_active_calls, 1)  # only the initial warm-up

    def test_list_versions_is_newest_first(self):
        dao = FakePersonaDao([seed_row(version=1)])
        service = build_service(dao)
        service.update_persona(content=_LONG_ENOUGH, change_note="v2")
        service.update_persona(content=_LONG_ENOUGH + "!", change_note="v3")

        versions = [row.version for row in service.list_versions()]
        self.assertEqual(versions, [3, 2, 1])

    def test_rollback_reactivates_an_older_version(self):
        dao = FakePersonaDao([seed_row(version=1, content="v1 text")])
        service = build_service(dao)
        service.update_persona(content=_LONG_ENOUGH, change_note="v2")

        activated = service.rollback_persona(version=1)

        self.assertEqual(activated.content, "v1 text")
        self.assertTrue(activated.is_active)
        self.assertFalse(dao.get_by_version(2).is_active)

    def test_rollback_invalidates_the_cache(self):
        dao = FakePersonaDao([seed_row(version=1, content="v1 text")])
        service = build_service(dao)
        service.update_persona(content=_LONG_ENOUGH, change_note="v2")
        service.get_active_content()

        service.rollback_persona(version=1)

        self.assertEqual(service.get_active_content(), "v1 text")

    def test_rollback_to_an_unknown_version_is_refused(self):
        dao = FakePersonaDao([seed_row(version=1)])
        service = build_service(dao)

        with self.assertRaises(PersonaValidationError):
            service.rollback_persona(version=99)

    def test_rollback_with_no_persona_store_raises(self):
        service = build_service(None)
        with patch.object(PersonaService, "_get_dao", return_value=None):
            with self.assertRaises(PersonaValidationError):
                service.rollback_persona(version=1)


class ToolFacingWrapperTests(_ResetsSharedCache, unittest.TestCase):
    """The shapes the agent tools actually see."""

    def test_get_persona_reports_the_active_row(self):
        dao = FakePersonaDao([seed_row(version=1, content="Active text")])
        service = build_service(dao)

        result = service.get_persona()

        self.assertEqual(result["source"], "database")
        self.assertEqual(result["version"], 1)
        self.assertEqual(result["content"], "Active text")

    def test_get_persona_reports_the_file_fallback(self):
        service = build_service(None)
        with patch.object(PersonaService, "_get_dao", return_value=None):
            result = service.get_persona()

        self.assertEqual(result["source"], "file")
        self.assertEqual(result["content"], _FILE_CONTENT)
        self.assertIsNone(result["version"])

    def test_tool_update_persona_returns_the_new_version(self):
        dao = FakePersonaDao([seed_row(version=1)])
        service = build_service(dao)

        result = service.tool_update_persona(
            content=_LONG_ENOUGH, change_note="Nate asked for a tweak."
        )

        self.assertEqual(result["status"], "activated")
        self.assertEqual(result["version"], 2)
        self.assertEqual(result["created_by"], "nova-agent")

    def test_tool_list_persona_versions_omits_full_content(self):
        dao = FakePersonaDao([seed_row(version=1, content="Something long enough.")])
        service = build_service(dao)

        versions = service.tool_list_persona_versions()

        self.assertEqual(len(versions), 1)
        self.assertNotIn("content", versions[0])
        self.assertEqual(versions[0]["content_length"], len("Something long enough."))

    def test_tool_rollback_persona_returns_the_activated_version(self):
        dao = FakePersonaDao([seed_row(version=1, content="v1")])
        service = build_service(dao)
        service.update_persona(content=_LONG_ENOUGH, change_note="v2")

        result = service.tool_rollback_persona(version=1)

        self.assertEqual(result["status"], "activated")
        self.assertEqual(result["version"], 1)
        self.assertEqual(result["content"], "v1")


if __name__ == "__main__":
    unittest.main()
