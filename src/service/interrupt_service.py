"""
Detecting the "Nova stop" / "Nova pause" mid-speech barge-in phrase.

This is deliberately narrower than `has_stop_phrase`
(src/controller/nova_controller.py) and `has_be_quiet_phrase`
(src/service/sidekick_service.py), which both end a whole session and
tolerate many phrasings of "I'm done". This one has a single, specific job:
let Nate interrupt Nova *while it is talking* without being understood as
having said anything else. Two concerns shape it:

  - Echo safety: Nova's own voice must never trip its own interrupt. Requiring
    the wake word "nova" immediately before "stop"/"pause" means Nova simply
    saying the word "stop" mid-sentence ("let's stop here") can never match.
  - Over-matching: a sentence that happens to contain the words should not
    match either ("tell Nova stop words list" is a request about stop words,
    not an instruction to stop). Matching is restricted to the *whole*
    utterance, or the *leading* words of a short one, so the phrase has to be
    what the utterance is actually about.
"""

from __future__ import annotations

import re

# Nova's name immediately followed by the instruction. Order matters: "stop
# nova" or "pause nova" are not matched - this is about addressing Nova, not
# describing something else that happens to end in its name.
_INTERRUPT_PHRASES: tuple[tuple[str, ...], ...] = (
    ("nova", "stop"),
    ("nova", "pause"),
)

# An utterance longer than this is about something else, even if it happens
# to start with the phrase's words - "nova stop" is unambiguous on its own or
# leading a short sentence ("Nova stop the music"), but a long one trails off
# into other content the phrase was never meant to gate.
_MAX_UTTERANCE_WORDS = 4


def _normalize_tokens(text: str) -> list[str]:
    """Lowercase, drop punctuation, and split into words."""
    cleaned = re.sub(r"[^\w\s]", " ", (text or "").lower())
    return cleaned.split()


def is_nova_interrupt_phrase(text: str) -> bool:
    """
    Whether `text` is Nate telling Nova to stop or pause mid-speech.

    Matches only "nova stop" or "nova pause" - case-insensitive, punctuation
    ignored - said as the whole utterance, or as the first two words of a
    short (at most four word) one, e.g. "Nova, stop!" or "Nova stop the
    music". A longer utterance never matches, even one that starts with
    those words, and neither does a sentence that merely mentions them
    ("tell Nova stop words list") or Nova's own voice saying "stop" without
    its name attached.

    Intended for final transcripts and stable partials alike - call it on
    whatever text a transcript pass has settled on.
    """
    tokens = _normalize_tokens(text)
    if not tokens or len(tokens) > _MAX_UTTERANCE_WORDS:
        return False
    return any(tuple(tokens[: len(phrase)]) == phrase for phrase in _INTERRUPT_PHRASES)
