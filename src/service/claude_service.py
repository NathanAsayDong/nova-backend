from anthropic import Anthropic
import os
from collections.abc import Iterator
from typing import Optional
from anthropic.types.message import Message

class ClaudeService:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        self.MODEL = 'claude-sonnet-5'
        self.max_tokens = int(os.getenv("CLAUDE_MAX_TOKENS", "1024"))

    def _build_messages(self, prompt: str, context: Optional[list]) -> list:
        messages = []
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": prompt})
        return messages

    def stream_response(self, prompt: str, role: Optional[str] = None, context: Optional[list] = None, tools: Optional[list] = None) -> Iterator[str]:
        """
        Stream a response from the Claude API.

        Args:
            prompt: The prompt to send to the Claude API.
            role: The role of the user.
            context: The context of the conversation.

        Yields:
            Text deltas as they are generated.
        """
        kwargs = {"tools": tools} if tools else {}
        with self.client.messages.stream(
            model=self.MODEL,
            messages=self._build_messages(prompt, context),
            max_tokens=self.max_tokens,
            **kwargs,
        ) as stream:
            yield from stream.text_stream

    def get_response(self, prompt: str, role: Optional[str] = None, context: Optional[list] = None, tools: Optional[list] = None) -> Message:
        """
        Get a response from the Claude API.

        Args:
            prompt: The prompt to send to the Claude API.
            role: The role of the user.
            context: The context of the conversation.
        """
        kwargs = {"tools": tools} if tools else {}
        return self.client.messages.create(
            model=self.MODEL,
            messages=self._build_messages(prompt, context),
            max_tokens=self.max_tokens,
            **kwargs,
        )


    