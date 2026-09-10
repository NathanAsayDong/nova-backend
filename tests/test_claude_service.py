"""
Per-model request settings.

Opus 5 and Sonnet 5 think by default at high effort, with the thinking
hidden. For a voice assistant that is a silence before the first word, so the
effort is turned down on the models that take the parameter — and left off
the ones that reject it.
"""

import os
import unittest
from unittest.mock import patch

from src.service.claude_service import ClaudeService


class GenerationKwargsTests(unittest.TestCase):
    def setUp(self):
        self.service = ClaudeService()

    def test_haiku_is_sent_no_effort(self):
        self.service.MODEL = "claude-haiku-4-5"

        self.assertEqual(self.service._generation_kwargs(), {})

    def test_opus_5_is_turned_down_to_low_effort(self):
        self.service.MODEL = "claude-opus-5"

        self.assertEqual(
            self.service._generation_kwargs(), {"output_config": {"effort": "low"}}
        )

    def test_sonnet_5_is_turned_down_too(self):
        self.service.MODEL = "claude-sonnet-5"

        self.assertEqual(
            self.service._generation_kwargs(), {"output_config": {"effort": "low"}}
        )

    def test_effort_is_configurable(self):
        with patch.dict(os.environ, {"NOVA_CLAUDE_EFFORT": "medium"}):
            self.assertEqual(ClaudeService().effort, "medium")

    def test_an_unknown_effort_falls_back_to_low(self):
        with patch.dict(os.environ, {"NOVA_CLAUDE_EFFORT": "turbo"}):
            self.assertEqual(ClaudeService().effort, "low")

    def test_the_output_ceiling_leaves_room_for_thinking(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_MAX_TOKENS", None)
            self.assertEqual(ClaudeService().max_tokens, 8192)
