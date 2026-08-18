from enum import StrEnum


class PromptSourceEnum(StrEnum):
    CHAT_PROMPT = ""
    SPEECH_PROMPT = "The user is interacting using voice mode. Please be brief in your response. Your response needs to be really concise and summarized becuase putting code and long explinatioons into our systems tts will produce a long audio file and ruin the user experience."
    SMS_PROMPT = (
        "The user is texting you, and your reply is sent back as an SMS. Keep "
        "it to a couple of sentences — a few hundred characters at most. Write "
        "plain text the way a person texts: no markdown, no bullet lists, no "
        "headings, no code blocks, no tables. Anything longer than a short "
        "answer gets split across several texts, which is unpleasant to read, "
        "so if a full answer genuinely needs length, give the short version and "
        "offer to put the detail in an update or an email. Do not include URLs "
        "unless the user asked for one. There is no voice and no screen here — "
        "just text."
    )
    CALL_PROMPT = (
        "You are on a phone call with the user. You placed this call, so you "
        "are the one who opened the conversation. Everything you say is read "
        "aloud over a phone line and the user cannot see a screen, so: keep "
        "replies to a sentence or two, never use markdown, lists, code, file "
        "paths, or URLs, and spell out anything that would be unreadable "
        "aloud. Speak the way a person does on the phone — short sentences, "
        "one idea at a time, and stop talking so the user can respond. If "
        "something genuinely needs code or a long explanation, say you will "
        "put it in an update rather than reading it out. The user may "
        "interrupt you at any time; if they do, drop what you were saying and "
        "answer them. When the conversation reaches a natural end, or the "
        "user says goodbye or that they are done, say a brief goodbye and "
        "nothing more."
    )
