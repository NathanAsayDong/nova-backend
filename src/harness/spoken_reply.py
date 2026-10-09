"""
Turning what Nova WRITES into what Nova SAYS.

The spoken reply is the written reply, read aloud. Nothing is rewritten for the
ear and nothing is summarised: every sentence of prose Nova writes is a
sentence Nova says. The one exception is markdown. Code blocks, tables and
lists have no spoken form, so they stay on the screen and are skipped by the
voice; inline markup (emphasis, links, headings, inline code) is stripped down
to the words.

This module is the seam between the two. `LiveReply` reads a round as it is
written and releases sentences to the speaker as they complete, so speech can
start long before the answer is finished.
"""

import re

# A `<speak>` tag the model was never asked for. Earlier versions of the voice
# prompt requested one, and a conversation that still has them in its history
# may keep producing them. The words inside are ordinary prose now; only the
# markup is dropped.
_SPEAK_TAG = re.compile(r"</?speak\b[^>]*>", re.IGNORECASE)


# How many sentences a pre-tool progress line may run to. Answers are never
# clamped, but "let me check that" followed by a paragraph is not a progress
# line, and a model that turns chatty before a tool call must not stall the turn.
MAX_SPOKEN_SENTENCES = 2

# What Nova says when a reply has no sayable prose in it at all — an answer
# that is entirely a table, a code block, or a list.
#
# Silence is the wrong behaviour. A turn that called tools has already spent
# the user's patience on "let me pull that up" followed by however long the
# work took; ending it with nothing reads as Nova having failed, when in fact
# the answer is sitting on the screen. This is only ever a floor.
SCREEN_ONLY_LINE = "I've put the details on screen."

# A backstop on top of the sentence count for progress lines, because
# "sentence" is not a bound. Roughly 20 seconds of speech.
MAX_SPOKEN_CHARS = 320

# Sentences are batched up to about this many characters before they go to the
# speaker. One TTS request per short sentence is choppy and slow; a clause or
# two per request sounds like a person talking.
MIN_SPOKEN_CHUNK_CHARS = 60

_SENTENCE_END = re.compile(r"[.!?][\"')\]]*\s*$")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])[\"')\]]*\s+")

# Markdown that has no spoken form.
_FENCE = re.compile(r"^\s*(```|~~~)")
_INLINE_CODE = re.compile(r"`([^`]*)`")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
_BLOCKQUOTE = re.compile(r"^\s{0,3}>\s?")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_TABLE_ROW = re.compile(r"^\s*\|")
_RULE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
_EMPHASIS = re.compile(r"(\*{1,3}|_{1,3}|~~)(?=\S)(.+?)(?<=\S)\1", re.DOTALL)
_WHITESPACE = re.compile(r"\s+")

# Enough of a line to tell whether it is prose or the start of a markdown
# block ("- ", "1. ", "| ", "```").
_LINE_DECISION_CHARS = 4


class SpokenProse:
    """
    Pulls the sayable prose out of streamed markdown, sentence by sentence.

    Feed it deltas as they arrive. `push` returns the lines ready to be said,
    each one a batch of whole sentences. Code fences, table rows and list items
    are skipped; everything else is spoken in the order it was written. Call
    `finish` at the end of the round for whatever is left.
    """

    def __init__(self) -> None:
        self._line = ""
        self._taken = 0  # chars of the current line already moved to `_open`
        self._in_fence = False
        self._open = ""  # prose of the current paragraph, sentence not yet done
        self._ready: list[str] = []  # whole sentences waiting to reach the chunk size

    def push(self, delta: str) -> list[str]:
        out: list[str] = []
        parts = delta.split("\n")
        for index, part in enumerate(parts):
            self._line += part
            out.extend(self._take(complete=False))
            if index < len(parts) - 1:
                out.extend(self._end_line())
        return out

    def finish(self) -> list[str]:
        out = self._end_line()
        out.extend(self._flush_ready())
        return out

    def _kind(self, line_ended: bool) -> str | None:
        """'prose', 'skip', or None while a line is still too short to tell."""
        if self._in_fence or _FENCE.match(self._line):
            return "skip"
        stripped = self._line.lstrip()
        if not line_ended and len(stripped) < _LINE_DECISION_CHARS:
            return None
        if (
            _TABLE_ROW.match(self._line)
            or _LIST_ITEM.match(self._line)
            or _HEADING.match(self._line)
            or _RULE.match(self._line)
        ):
            return "skip"
        return "prose"

    def _take(self, *, complete: bool) -> list[str]:
        if self._kind(complete) != "prose":
            return []
        self._open += self._line[self._taken :]
        self._taken = len(self._line)
        return self._drain(complete=complete)

    def _end_line(self) -> list[str]:
        out = self._take(complete=True)
        if _FENCE.match(self._line):
            self._in_fence = not self._in_fence
        # A line break ends the sentence: headings and one-line paragraphs
        # carry no final punctuation to split on.
        out.extend(self._drain(complete=True))
        self._line = ""
        self._taken = 0
        return out

    def _drain(self, *, complete: bool) -> list[str]:
        sentences = [p for p in _SENTENCE_SPLIT.split(self._open) if p.strip()]
        # The last piece is still being written unless the buffer ends in a
        # finished sentence followed by whitespace. It goes back untouched,
        # trailing space included, so the next delta joins it cleanly.
        finished = (
            complete
            or not sentences
            or (self._open[-1:].isspace() and _SENTENCE_END.search(sentences[-1]))
        )
        if finished:
            self._open = ""
        else:
            self._open = sentences.pop()
        for sentence in sentences:
            said = _plain_text(sentence)
            if said:
                self._ready.append(said)
        if complete:
            return self._flush_ready()
        if sum(len(r) for r in self._ready) >= MIN_SPOKEN_CHUNK_CHARS:
            return self._flush_ready()
        return []

    def _flush_ready(self) -> list[str]:
        if not self._ready:
            return []
        line = " ".join(self._ready)
        self._ready = []
        return [line]


# How much prose is held back before the round is treated as the answer. A
# pre-tool acknowledgment is one sentence; an answer is longer than this within
# its first second of generation.
LIVE_HOLD_CHARS = 200


class LiveReply:
    """
    One round of a reply, read as it is written.

    Two things leave a round while the model is still writing it: the prose,
    streamed to the screen, and the same prose, sentence by sentence, to the
    speaker.

    The first sentence of a round looks the same whether it is the answer or a
    "let me check your calendar" that precedes a tool call, and the latter must
    neither land on the screen as the answer's opening paragraph nor be said as
    though it were the answer. So both are held until one of three things
    settles it: enough has arrived that it is plainly an answer
    (`LIVE_HOLD_CHARS`), the model opened a tool_use block (it was an
    acknowledgment — dropped from the screen, said as a "status" line), or the
    round ended.

    Events come out as the same dicts the agent loop yields, unclamped and
    ungated: `{"type": "speech_text", ...}` with a role of "status" or "final",
    and `{"type": "text", ...}` carrying whitespace-exact prose. The loop
    applies the progress limits, because those are turn-level decisions and
    this object sees one round.
    """

    def __init__(self) -> None:
        self._prose = SpokenProse()
        self._settled = False
        self._queued: list[str] = []
        self._display = ""
        self._live = False
        self._streamed = ""
        self._tool_round = False
        self._said = False

    @property
    def streamed(self) -> str:
        """Prose already sent to the screen this round, whitespace-exact."""
        return self._streamed

    @property
    def tool_round(self) -> bool:
        return self._tool_round

    def push(self, delta: str) -> list[dict]:
        events: list[dict] = []
        self._display += delta
        lines = self._prose.push(delta)

        if not self._settled:
            self._queued.extend(lines)
            if len(self._display) < LIVE_HOLD_CHARS:
                return events
            self._settled = True
            events.extend(self._speech(self._queued, "final"))
            self._queued = []
        else:
            events.extend(self._speech(lines, "final"))

        events.extend(self._maybe_go_live())
        return events

    def tool_use_started(self) -> list[dict]:
        """The model opened a tool call: this round was an acknowledgment."""
        self._tool_round = True
        events: list[dict] = []
        tail = self._prose.finish()
        if self._settled:
            events.extend(self._speech(tail, "final"))
        else:
            # Whatever was being held was the acknowledgment. It is said as one
            # status line and not shown as the answer; the end-of-round path
            # captions it.
            events.extend(self._speech(self._queued + tail, "status", join=True))
            self._queued = []
            self._display = ""
        return events

    def finish(self, *, tool_round: bool = False) -> list[dict]:
        """
        The round ended. Release whatever is still held.

        `tool_round` is for a turn that arrived complete rather than live —
        it never saw `tool_use_started`, so the caller says what the message
        turned out to contain.
        """
        if tool_round and not self._tool_round:
            return self.tool_use_started()
        events: list[dict] = []
        tail = self._prose.finish()
        if not self._settled:
            self._settled = True
            events.extend(self._speech(self._queued + tail, "final"))
            self._queued = []
        else:
            events.extend(self._speech(tail, "final"))
        if not self._tool_round and self._display:
            events.append(self._flush())
        return events

    def _speech(self, lines: list[str], role: str, *, join: bool = False) -> list[dict]:
        lines = [line for line in lines if line.strip()]
        if join and lines:
            lines = [" ".join(lines)]
        if lines:
            self._said = True
        return [{"type": "speech_text", "text": line, "role": role} for line in lines]

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


def strip_speak_tags(text: str) -> str:
    """
    Drop `<speak>` markup from a reply, keeping the words inside it.

    Voice turns no longer ask for the tag, but a conversation whose history
    still shows it can keep producing it, and markup must never reach the
    screen.
    """
    text = text or ""
    if _SPEAK_TAG.search(text) is None:
        return text
    return _SPEAK_TAG.sub("", text).strip()


def speech_summary(text: str) -> str:
    """
    The sayable prose of a whole written reply, markdown left out.

    For a reply that arrived complete rather than live. Returns "" when
    nothing sayable is left (a reply that was only a code block, say); the
    caller decides whether that means silence or `SCREEN_ONLY_LINE`.
    """
    prose = SpokenProse()
    lines = prose.push(text or "") + prose.finish()
    return " ".join(lines)


def clamp_spoken(text: str) -> str:
    """
    Hold a pre-tool progress line to the spoken budget.

    Only for progress lines. An answer is said in full; a "let me check that"
    that grows into a paragraph is not an answer and must not stall the turn.
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
    """One piece of prose to bare words, dropping markup with no spoken form."""
    stripped = _SPEAK_TAG.sub(" ", text or "")
    stripped = _IMAGE.sub(" ", stripped)
    stripped = _LINK.sub(r"\1", stripped)
    stripped = _INLINE_CODE.sub(r"\1", stripped)
    stripped = _BLOCKQUOTE.sub("", stripped)
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
