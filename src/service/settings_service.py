"""
Settings service for managing user preferences like model selection.

The model list is not hardcoded. It comes from Anthropic's Models API
(`GET /v1/models`), so a model released after this code was written shows up
without an edit — which is the whole problem with a literal list: the one that
used to be here had drifted a full generation behind and offered two models
that were no longer current.

The list is cached, because it is read on every settings page load and on every
validation in set_current_model, and it changes a few times a year. A static
fallback covers the case where the API cannot be reached at all, so a network
blip degrades the list rather than emptying it.
"""

from typing import Any, Dict

import os
import time

# How long a fetched model list is trusted. Models are announced, not
# hot-swapped; an hour is far shorter than the interval between releases and
# long enough that nothing in a request path pays for the round trip twice.
_MODELS_TTL_SECONDS = 3600

# Used only when the API cannot be reached and nothing is cached yet. Kept
# deliberately short — it exists so the settings page and model validation
# still work offline, not as a second source of truth. Display names are
# spelled the way the API spells them, so an offline picker reads the same as
# an online one.
_FALLBACK_MODELS = [
    {"id": "claude-opus-5", "display_name": "Claude Opus 5"},
    {"id": "claude-sonnet-5", "display_name": "Claude Sonnet 5"},
    {"id": "claude-haiku-4-5", "display_name": "Claude Haiku 4.5"},
]


class SettingsService:
    """Manages Nova user settings and preferences."""

    # Class attributes, deliberately, and this is load-bearing: the settings
    # controller builds a FRESH ClaudeService (and so a fresh SettingsService)
    # for every request, so state on `self` would be discarded the moment the
    # request that wrote it ended — set_model would report success and change
    # nothing, and the model list would be re-fetched on every call. Same trap
    # CodingService documents for its link and loop.
    #
    # Settings are still in memory, so a switch does not survive a restart;
    # persisting them is the next step if that matters.
    _settings: Dict[str, Any] = {}
    _models_cache: list[Dict[str, str]] = []
    _models_fetched_at: float = 0.0

    def __init__(self):
        """Initialize settings service with default values."""
        self.default_model = os.getenv("DEFAULT_CLAUDE_MODEL", "claude-haiku-4-5")
        self._settings.setdefault("current_model", self.default_model)

    # ---------- the model list ----------

    @property
    def available_models(self) -> list[str]:
        """
        Kept as a property so existing readers of `.available_models` still work.

        It used to be a plain list assigned in __init__; anything that touched
        the attribute now gets the live list instead.
        """
        return self.get_available_models()

    def get_available_models(self, refresh: bool = False) -> list[str]:
        """
        Model ids this account can actually use, newest first.

        Ids only, because this is what validation compares against and what
        callers storing a choice need. A picker wants
        `get_model_options()` instead, so it can show "Claude Opus 5" rather
        than `claude-opus-5`.
        """
        return [model["id"] for model in self.get_model_options(refresh=refresh)]

    def get_model_options(self, refresh: bool = False) -> list[Dict[str, str]]:
        """
        Models as {id, display_name}, newest first — what a picker renders.

        The display name comes from the API too. A UI that maps ids to labels
        itself has the same problem the hardcoded list had, one layer up: the
        settings modal used to label every model it did not recognise "Haiku
        (Fast & efficient)", so the moment the real list arrived, ten of the
        eleven entries were lying.

        Asks Anthropic rather than trusting a literal, and caches the answer
        for `_MODELS_TTL_SECONDS`. Never raises: a settings page that cannot
        list models is a worse outcome than one listing a slightly stale set,
        so a failed fetch falls back to the last good list, then to a static
        one.

        `refresh=True` bypasses the cache, for a "reload models" control.
        """
        fresh = time.monotonic() - self._models_fetched_at < _MODELS_TTL_SECONDS
        if self._models_cache and fresh and not refresh:
            return list(self._models_cache)

        fetched = self._fetch_models()
        if fetched:
            # Written on the class, not the instance — see the note above.
            SettingsService._models_cache = fetched
            SettingsService._models_fetched_at = time.monotonic()
            return list(fetched)

        if self._models_cache:
            # Serve the stale list rather than nothing, and do not reset the
            # timestamp, so the next call tries the API again.
            return list(self._models_cache)
        return list(_FALLBACK_MODELS)

    @staticmethod
    def _fetch_models() -> list[Dict[str, str]]:
        """
        One call to the Models API, returning [] on any failure.

        The client is built here rather than held on the service so that
        constructing a SettingsService stays free — ClaudeService builds one in
        its own __init__, on every request and every agent turn, and none of
        those need the model list.

        Ordering comes from the API, which returns newest first; it is
        preserved rather than sorted so the newest models head the list a
        settings UI renders.
        """
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
            return [
                {
                    "id": model.id,
                    # Falls back to the id so a model the API returns without
                    # a name still renders as something selectable.
                    "display_name": getattr(model, "display_name", None) or model.id,
                }
                for model in client.models.list(limit=100)
            ]
        except Exception as exc:
            print(f"Could not list models from the Claude API: {exc}")
            return []

    # ---------- the selected model ----------

    def get_current_model(self) -> str:
        """
        The currently selected model.

        Reads stored state only — no API call. ClaudeService calls this in its
        constructor on every request, so it has to stay free.
        """
        return self._settings.get("current_model", self.default_model)

    def set_current_model(self, model: str) -> bool:
        """
        Set the current model.

        Returns False for a model the account cannot use, so a bad value from
        a controller cannot leave the service pointing at something the
        Messages API will reject on the next turn.

        Aliases count as usable. The Models API answers with dated snapshots
        for older models — `claude-haiku-4-5-20251001` — while the alias
        `claude-haiku-4-5` is what people write and what the Messages API
        happily accepts. A strict membership test rejected Nova's own default
        model for that reason alone.
        """
        if not self.resolve_model(model):
            return False
        self._settings["current_model"] = model
        return True

    def resolve_model(self, model: str) -> str | None:
        """
        The listed id `model` refers to, or None if the account has no such model.

        An exact id wins; otherwise an alias matches the dated snapshot it
        names (`claude-haiku-4-5` -> `claude-haiku-4-5-20251001`).
        """
        if not model:
            return None
        listed = self.get_available_models()
        if model in listed:
            return model
        return next((entry for entry in listed if entry.startswith(model)), None)

    def display_name_for(self, model: str) -> str:
        """
        The name to show for a model id, falling back to the id itself.

        Used for the "current model" line, which is given a stored id that may
        be an alias rather than one of the ids in the list.
        """
        resolved = self.resolve_model(model) or model
        for entry in self.get_model_options():
            if entry["id"] == resolved:
                return entry["display_name"]
        return model

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all current settings."""
        return self._settings.copy()
