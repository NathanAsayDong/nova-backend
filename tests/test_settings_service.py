"""
Coverage for the model list, which is now asked for rather than assumed.

The list used to be three literals in the constructor, and it had drifted a
generation behind — offering two models that were no longer current and none of
the ones that were. It comes from Anthropic's Models API now, which moves the
risk somewhere else: a network call in a request path, and a settings page that
must not break when that call fails. Those are what these tests pin down.

Nothing here touches the network; `_fetch_models` is the seam.
"""

import unittest
from unittest.mock import patch

from src.service.settings_service import (
    _FALLBACK_MODELS,
    _MODELS_TTL_SECONDS,
    SettingsService,
)

# What the live endpoint returns, newest first.
_LIVE = [
    {"id": "claude-fable-5-1", "display_name": "Claude Fable 5.1"},
    {"id": "claude-opus-5", "display_name": "Claude Opus 5"},
    {"id": "claude-sonnet-5", "display_name": "Claude Sonnet 5"},
    {"id": "claude-opus-4-8", "display_name": "Claude Opus 4.8"},
    # The API answers with dated snapshots for older models, and bare ids for
    # current ones. That mix is the whole point of the alias tests below.
    {"id": "claude-haiku-4-5-20251001", "display_name": "Claude Haiku 4.5"},
]
_LIVE_IDS = [model["id"] for model in _LIVE]


class _ResetsSharedState:
    """
    Reset the class-level settings and model cache around each test.

    A mixin rather than a base TestCase on purpose: subclassing a TestCase to
    reuse its setUp re-runs every one of its tests in the subclass too, which
    is why one 13-test module can report 22.
    """

    def setUp(self):
        # Class-level state by design (a fresh service per request), so it has
        # to be reset between tests or they leak into each other.
        self._saved = (
            dict(SettingsService._settings),
            list(SettingsService._models_cache),
            SettingsService._models_fetched_at,
        )
        SettingsService._settings = {}
        SettingsService._models_cache = []
        SettingsService._models_fetched_at = 0.0

    def tearDown(self):
        settings, cache, fetched_at = self._saved
        SettingsService._settings = settings
        SettingsService._models_cache = cache
        SettingsService._models_fetched_at = fetched_at


class ModelListTests(_ResetsSharedState, unittest.TestCase):
    def test_the_list_comes_from_the_api(self):
        with patch.object(SettingsService, "_fetch_models", return_value=_LIVE):
            self.assertEqual(SettingsService().get_available_models(), _LIVE_IDS)

    def test_options_carry_the_display_name_from_the_api(self):
        """
        What a picker renders. Without this the UI maps ids to labels itself,
        which is the hardcoded-list problem one layer up — the settings modal
        labelled every model it did not recognise "Haiku (Fast & efficient)".
        """
        with patch.object(SettingsService, "_fetch_models", return_value=_LIVE):
            options = SettingsService().get_model_options()

        self.assertEqual(options, _LIVE)
        self.assertEqual(options[1]["display_name"], "Claude Opus 5")

    def test_a_model_with_no_display_name_still_renders(self):
        """Falls back to the id rather than showing a blank option."""
        class Nameless:
            id = "claude-unnamed-1"
            display_name = None

        with patch("anthropic.Anthropic") as client:
            client.return_value.models.list.return_value = [Nameless()]
            self.assertEqual(
                SettingsService._fetch_models(),
                [{"id": "claude-unnamed-1", "display_name": "claude-unnamed-1"}],
            )

    def test_order_is_preserved_so_the_newest_models_come_first(self):
        """The API returns newest first; sorting it would bury the current models."""
        with patch.object(SettingsService, "_fetch_models", return_value=_LIVE):
            self.assertEqual(SettingsService().get_available_models()[0], "claude-fable-5-1")
            self.assertEqual(
                SettingsService().get_model_options()[0]["display_name"], "Claude Fable 5.1"
            )

    def test_the_list_is_fetched_once_not_per_call(self):
        """
        A fresh service per request means an uncached fetch would be one HTTP
        round trip per settings page load and per validation.
        """
        with patch.object(
            SettingsService, "_fetch_models", return_value=_LIVE
        ) as fetch:
            SettingsService().get_available_models()
            SettingsService().get_available_models()
            SettingsService().get_available_models()

        self.assertEqual(fetch.call_count, 1)

    def test_refresh_bypasses_the_cache(self):
        with patch.object(SettingsService, "_fetch_models", return_value=_LIVE) as fetch:
            service = SettingsService()
            service.get_available_models()
            service.get_available_models(refresh=True)

        self.assertEqual(fetch.call_count, 2)

    def test_an_expired_cache_is_refetched(self):
        with patch.object(SettingsService, "_fetch_models", return_value=_LIVE) as fetch:
            SettingsService().get_available_models()
            SettingsService._models_fetched_at -= _MODELS_TTL_SECONDS + 1
            SettingsService().get_available_models()

        self.assertEqual(fetch.call_count, 2)

    def test_a_failed_fetch_falls_back_rather_than_returning_nothing(self):
        """A settings page that lists no models is worse than one listing a few."""
        with patch.object(SettingsService, "_fetch_models", return_value=[]):
            service = SettingsService()
            self.assertEqual(service.get_model_options(), _FALLBACK_MODELS)
            # The fallback carries display names too, so an offline picker
            # reads the same as an online one.
            self.assertTrue(all(m["display_name"] for m in service.get_model_options()))

    def test_a_stale_list_beats_the_fallback(self):
        with patch.object(SettingsService, "_fetch_models", return_value=_LIVE):
            SettingsService().get_available_models()

        # The API goes away after a good fetch.
        with patch.object(SettingsService, "_fetch_models", return_value=[]):
            SettingsService._models_fetched_at -= _MODELS_TTL_SECONDS + 1
            self.assertEqual(SettingsService().get_available_models(), _LIVE_IDS)

    def test_a_failed_fetch_is_retried_next_call(self):
        """Serving a stale list must not also freeze the clock on it."""
        with patch.object(SettingsService, "_fetch_models", return_value=_LIVE):
            SettingsService().get_available_models()
        SettingsService._models_fetched_at -= _MODELS_TTL_SECONDS + 1

        with patch.object(SettingsService, "_fetch_models", return_value=[]) as fetch:
            SettingsService().get_available_models()
            SettingsService().get_available_models()

        self.assertEqual(fetch.call_count, 2)

    def test_the_api_never_raises_into_the_caller(self):
        """_fetch_models swallows everything: no key, no network, a 500."""
        with patch("anthropic.Anthropic", side_effect=RuntimeError("no credentials")):
            self.assertEqual(SettingsService._fetch_models(), [])


class CurrentModelTests(_ResetsSharedState, unittest.TestCase):
    """Selecting a model, validated against the live list."""

    def test_a_model_the_hardcoded_list_never_had_is_selectable(self):
        """The point of the change: a newer model works without an edit."""
        with patch.object(SettingsService, "_fetch_models", return_value=_LIVE):
            service = SettingsService()
            self.assertTrue(service.set_current_model("claude-opus-5"))
            self.assertEqual(service.get_current_model(), "claude-opus-5")

    def test_a_model_the_account_cannot_use_is_refused(self):
        with patch.object(SettingsService, "_fetch_models", return_value=_LIVE):
            service = SettingsService()
            before = service.get_current_model()
            self.assertFalse(service.set_current_model("claude-imaginary-9"))
            self.assertEqual(service.get_current_model(), before)

    def test_the_selection_survives_the_request_that_made_it(self):
        """
        The settings controller builds a fresh ClaudeService — and so a fresh
        SettingsService — per request. Instance state would be discarded, and
        set_model would report success while changing nothing.
        """
        with patch.object(SettingsService, "_fetch_models", return_value=_LIVE):
            self.assertTrue(SettingsService().set_current_model("claude-sonnet-5"))
            self.assertEqual(SettingsService().get_current_model(), "claude-sonnet-5")

    def test_an_alias_resolves_to_the_dated_snapshot_it_names(self):
        """
        The Models API returns claude-haiku-4-5-20251001; people (and Nova's
        own DEFAULT_CLAUDE_MODEL) write claude-haiku-4-5. A strict membership
        test rejected the default model for that reason alone.
        """
        with patch.object(SettingsService, "_fetch_models", return_value=_LIVE):
            service = SettingsService()
            self.assertEqual(
                service.resolve_model("claude-haiku-4-5"), "claude-haiku-4-5-20251001"
            )
            self.assertTrue(service.set_current_model("claude-haiku-4-5"))

    def test_an_alias_still_gets_a_display_name(self):
        with patch.object(SettingsService, "_fetch_models", return_value=_LIVE):
            self.assertEqual(
                SettingsService().display_name_for("claude-haiku-4-5"), "Claude Haiku 4.5"
            )

    def test_an_unknown_model_resolves_to_nothing(self):
        with patch.object(SettingsService, "_fetch_models", return_value=_LIVE):
            service = SettingsService()
            self.assertIsNone(service.resolve_model("claude-imaginary-9"))
            self.assertIsNone(service.resolve_model(""))
            # display_name_for still answers with something printable.
            self.assertEqual(
                service.display_name_for("claude-imaginary-9"), "claude-imaginary-9"
            )

    def test_reading_the_current_model_costs_no_api_call(self):
        """
        ClaudeService reads this in its constructor, on every request and every
        agent turn. It has to stay free.
        """
        with patch.object(SettingsService, "_fetch_models", return_value=_LIVE) as fetch:
            SettingsService().get_current_model()

        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
