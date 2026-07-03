from typing import Any
from uuid import UUID
from src.service.claude_service import ClaudeService

class AgentLoop:
    """
    Handles the logic for orchestrating the LLM's lifecycle and memory context.
    """
    def __init__(self):
        self.claude_service = ClaudeService()
        self.conversations = dict[UUID, list] #key: uuid of conversation, value: list of messages
        self.background_agents = Any

    def run(self):
        """
        Run the agent loop.
        """
        pass