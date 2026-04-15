from pathlib import Path

import whisper

class WhisperService:
    def __init__(self) -> None:
        self.whisper = whisper.load_model("base")

    def transcribe_file_path(self, file_path: str | Path, language: str | None = None) -> str:
        transcription = self.whisper.transcribe(str(file_path), language=language)
        if isinstance(transcription, dict):
            return transcription.get("text", "").strip()
        return str(transcription)
