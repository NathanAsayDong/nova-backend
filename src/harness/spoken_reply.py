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

# What Nova says when a reply has no sayable prose in it at all — an answer
# that is entirely a table, a code block, or a diff.
#
# Silence was the old behaviour and it is the wrong one. A turn that called
# tools has already spent the user's patience on "let me pull that up"
# followed by however long the work took; ending it with nothing reads as
# Nova having failed, when in fact the answer is sitting on the screen. This
# is only ever a floor — the model's own `<speak>` line, or the opening of its
# prose, is used whenever either exists.
SCREEN_ONLY_LINE = "I've put the details on screen."

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
        self._no_block = False

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

    @property
    def no_block(self) -> bool:
        """True once it is clear no `<speak>` block is coming this round."""
        return self._no_block

    def _give_up_if_no_opener(self) -> None:
        """Stop watching once it is clear the model declined the format."""
        if len(self._buffer) < _OPENER_GRACE_CHARS:
            return
        if _UNCLOSED_SPEAK.search(self._buffer) is None:
            self._finished = True
            self._no_block = True


# How much prose is held back before the screen goes live. A pre-tool
# acknowledgment is one sentence; an answer is longer than this within its
# first second of generation. Matching the opener grace keeps one rule: by the
# time this much has arrived, both questions — is there a spoken line, and is
# this the answer — have been settled by the text itself.
LIVE_HOLD_CHARS = _OPENER_GRACE_CHARS


class LiveReply:
    """
    One round of a reply, read as it is written.

    Two things leave a round while the model is still writing it. The spoken
    line goes the moment its closing tag lands — that part `SpokenLineWatcher`
    already did. The written answer now goes too, streamed to the screen as
    prose once it is clear that prose is what it is.

    That last clause is the hard part. The first sentence of a round looks the
    same whether it is the answer or a "let me check your calendar" that
    precedes a tool call, and the latter must not land on the screen as the
    answer's opening paragraph. So prose is held until one of three things
    settles it: enough has arrived that it is plainly an answer
    (`LIVE_HOLD_CHARS`), the model opened a tool_use block (it was an
    acknowledgment — dropped here, shown by the end-of-round path as a status
    line), or the round ended.

    The same ambiguity decides the spoken line's role. A closed `<speak>` block
    followed by prose is the answer; followed by a tool call it is a progress
    line. The line is held for exactly that one next event — a token or a
    block start, never more than a few milliseconds — so it can go out labelled
    correctly rather than be relabelled later.

    Events come out as the same dicts the agent loop yields, unclamped and
    ungated: `{"type": "speech_text", ...}` with a role of "status" or "final",
    and `{"type": "text", ...}` carrying whitespace-exact prose. The loop
    applies the length ceiling and the progress limits, because those are
    turn-level decisions and this object sees one round.
    """

    def __init__(self) -> None:
        self._watcher = SpokenLineWatcher()
        self._text = ""
        self._settled = False
        self._pending_line: str | None = None
        self._display = ""
        self._live = False
        self._streamed = ""
        self._tool_round = False

    @property
    def streamed(self) -> str:
        """Prose already sent to the screen this round, whitespace-exact."""
        return self._streamed

    @property
    def tool_round(self) -> bool:
        return self._tool_round

    def push(self, delta: str) -> list[dict]:
        events: list[dict] = []
        self._text += delta

        if not self._settled:
            line = self._watcher.push(delta)
            if line is not None:
                # Everything after the closing tag is for the screen; the
                # block itself never is.
                self._settled = True
                self._pending_line = line
                match = _SPEAK_BLOCK.search(self._text)
                self._display = self._text[match.end():] if match else ""
            elif self._watcher.no_block:
                self._settled = True
                self._display = self._text
            else:
                # Still could be a block, or an unclosed one. Hold everything:
                # a raw tag must never reach the screen.
                return events
        else:
            self._display += delta

        if self._pending_line is not None and self._display.strip():
            # Prose after the block means this round is the answer, and the
            # line is the answer's — say it now.
            events.append(self._speech("final"))

        events.extend(self._maybe_go_live())
        return events

    def tool_use_started(self) -> list[dict]:
        """The model opened a tool call: this round was an acknowledgment."""
        self._tool_round = True
        events: list[dict] = []
        if self._pending_line is not None:
            events.append(self._speech("status"))
        # Whatever prose was being held was the acknowledgment. It is not the
        # answer, so it does not stream as one; the end-of-round path captions
        # it as a status line, where it belongs.
        self._display = ""
        return events

    def finish(self, *, tool_round: bool = False) -> list[dict]:
        """
        The round ended. Release whatever is still held.

        `tool_round` is for a turn that arrived complete rather than live —
        it never saw `tool_use_started`, so the caller says what the message
        turned out to contain. A line still pending is then a progress line
        or the answer's accordingly. Prose still held is flushed only when
        the round settled what it was; an unclosed `<speak>` never settles,
        and the end-of-round split handles that text whole, tags stripped.
        """
        if tool_round and not self._tool_round:
            return self.tool_use_started()
        if not self._settled and _UNCLOSED_SPEAK.search(self._text) is None:
            # Too short for the watcher to have given up, but the round is
            # over and there is no tag anywhere in it: it was all prose.
            self._settled = True
            self._display = self._text
        events: list[dict] = []
        if self._pending_line is not None:
            events.append(self._speech("final"))
        if self._settled and not self._tool_round and self._display:
            events.append(self._flush())
        return events

    def _speech(self, role: str) -> dict:
        line = self._pending_line or ""
        self._pending_line = None
        return {"type": "speech_text", "text": line, "role": role}

    def _maybe_go_live(self) -> list[dict]:
        if self._live:
            return [self._flush()] if self._display else []
        if len(self._display) >= LIVE_HOLD_CHARS:
            self._live = True
            return [self._flush()]
        return []

    def _flush(self) -> dict:
        chunk = self._display
        self._display = ""
        self._streamed += chunk
        return {"type": "text", "text": chunk}


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


def is_repeat(line: str, previous: str) -> bool:
    """
    Whether two spoken lines are the same thing said twice.

    Models settle into a phrase and reuse it across tool rounds — three
    consecutive "let me check that for you"s are worse than one. Compared
    loosely, because "On it." and "On it!" are not two different sentences.
    """
    return _comparable(line) == _comparable(previous) and _comparable(line) != ""


def _comparable(text: str) -> str:
    return _WHITESPACE.sub(" ", (text or "").strip().casefold()).strip(" .!?,;:—-")


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
