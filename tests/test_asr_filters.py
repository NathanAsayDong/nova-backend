"""
Keeping invented words out of Nova's transcripts.

Whisper writes something for every clip it is handed, including a cough, a
baby, or room noise ("you", "Thanks for watching!"). These filters drop that
output without touching real speech.
"""

import unittest
from types import SimpleNamespace

from src.service.asr_service import ASRService, drop_hallucination


def _segment(text, no_speech_prob=0.01, avg_logprob=-0.2):
    return SimpleNamespace(text=text, no_speech_prob=no_speech_prob, avg_logprob=avg_logprob)


class DropHallucinationTests(unittest.TestCase):
    def test_known_noise_transcripts_are_dropped(self):
        for text in ("you", "You.", " you ", "?", "...", "Thanks for watching!", ""):
            self.assertEqual(drop_hallucination(text), "", repr(text))

    def test_real_short_replies_survive(self):
        for text in ("Thank you.", "Thanks", "Stop.", "Yes", "You too", "Can you hear me?"):
            self.assertEqual(drop_hallucination(text), text, text)


class WhisperSegmentFilterTests(unittest.TestCase):
    def _service(self, segments):
        service = ASRService.__new__(ASRService)
        service.hotwords = None
        service.whisper = SimpleNamespace(transcribe=lambda *a, **k: (iter(segments), None))
        return service

    def test_segments_whisper_judges_non_speech_are_dropped(self):
        service = self._service(
            [
                _segment("Call Brad and tell him a joke."),
                _segment("Baby.", no_speech_prob=0.8, avg_logprob=-1.4),
            ]
        )
        self.assertEqual(
            service._transcribe_whisper("clip.webm", "en"), "Call Brad and tell him a joke."
        )

    def test_quiet_but_confident_speech_is_kept(self):
        # High no-speech probability alone is not enough: soft real speech
        # scores that way too, but Whisper is confident in the words.
        service = self._service([_segment("Okay.", no_speech_prob=0.7, avg_logprob=-0.3)])
        self.assertEqual(service._transcribe_whisper("clip.webm", "en"), "Okay.")


if __name__ == "__main__":
    unittest.main()
