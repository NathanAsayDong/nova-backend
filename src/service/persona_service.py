"""
PersonaService: Nova's persona prompt, live-editable from the database.

The persona used to be a single markdown file loaded once at process start.
It now lives in the persona_prompt table (migration 009) so an agent tool —
"hey Nova, update the persona..." — can change it without a restart. The
active row is cached for a short TTL (same shape as SettingsService's model
list cache below) because it is read on every conversation turn; the TTL is
short enough that an update is live within roughly a minute everywhere, and
invalidated immediately in the process that made the change.

The file on disk (prompting/nova_persona_prompt.md) is kept as the fallback.
If the database is unreachable — no credentials, no network, the table does
not exist yet — or has no active row, Nova's identity still loads from the
file rather than breaking every conversation. That fallback is the whole
reason this module never lets a database error escape to its caller.
"""

from __future__ import annotations

import time
from typing import Any

from prompting.prompt_enums import PromptEnums
from src.dao.persona_prompt_dao import PersonaPromptDao
from src.model.persona_prompt import PersonaPrompt

# Long enough that a turn never pays for a database round trip, short enough
# that "update the persona" takes effect everywhere within about a minute
# without anyone restarting a process.
CACHE_TTL_SECONDS = 45

# Guardrails on update_persona. A handful of characters is never a real
# persona (a truncated paste, an empty string the model sent by mistake);
# the max keeps one bad write from ballooning the system prompt (and the
# column) without bound.
MIN_CONTENT_LENGTH = 50
MAX_CONTENT_LENGTH = 20_000

DEFAULT_PERSONA_NAME = "nova"


class PersonaValidationError(ValueError):
    """Raised for a persona write that fails the guardrails below."""


class PersonaService:
    """
    Class-level cache, deliberately — mirrors SettingsService's model-list
    cache. A fresh PersonaService is cheap to construct (it does not touch
    the database until something asks for the persona), so callers build one
    per use without worrying about losing the cache: it lives on the class,
    not the instance.
    """

    _cache: dict[str, PersonaPrompt] = {}
    _cached_at: dict[str, float] = {}

    def __init__(self) -> None:
        # Built lazily in _get_dao(), not here: constructing PersonaPromptDao
        # requires SUPABASE_URL/SUPABASE_KEY and, in a sandbox or a database
        # outage, can fail outright. A PersonaService has to stay constructible
        # everywhere (including AgentLoop's eager setup) even when neither is
        # available, so every caller falls back to the file instead of the
        # process failing to start.
        self._dao: PersonaPromptDao | None = None

    # ---------- plumbing ----------

    def _get_dao(self) -> PersonaPromptDao | None:
        if self._dao is not None:
            return self._dao
        try:
            self._dao = PersonaPromptDao()
        except Exception as exc:
            print(f"PersonaService: persona store unavailable: {exc}")
            return None
        return self._dao

    @classmethod
    def invalidate_cache(cls, name: str = DEFAULT_PERSONA_NAME) -> None:
        cls._cache.pop(name, None)
        cls._cached_at.pop(name, None)

    @classmethod
    def _store(cls, name: str, row: PersonaPrompt) -> None:
        cls._cache[name] = row
        cls._cached_at[name] = time.monotonic()

    # ---------- reading ----------

    def get_active_prompt(
        self, name: str = DEFAULT_PERSONA_NAME, refresh: bool = False
    ) -> PersonaPrompt | None:
        """
        The active persona_prompt row, or None if the database cannot answer
        and nothing is cached yet. Serves the cache within CACHE_TTL_SECONDS;
        `refresh=True` bypasses it (used right after a write).
        """
        fresh = (
            name in self._cache
            and time.monotonic() - self._cached_at.get(name, 0.0) < CACHE_TTL_SECONDS
        )
        if fresh and not refresh:
            return self._cache[name]

        dao = self._get_dao()
        active: PersonaPrompt | None = None
        if dao is not None:
            try:
                active = dao.get_active(name)
            except Exception as exc:
                print(f"PersonaService: could not load the active persona: {exc}")
                active = None

        if active is not None:
            self._store(name, active)
            return active

        # Database unreachable, or no active row yet: serve the stale cache
        # rather than falling straight to the file, same as SettingsService's
        # model list. Only when there is nothing cached does the caller see
        # None and fall back to the file.
        return self._cache.get(name)

    def get_active_content(
        self, name: str = DEFAULT_PERSONA_NAME, refresh: bool = False
    ) -> str:
        """
        The persona text to splice into the system prompt. Tries the
        database-backed active row first; falls back to the shipped markdown
        file when the database has nothing usable, so a database blip never
        leaves a conversation with no persona at all.
        """
        active = self.get_active_prompt(name=name, refresh=refresh)
        if active is not None and active.content and active.content.strip():
            return active.content
        return PromptEnums.NOVA_PERSONA_PROMPT.load()

    def get_active_version(self, name: str = DEFAULT_PERSONA_NAME) -> int | None:
        active = self.get_active_prompt(name=name)
        return active.version if active else None

    def list_versions(self, name: str = DEFAULT_PERSONA_NAME) -> list[PersonaPrompt]:
        dao = self._get_dao()
        if dao is None:
            return []
        return dao.list_versions(name)

    # ---------- writing ----------

    @staticmethod
    def _validate_content(content: str | None) -> str:
        if not isinstance(content, str) or not content.strip():
            raise PersonaValidationError("Persona content must not be empty.")
        normalized = content.strip()
        if len(normalized) < MIN_CONTENT_LENGTH:
            raise PersonaValidationError(
                f"Persona content is too short ({len(normalized)} characters; "
                f"minimum is {MIN_CONTENT_LENGTH})."
            )
        if len(normalized) > MAX_CONTENT_LENGTH:
            raise PersonaValidationError(
                f"Persona content is too long ({len(normalized)} characters; "
                f"maximum is {MAX_CONTENT_LENGTH})."
            )
        return normalized

    @staticmethod
    def _validate_change_note(change_note: str | None) -> str:
        if not isinstance(change_note, str) or not change_note.strip():
            raise PersonaValidationError(
                "A short change note describing the update is required."
            )
        return change_note.strip()

    def update_persona(
        self,
        content: str,
        change_note: str,
        name: str = DEFAULT_PERSONA_NAME,
        created_by: str | None = None,
    ) -> PersonaPrompt:
        """
        Create and activate a new persona version.

        This is a persisted write: the caller (the update_persona tool) is
        expected to have already confirmed the change with Nate, since it
        takes effect on Nova's very next turn. Raises PersonaValidationError
        for content that fails the guardrails, and whatever the database
        raises if the write itself fails — neither is swallowed, because a
        write the caller believes succeeded must not silently no-op.
        """
        normalized_content = self._validate_content(content)
        normalized_note = self._validate_change_note(change_note)

        dao = self._get_dao()
        if dao is None:
            raise PersonaValidationError(
                "The persona store is unavailable, so this change cannot be "
                "saved right now."
            )

        created = dao.create_version(
            content=normalized_content,
            name=name,
            created_by=created_by,
            notes=normalized_note,
        )
        print(
            f"PersonaService: persona '{name}' updated to version "
            f"{created.version} by {created_by or 'unknown'} ({normalized_note!r})"
        )
        self._store(name, created)
        return created

    def rollback_persona(
        self, version: int, name: str = DEFAULT_PERSONA_NAME
    ) -> PersonaPrompt:
        """
        Activate a prior version. Raises PersonaValidationError if that
        version does not exist or cannot be activated.
        """
        dao = self._get_dao()
        if dao is None:
            raise PersonaValidationError(
                "The persona store is unavailable, so rollback cannot run "
                "right now."
            )

        target = dao.get_by_version(version, name=name)
        if target is None:
            raise PersonaValidationError(
                f"No persona version {version} found for '{name}'."
            )

        activated = dao.activate_version(target.id)
        if activated is None:
            raise PersonaValidationError(
                f"Could not activate persona version {version}."
            )

        print(f"PersonaService: persona '{name}' rolled back to version {version}")
        self._store(name, activated)
        return activated

    # ---------- tool-facing wrappers ----------
    #
    # Returns plain dicts rather than PersonaPrompt rows: tool results go
    # straight back to the model as JSON, and SQLModel instances are not
    # trivially serializable the way ResponsibilityService's _to_dict-shaped
    # returns are.

    @staticmethod
    def _to_dict(row: PersonaPrompt) -> dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "version": row.version,
            "is_active": row.is_active,
            "content": row.content,
            "notes": row.notes,
            "created_by": row.created_by,
            "created_at": (
                row.created_at.isoformat()
                if hasattr(row.created_at, "isoformat")
                else row.created_at
            ),
        }

    def get_persona(self, name: str = DEFAULT_PERSONA_NAME) -> dict[str, Any]:
        """Tool: the active persona's version and content, for review."""
        active = self.get_active_prompt(name=name, refresh=True)
        if active is None:
            return {
                "source": "file",
                "content": PromptEnums.NOVA_PERSONA_PROMPT.load(),
                "version": None,
                "note": (
                    "No active persona row in the database; serving the "
                    "fallback file."
                ),
            }
        return {"source": "database", **self._to_dict(active)}

    def tool_update_persona(
        self,
        content: str,
        change_note: str,
        name: str = DEFAULT_PERSONA_NAME,
    ) -> dict[str, Any]:
        """
        Tool: persist a new persona version and activate it immediately.
        The caller must already have Nate's explicit confirmation — see the
        tool's own description, which says so.
        """
        created = self.update_persona(
            content=content,
            change_note=change_note,
            name=name,
            created_by="nova-agent",
        )
        return {
            "status": "activated",
            **self._to_dict(created),
        }

    def tool_list_persona_versions(
        self, name: str = DEFAULT_PERSONA_NAME
    ) -> list[dict[str, Any]]:
        """Tool: every stored version, newest first, without the full content."""
        versions = self.list_versions(name=name)
        return [
            {
                "id": row.id,
                "version": row.version,
                "is_active": row.is_active,
                "notes": row.notes,
                "created_by": row.created_by,
                "created_at": (
                    row.created_at.isoformat()
                    if hasattr(row.created_at, "isoformat")
                    else row.created_at
                ),
                "content_length": len(row.content or ""),
            }
            for row in versions
        ]

    def tool_rollback_persona(
        self, version: int, name: str = DEFAULT_PERSONA_NAME
    ) -> dict[str, Any]:
        """Tool: activate a prior version by its version number."""
        activated = self.rollback_persona(version=version, name=name)
        return {"status": "activated", **self._to_dict(activated)}
