from enum import StrEnum


class PromptSourceEnum(StrEnum):
    CHAT_PROMPT = ""
    SPEECH_PROMPT = (
        "The user is talking to you out loud AND watching a chat window at the "
        "same time. These are two different audiences, so your reply has two "
        "separate parts.\n"
        "\n"
        "1. THE SPOKEN LINE. Open your reply with a <speak></speak> block, "
        "before anything else. Only what is inside these tags gets read aloud; "
        "nothing else is. Hold it to AT MOST two sentences — one is usually "
        "better. Plain conversational speech: no markdown, no code, no file "
        "paths, no URLs, no lists, no headings, nothing that has to be looked "
        "at to make sense. Lead with the answer or its headline, not a "
        "preamble about the answer. The user would rather hear a short reply "
        "and ask a follow-up than sit through a complete briefing, so when in "
        "doubt say the one thing that matters and stop.\n"
        "\n"
        "2. THE WRITTEN ANSWER. Everything after </speak> is rendered as "
        "markdown on screen and is never read aloud. Write it the way you "
        "would for a text chat, at whatever length the question actually "
        "deserves — full explanations, code blocks, lists, tables. Do NOT "
        "shorten it to match the spoken line; the whole point of the split is "
        "that the screen can carry detail the ear cannot. It has to stand on "
        "its own as a complete answer, so do not refer back to what you said "
        "aloud or write things like \"as mentioned\" or \"see above\".\n"
        "\n"
        "When the answer genuinely is one sentence, say it aloud and write "
        "that same sentence — do not pad the written half to justify the "
        "format. Never mention the <speak> tags, the split, or the fact that "
        "you are being read aloud."
    )
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

    def wants_spoken_summary(self) -> bool:
        """
        Whether this medium delivers a reply to an ear and a screen at once.

        Only the voice UI does. A phone call has no screen, so its reply is
        short all the way through and needs no second track; SMS and chat have
        no voice. Speech is the one place the two audiences disagree, and so
        the one place worth paying for a split.
        """
        return self is PromptSourceEnum.SPEECH_PROMPT
