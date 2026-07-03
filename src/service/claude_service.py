from anthropic import Anthropic
import os
from typing import Optional
from anthropic.types import RawMessageStreamEvent
from anthropic.types.message import Message

class ClaudeService:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        self.MODEL = 'claude-sonnet-5'
    
    def stream_response(self, prompt: str, role: Optional[str] = None, context: Optional[list] = None, tools: Optional[list] = None):
        """
        Stream a response from the Claude API.

        Args:
            prompt: The prompt to send to the Claude API.
            role: The role of the user.
            context: The context of the conversation.

        Returns:
            A generator of response chunks.
        """
        messages = []
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": prompt})

        stream = self.client.messages.create(
            model=self.MODEL,
            messages=messages,
            stream=True,
            tools=tools
        )

        return stream

    def get_response(self, prompt: str, role: Optional[str] = None, context: Optional[list] = None, tools: Optional[list] = None) -> Message:
        """
        Get a response from the Claude API.

        Args:
            prompt: The prompt to send to the Claude API.
            role: The role of the user.
            context: The context of the conversation.
        """
        messages = []
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": prompt})
        response = self.client.messages.create(
            model=self.MODEL,
            messages=messages,
            tools=tools
        )

        return response


    