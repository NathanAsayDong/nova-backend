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
# silence to be sure the speaker stopped. Raised from 600 to 750 (+25%):
# PR #35 fixed the live-caption floor, but Nate was still getting cut off on
# the normal voice path and especially on the glasses, where mic placement
# and wind noise make a genuinely-finished-sounding tail more common mid-
# sentence. Every tier below is raised for the same reason — this whole pass
# is "make end-of-speech detection substantially less aggressive," not just
# patch the one floor bug.
MIN_SILENCE_MS = _ms(750)
# A trailing period. Weaker evidence than a question mark: Whisper ends
# whatever fragment it decodes with a period, and people dictating pause
# between complete sentences intending to continue — so a statement gets a
# thinking-pause of grace that a question does not need. Raised from 850 to
# 1100 (+~29%).
STATEMENT_SILENCE_MS = _ms(1100)
# Nothing either way — no transcript yet. Raised from 1000 to 1300 (+30%),
# to match the client's own neutral starting window (TurnDetector.swift /
# turnDetector.ts `defaultSilenceMs`) — keep those in step if this changes.
DEFAULT_SILENCE_MS = _ms(1300)
# Leaning unfinished: a particle, a comma, mid-number, a short fragment, or a
# clause Whisper did not close with punctuation. Raised from 1400 to 2100
# (+50%) — the biggest relative bump of the five tiers, because this is the
# window that actually covers an ordinary mid-thought pause ("let me think
# about... the budget") or trailing off, which is exactly the behavior Nate
# is describing as a cutoff.
PENDING_SILENCE_MS = _ms(2100)
# Obviously unfinished: hold the line. This is the window that actually
# protects a speaker who pauses mid-thought ("send that to, uh...") — first
# raised from 2200 to 2800 (+~27%), now from 2800 to 3600 (+~29%, so a
# dangling conjunction or filler word gets a solid 3.6s before Nova gives up
# and treats silence as the end of the turn).
MAX_SILENCE_MS = _ms(3600)

# Below this many words, a bare trailing period is not trusted as evidence
# the sentence is finished — see `_score_transcript`'s "weak_terminal_
# punctuation" branch. Whisper puts a period on whatever fragment it is
# handed ("Sophie." after two words is as likely a dangling name as a
# complete thought), and a short fragment is exactly where that habit does
# the most damage: at low word counts there is no other lexical evidence
# (hard/soft continuation, filler) to catch it.
MIN_WORDS_FOR_BARE_PERIOD = 3


# Live captions are transcribed with greedy decoding (ASRService's `fast`
# flag) so they can be redrawn roughly once a second while the user is still
# talking, rather than every ~900ms costing a full beam-search pass. Greedy
# decoding is measurably worse exactly where this scorer looks hardest: the
# last word or two of the transcript. A greedy pass that mishears a dangling
# "Sophie," as "Sophie." is enough to swing the window all the way down to
# MIN_SILENCE_MS before the speaker has actually finished — and if an
# ordinary mid-sentence breath happens to land inside that window, Nova cuts
# in on an unfinished thought. The pass that actually runs during the
# silence wait (`run_speculative_transcription`, full beam search) does not
# have this problem, so only it is trusted with the sub-second floor.
# Configurable because mic quality and ASR model affect greedy accuracy
# differently machine to machine; NOVA_CAPTION_SILENCE_FLOOR_MS in .env.
def _caption_floor() -> int:
    try:
        return _ms(int(os.getenv("NOVA_CAPTION_SILENCE_FLOOR_MS", "1100")))
    except ValueError:
        return _ms(1100)


CAPTION_SILENCE_FLOOR_MS = _caption_floor()


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


def _score_transcript(transcript: str | None) -> EndpointDecision:
    """
    Pick the silence window for a turn whose transcript so far is `transcript`.

    Called on every partial caption, so the window tracks the utterance as it
    develops: it widens when the speaker trails off and snaps back down the
    moment the sentence resolves.

    Not called directly outside this module — see `endpoint_decision` and
    `caption_endpoint_decision` below, which both wrap this.
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
        # A short fragment does not get to borrow the statement tier just
        # because Whisper happened to end it with a period — that habit is
        # exactly as likely on a dangling two-word clip ("Sophie.", "The
        # thing.") as on a real complete thought, and at this word count
        # there is no other lexical evidence (hard/soft continuation,
        # filler) around to catch the false read. Require the transcript to
        # actually look like a finished utterance before trusting the
        # period; otherwise treat it the same as any other short fragment.
        if len(words) < MIN_WORDS_FOR_BARE_PERIOD:
            return EndpointDecision(PENDING_SILENCE_MS, "weak_terminal_punctuation")
        return EndpointDecision(STATEMENT_SILENCE_MS, "terminal_statement")
    if last_char in _PENDING_PUNCTUATION:
        return EndpointDecision(PENDING_SILENCE_MS, "pending_punctuation")

    if tail in _SOFT_CONTINUATIONS:
        return EndpointDecision(PENDING_SILENCE_MS, "soft_continuation")

    if len(words) <= 2:
        return EndpointDecision(PENDING_SILENCE_MS, "short_fragment")

    # Whisper punctuates what it hears as a finished sentence, so a clause it
    # left open is evidence the speaker is mid-thought ("…do you mind
    # actually finding"). That cut real requests off at the old 1s; the cost
    # of the longer wait is a beat on the rarer finished command that Whisper
    # also left unpunctuated.
    return EndpointDecision(PENDING_SILENCE_MS, "unpunctuated_clause")


def endpoint_decision(transcript: str | None) -> EndpointDecision:
    """
    `_score_transcript`, for a transcript trusted at face value.

    Use this for the pass that actually runs during the silence wait
    (full-quality decode, on audio the speaker has already stopped adding
    to) — the one place a verdict of MIN_SILENCE_MS should be allowed to
    stand. For a live caption transcribed with greedy decoding while the
    speaker may still be talking, use `caption_endpoint_decision` instead.
    """
    return _score_transcript(transcript)


def caption_endpoint_decision(transcript: str | None) -> EndpointDecision:
    """
    `_score_transcript`, floored for a live caption's lower accuracy.

    Live captions (ASRService's `fast=True` path) use greedy decoding so
    they can be redrawn roughly once a second while the user is still
    talking, rather than paying a full beam-search pass that often. Greedy
    decoding is measurably worse exactly where this scorer looks hardest:
    the last word or two of the transcript. A greedy pass that mishears a
    dangling "Sophie," as "Sophie." is enough to swing the window all the
    way down to MIN_SILENCE_MS before the speaker has actually finished —
    and if an ordinary mid-sentence breath happens to land inside that
    window, Nova cuts in on an unfinished thought.

    Flooring at CAPTION_SILENCE_FLOOR_MS keeps a caption's optimism in
    check: it can still lengthen the window on real evidence of an
    unfinished clause, just never shorten it past the floor on its own.
    The full-quality pass that runs during the silence wait
    (`run_speculative_transcription`, via plain `endpoint_decision`) is not
    floored — once the speaker has actually stopped and a careful decode
    says the sentence is done, that verdict is trusted all the way down to
    MIN_SILENCE_MS.
    """
    decision = _score_transcript(transcript)
    if decision.silence_ms >= CAPTION_SILENCE_FLOOR_MS:
        return decision
    return EndpointDecision(CAPTION_SILENCE_FLOOR_MS, decision.reason)


def silence_budget_ms(transcript: str | None) -> int:
    """Just the window, for callers that do not care why."""
    return endpoint_decision(transcript).silence_ms
