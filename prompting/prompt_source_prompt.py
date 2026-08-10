from enum import StrEnum


class PromptSourceEnum(StrEnum):
    CHAT_PROMPT = ""
    SPEECH_PROMPT = "The user is interacting using voice mode. Please be brief in your response. Your response needs to be really concise and summarized becuase putting code and long explinatioons into our systems tts will produce a long audio file and ruin the user experience."