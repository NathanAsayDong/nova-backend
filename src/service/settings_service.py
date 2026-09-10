"""
Settings service for managing user preferences like model selection.
Stores settings in memory with potential future persistence to database.
"""

from typing import Optional, Dict, Any
import os


class SettingsService:
    """Manages Nova user settings and preferences."""

    # Class attribute, deliberately, and this is load-bearing: the settings
    # controller builds a FRESH ClaudeService (and so a fresh SettingsService)
    # for every request, so a dict on `self` would be discarded the moment the
    # request that wrote it ended — set_model would report success and change
    # nothing. Same trap CodingService documents for its link and loop.
    #
    # Still in memory, so a switch does not survive a restart; persisting it is
    # the next step if that matters.
    _settings: Dict[str, Any] = {}

    def __init__(self):
        """Initialize settings service with default values."""
        self.default_model = os.getenv("DEFAULT_CLAUDE_MODEL", "claude-haiku-4-5")
        self.available_models = [
            "claude-opus-4-1",
            "claude-sonnet-4-20250514",
            "claude-haiku-4-5",
        ]
        self._settings.setdefault("current_model", self.default_model)

    def get_current_model(self) -> str:
        """Get the currently selected model."""
        return self._settings.get("current_model", self.default_model)

    def set_current_model(self, model: str) -> bool:
        """
        Set the current model.

        Args:
            model: The model to switch to.

        Returns:
            True if successful, False if invalid model.
        """
        if model not in self.available_models:
            return False
        self._settings["current_model"] = model
        return True

    def get_available_models(self) -> list[str]:
        """Get list of available models."""
        return self.available_models

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all current settings."""
        return self._settings.copy()
