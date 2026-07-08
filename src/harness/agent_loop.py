import re
from collections.abc import Iterable, Iterator
from typing import Any
from uuid import UUID
import uuid

from anthropic.types.message import Message

from src.service.claude_service import ClaudeService
from src.model.responsibility import Responsibility

_SENTENCE_END = re.compile(r"[.!?][\"')\]]*\s")
_MIN_SENTENCE_CHARS = 30


def iter_sentence_chunks(text_stream: Iterable[str], min_chars: int = _MIN_SENTENCE_CHARS) -> Iterator[str]:
    """
    Group a stream of text deltas into sentence-sized chunks suitable for TTS.

    Chunks are only emitted at sentence boundaries past `min_chars`, so short
    fragments like abbreviations don't produce choppy audio.
    """
    buffer = ""
    for piece in text_stream:
        buffer += piece
        while True:
            match = _SENTENCE_END.search(buffer, min_chars)
            if not match:
                break
            chunk = buffer[: match.end()].strip()
            buffer = buffer[match.end():]
            if chunk:
                yield chunk
    remainder = buffer.strip()
    if remainder:
        yield remainder


class AgentLoop:
    """
    Handles the logic for orchestrating the LLM's lifecycle and memory context.
    """

    def __init__(self):
        self.claude_service = ClaudeService()
        self.conversations: dict[UUID, list] = {}
        self.background_agents = Any

    def new_conversation_id(self) -> UUID:
        return self.__generate_conversation_uuid()

    def conversation_loop(self, prompt: str, conversation_uuid: UUID) -> str:
        """
        Run a single conversation turn and return the model's response text.
        """
        if conversation_uuid not in self.conversations:
            self.conversations[conversation_uuid] = []

        history = self.conversations[conversation_uuid]
        response = self.claude_service.get_response(prompt, context=history)
        text = self._extract_text(response)

        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": text})

        return text

    def conversation_loop_stream(self, prompt: str, conversation_uuid: UUID) -> Iterator[str]:
        """
        Run a single conversation turn, yielding sentence-sized chunks of the
        response as they are generated.

        History is updated when the stream finishes; if the stream is
        interrupted, whatever text was generated so far is still committed.
        """
        history = self.conversations.setdefault(conversation_uuid, [])
        parts: list[str] = []

        def collect(stream: Iterable[str]) -> Iterator[str]:
            for piece in stream:
                parts.append(piece)
                yield piece

        text_stream = self.claude_service.stream_response(prompt, context=history)
        try:
            yield from iter_sentence_chunks(collect(text_stream))
        finally:
            if parts:
                history.append({"role": "user", "content": prompt})
                history.append({"role": "assistant", "content": "".join(parts)})

    def background_agent_loop(self):
        """
        Runs the scheduler loop that checks out background agents for work.
        """
        pass

    def __preform_responsibility(self, responsibility: Responsibility):
        """
        Agent performs a responsibility.
        """
        pass

    def __queue_background_agent(self, background_agent: Any):
        """
        Queue a background agent.
        """
        pass

    def __generate_conversation_uuid(self) -> UUID:
        """
        Generate a new conversation UUID.
        """
        return uuid.uuid4()

    @staticmethod
    def _extract_text(message: Message) -> str:
        parts: list[str] = []
        for block in message.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "".join(parts)
