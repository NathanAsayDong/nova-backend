from anthropic import Anthropic
import os

class ClaudeService:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

    