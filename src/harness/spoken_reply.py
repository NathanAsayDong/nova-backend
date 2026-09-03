"""
Separating what Nova SAYS from what Nova WRITES.

A spoken reply and a written one want opposite things. On screen, a long
markdown answer costs nothing — it streams in faster than it can be read, and
the reader skims to the part they wanted. Read aloud, that same answer is a
minute of audio the user has to sit through before they can respond, and there
is no skimming.

So a voice turn asks the model for both: a short line wrapped in
`<speak>...</speak>` for the ear, and the full markdown answer for the screen.
This module is the seam between them — it pulls the two apart, and it holds the
line on brevity when the model does not, because a prompt is a request and this
is a guarantee.
"""

import re

# The tag the speech prompt asks for. Case-insensitive and tolerant of
# attributes, because a model that mostly follows the format should not lose
# its whole spoken line to a stray space.
_SPEAK_BLOCK = re.compile(r"<speak\b[^>]*>(.*?)</speak>", re.DOTALL | re.IGNORECASE)

# An unclosed <speak> tag: the model opened the block and then never shut it.
# Treat everything after it as the spoken line rather than leaking a raw tag
# into the transcript.
_UNCLOSED_SPEAK = re.compile(r"<speak\b[^>]*>", re.IGNORECASE)

# How many sentences the spoken line may run to. Two is the ceiling the user
# set; one is usually better, and the prompt says so.
MAX_SPOKEN_SENTENCES = 2

# A backstop on top of the sentence count, because "sentence" is not a bound —
# a single one can run for a paragraph. Roughly 20 seconds of speech.
MAX_SPOKEN_CHARS = 320

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])[\"')\]]*\s+")

# Markdown that has no spoken form. Stripped only on the fallback path, where
# the model ignored the tag and its prose has to be salvaged into something
# sayable.
_FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`]*)`")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_BLOCKQUOTE = re.compile(r"^\s{0,3}>\s?", re.MULTILINE)
_LIST_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+", re.MULTILINE)
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)
_EMPHASIS = re.compile(r"(\*{1,3}|_{1,3}|~~)(?=\S)(.+?)(?<=\S)\1", re.DOTALL)
_WHITESPACE = re.compile(r"\s+")


# How much of a reply may go by without a `<speak>` opener before the watcher
# concludes none is coming. The prompt asks for the block FIRST, so anything
# past a sentence or two of prose means the model chose not to use it.
_OPENER_GRACE_CHARS = 200


class SpokenLineWatcher:
    """
    Reports the spoken line the instant it is finished, mid-generation.

    The `<speak>` block is asked for first precisely so this can exist. The
    two sentences Nova says are done long before the markdown answer beneath
    them, and the whole felt cost of a voice turn is the wait for those two
    sentences — so the turn should not have to see its own last token before
    it can start talking.

    Feed it deltas as they arrive. `push` returns the finished line exactly
    once, on the delta that completes the closing tag, and None every other
    time. A model that never opens the block, or opens it and never closes it,
    simply never fires: the end-of-turn path picks those up instead.
    """

    def __init__(self) -> None:
        self._buffer = ""
        self._finished = False

    def push(self, delta: str) -> str | None:
        if self._finished:
            return None

        self._buffer += delta

        # The delta that completes `</speak>` necessarily contains its final
        # ">", so anything without one cannot be the delta we are waiting for.
        # Cheap, and it keeps this off the hot path of a long generation.
        if ">" not in delta:
            self._give_up_if_no_opener()
            return None

        match = _SPEAK_BLOCK.search(self._buffer)
        if match is None:
            self._give_up_if_no_opener()
            return None

        self._finished = True
        return match.group(1).strip() or None

    def _give_up_if_no_opener(self) -> None:
        """Stop watching once it is clear the model declined the format."""
        if len(self._buffer) < _OPENER_GRACE_CHARS:
            return
        if _UNCLOSED_SPEAK.search(self._buffer) is None:
            self._finished = True


def split_spoken_reply(text: str) -> tuple[str, str | None]:
    """
    Pull a `<speak>` block out of a reply.

    Returns `(display_text, spoken_text)`. `spoken_text` is None when the model
    wrote no block — the caller decides whether that is fine (a typed turn) or
    something to fall back from (a spoken one).

    The tag never survives into `display_text` in either case: a model that
    emits one on a chat turn should not put markup on the user's screen.
    """
    if not text:
        return "", None

    match = _SPEAK_BLOCK.search(text)
    if match is not None:
        spoken = match.group(1).strip()
        display = (text[: match.start()] + text[match.end():]).strip()
    else:
        unclosed = _UNCLOSED_SPEAK.search(text)
        if unclosed is None:
            return text, None
        spoken = text[unclosed.end():].strip()
        display = text[: unclosed.start()].strip()

    # A reply that was ONLY the spoken line still needs something on screen.
    # Showing the same sentence is right: there was no longer answer to show.
    if not display:
        display = spoken

    return display, (spoken or None)


def speech_summary(text: str) -> str:
    """
    Reduce written prose to something worth reading aloud.

    Used when the model skipped the `<speak>` block. Strips the markdown that
    has no spoken form, then keeps the opening sentences — the opening is where
    an answer's headline lives, and everything after it is the detail the
    screen is already showing.

    Returns "" when nothing sayable is left (a reply that was only a code
    block, say); the caller stays silent rather than reading punctuation.
    """
    plain = _plain_text(text)
    if not plain:
        return ""
    return _clamp(plain)


def clamp_spoken(text: str) -> str:
    """
    Hold an already-conversational line to the spoken budget.

    For text the model intended to be spoken — a `<speak>` block, or a pre-tool
    acknowledgment — where the markdown stripping `speech_summary` does would
    be pointless but the length ceiling still has to hold.
    """
    collapsed = _WHITESPACE.sub(" ", (text or "").strip())
    if not collapsed:
        return ""
    return _clamp(collapsed)


def _plain_text(text: str) -> str:
    """Markdown to bare prose, dropping anything with no spoken form."""
    stripped = _FENCED_CODE.sub(" ", text or "")
    stripped = _TABLE_ROW.sub(" ", stripped)
    stripped = _IMAGE.sub(" ", stripped)
    stripped = _LINK.sub(r"\1", stripped)
    stripped = _INLINE_CODE.sub(r"\1", stripped)
    stripped = _HEADING.sub("", stripped)
    stripped = _BLOCKQUOTE.sub("", stripped)
    stripped = _LIST_BULLET.sub("", stripped)
    stripped = _EMPHASIS.sub(r"\2", stripped)
    return _WHITESPACE.sub(" ", stripped).strip()


def _clamp(text: str) -> str:
    """First `MAX_SPOKEN_SENTENCES` sentences, then the hard character cap."""
    sentences = [part for part in _SENTENCE_SPLIT.split(text) if part.strip()]
    kept = " ".join(sentences[:MAX_SPOKEN_SENTENCES]).strip() if sentences else text

    if len(kept) <= MAX_SPOKEN_CHARS:
        return kept

    # One very long sentence. Cut at a word boundary and end it cleanly, so TTS
    # reads a finished-sounding clause instead of trailing off mid-word.
    cut = kept[:MAX_SPOKEN_CHARS].rstrip()
    space = cut.rfind(" ")
    if space > MAX_SPOKEN_CHARS // 2:
        cut = cut[:space].rstrip()
    return cut.rstrip(",;:—- ") + "…"
