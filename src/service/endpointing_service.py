"""
Semantic endpointing: how long to wait for silence before ending a turn.

A fixed silence timeout is wrong in both directions at once. Set it short and
a speaker who pauses to think ("send that to, uh...") gets cut off; set it
long and every finished sentence costs the listener a needless second before
the reply starts. The fix production turn detectors use is to let *what was
said* pick the timeout: a transcript that reads as a complete thought needs
only enough silence to be sure the speaker stopped, while one trailing off on
a conjunction or a determiner should be given room to land.

This is the text-only version of that idea, scored over the live partial
transcript the socket already produces for captions, so it costs a regex pass
rather than a model inference on the critical path.

Two hard-won rules shape the word lists:

1. The last *word* matters more than the last punctuation mark — but only for
   words that genuinely cannot end an utterance. Whisper punctuates whatever
   fragment it is handed, so "Can you send this to." carries a fake period and
   a real dangling "to"; the hard-continuation check therefore beats the
   punctuation check. Everything else defers to punctuation.

2. Spoken English ends sentences with function words constantly. "What time is
   it", "turn the lights on", "I think so", "what are you waiting for" — a
   list built from the grammar-book intuition that pronouns, particles, and
   stranded prepositions "cannot end a sentence" holds the line after
   thousands of perfectly complete utterances, which is strictly worse than a
   fixed timeout. So the hard list is only words that essentially never end an
   utterance (conjunctions, articles, "to"); particles, prepositions,
   auxiliaries, and question words get a soft middle window; pronouns are not
   evidence of anything and are not listed at all.

Window names follow the AssemblyAI / LiveKit convention: MIN_SILENCE_MS is
floor latency for an obviously-finished utterance, MAX_SILENCE_MS the patience
ceiling for an obviously-unfinished one.
"""

import os
import re
from typing import NamedTuple


def _endpoint_scale() -> float:
    """
    One knob over every window: NOVA_ENDPOINT_SCALE in .env.

    Rooms, mics, and speakers differ — the same windows that feel snappy on
    one machine feel trigger-happy on another. Raising the scale (e.g. 1.3)
    makes Nova more patient everywhere at once; lowering it makes it faster.
    Bounded so a typo cannot produce a zero or a minute-long wait.
    """
    try:
        return max(0.25, min(4.0, float(os.getenv("NOVA_ENDPOINT_SCALE", "1.0"))))
    except ValueError:
        return 1.0


_SCALE = _endpoint_scale()


def _ms(base: int) -> int:
    return round(base * _SCALE)


# Obviously finished — a question, an exclamation, a bare "yes": just enough
# silence to be sure the speaker stopped.
MIN_SILENCE_MS = _ms(600)
# A trailing period. Weaker evidence than a question mark: Whisper ends
# whatever fragment it decodes with a period, and people dictating pause
# between complete sentences intending to continue — so a statement gets a
# thinking-pause of grace that a question does not need.
STATEMENT_SILENCE_MS = _ms(850)
# Nothing either way — no transcript yet, or a plain unpunctuated clause.
DEFAULT_SILENCE_MS = _ms(1000)
# Leaning unfinished: a particle, a comma, mid-number, a short fragment.
PENDING_SILENCE_MS = _ms(1400)
# Obviously unfinished: hold the line.
MAX_SILENCE_MS = _ms(2200)


class EndpointDecision(NamedTuple):
    """How long to wait, and the evidence that picked that window."""

    silence_ms: int
    reason: str


# Words that essentially never end an English utterance. A speaker who stops
# here has not stopped, they have paused — even when Whisper puts a period
# after the fragment. Deliberately small: every entry costs MAX_SILENCE_MS of
# latency each time it ends a sentence after all, so a word earns its place
# only if that basically never happens in speech.
_HARD_CONTINUATIONS = frozenset(
    {
        # conjunctions that demand a following clause
        "and", "but", "or", "nor", "because", "although", "whereas",
        "unless", "if", "than", "while", "since", "whether", "until",
        "however", "therefore", "besides", "plus",
        # articles and possessive determiners — a noun is coming
        "a", "an", "the",
        "my", "your", "our", "their", "whose",
        # infinitive/dative "to": "send it to", "I want to"
        "to",
        # contractions that grammatically require a verb
        "gonna", "wanna",
    }
)

# Words that *lean* unfinished but end real sentences often enough that the
# maximum hold would hurt: phrasal-verb particles and stranded prepositions
# ("turn the lights on", "what are you waiting for"), auxiliaries in
# elliptical answers ("yes I will"), question words ("tell me why"), and
# connectives that double as sentence-final adverbs ("I think so").
_SOFT_CONTINUATIONS = frozenset(
    {
        # prepositions / particles
        "about", "above", "across", "after", "against", "along", "among",
        "around", "at", "before", "behind", "below", "beneath", "beside",
        "between", "beyond", "by", "down", "during", "for", "from", "in",
        "inside", "into", "like", "near", "of", "off", "on", "onto", "out",
        "outside", "over", "through", "toward", "towards", "under", "up",
        "upon", "with", "within", "without",
        # auxiliaries / modals
        "am", "is", "are", "was", "were", "be", "been", "being", "do",
        "does", "did", "have", "has", "had", "will", "would", "shall",
        "should", "can", "could", "may", "might", "must",
        # question / relative leads
        "what", "which", "who", "whom", "when", "where", "why", "how",
        # connectives that also close sentences
        "so", "though", "then", "also",
    }
)

# Hesitation noises. Whisper transcribes these, and they are the single
# clearest signal that the speaker is still composing.
_FILLER_WORDS = frozenset({"um", "uh", "uhm", "erm", "er", "ah", "hmm", "mmm", "eh"})

# Utterances that are genuinely complete at one or two words. Without this a
# bare "yes" would be treated as a fragment and cost the user a full second.
_STANDALONE_COMPLETE = frozenset(
    {
        "yes", "yeah", "yep", "yup", "no", "nope", "nah", "ok", "okay",
        "sure", "correct", "right", "wrong", "stop", "cancel", "nevermind",
        "thanks", "thank", "please", "done", "exactly", "perfect", "great",
        "hello", "hi", "hey", "nova", "goodbye", "bye", "continue", "go",
        "next", "back", "louder", "quieter", "repeat", "again",
    }
)

_WORD = re.compile(r"[A-Za-z']+|\d+")
# Marks that signal an unfinished clause rather than a finished sentence.
_PENDING_PUNCTUATION = ",:;-–—"


def endpoint_decision(transcript: str | None) -> EndpointDecision:
    """
    Pick the silence window for a turn whose transcript so far is `transcript`.

    Called on every partial caption, so the window tracks the utterance as it
    develops: it widens when the speaker trails off and snaps back down the
    moment the sentence resolves.
    """
    text = (transcript or "").strip()
    if not text:
        # No words yet. The acoustic detector is on its own, so give it the
        # neutral window rather than the impatient one.
        return EndpointDecision(DEFAULT_SILENCE_MS, "no_transcript")

    words = _WORD.findall(text.lower())
    if not words:
        return EndpointDecision(DEFAULT_SILENCE_MS, "no_words")

    tail = words[-1]
    last_char = text[-1]

    # Strong lexical evidence first: it survives Whisper's habit of putting a
    # period on whatever fragment it was handed.
    if tail in _FILLER_WORDS:
        return EndpointDecision(MAX_SILENCE_MS, "filler")
    if tail in _HARD_CONTINUATIONS:
        return EndpointDecision(MAX_SILENCE_MS, "hard_continuation")
    if tail.isdigit():
        # Mid-dictation of a number, address, or time. Checked before
        # punctuation because Whisper writes "801." while a phone number is
        # still in progress.
        return EndpointDecision(PENDING_SILENCE_MS, "digits")

    # A bare acknowledgment is complete no matter how Whisper punctuates it —
    # "Yes." must not pay the statement tier's thinking-pause tax.
    if len(words) <= 2 and tail in _STANDALONE_COMPLETE:
        return EndpointDecision(MIN_SILENCE_MS, "standalone_complete")

    # An ellipsis is Whisper writing down a trail-off. Check before the plain
    # period, which it would otherwise be mistaken for.
    if text.endswith("...") or last_char == "…":
        return EndpointDecision(PENDING_SILENCE_MS, "ellipsis")

    # Punctuation next, by strength. A question mark is rarely fake — a
    # question to an assistant is over when it is asked. A period is weak:
    # Whisper ends fragments with one, and a speaker dictating several
    # sentences pauses between them intending to continue, so statements keep
    # a thinking-pause of grace. Soft-continuation words defer to both:
    # "turn it off." is a finished command far more often than a fragment.
    if last_char in "?!":
        return EndpointDecision(MIN_SILENCE_MS, "terminal_question")
    if last_char == ".":
        return EndpointDecision(STATEMENT_SILENCE_MS, "terminal_statement")
    if last_char in _PENDING_PUNCTUATION:
        return EndpointDecision(PENDING_SILENCE_MS, "pending_punctuation")

    if tail in _SOFT_CONTINUATIONS:
        return EndpointDecision(PENDING_SILENCE_MS, "soft_continuation")

    if len(words) <= 2:
        return EndpointDecision(PENDING_SILENCE_MS, "short_fragment")

    return EndpointDecision(DEFAULT_SILENCE_MS, "unpunctuated_clause")


def silence_budget_ms(transcript: str | None) -> int:
    """Just the window, for callers that do not care why."""
    return endpoint_decision(transcript).silence_ms
