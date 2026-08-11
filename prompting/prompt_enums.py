from enum import StrEnum
from pathlib import Path

_PROMPTING_DIR = Path(__file__).resolve().parent


class PromptEnums(StrEnum):
    """Prompt files shipped in this package; call .load() to read one."""

    NOVA_PERSONA_PROMPT = "nova_persona_prompt.md"
    TTS_CONVERSION_ENHANCER_PROMPT = "tts_conversion_enhancer_prompt.txt"
    BACKGROUND_AGENT_PROMPT = "background_agent_prompt.txt"

    def load(self) -> str:
        return (_PROMPTING_DIR / self.value).read_text(encoding="utf-8").strip()
