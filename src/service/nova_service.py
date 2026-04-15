from src.service.openai_service import OpenAIService
from src.service.whisper_service import WhisperService
from src.service.tts_service import TTSService
from fastapi import HTTPException, UploadFile

class NovaService:
    def __init__(self):
        self.openai_service = OpenAIService()
        self.whisper_service = WhisperService()
        self.tts_service = TTSService()
        
    def handle_user_message(self, file: UploadFile) -> UploadFile:
        """
        Handles a user message by transcribing the audio file and sending it to the OpenAI service.

        Args:
            file: The audio file to transcribe.

        Returns:
            The transcribed text.
        """
        try:
            transcript = self.whisper_service.transcribe(file)
            
            #agent call loop:
            calls = 0
            while True:
                response = self.openai_service.generate_response(transcript)
                if response.end_conversation:
                    break
                else:
                    transcript = response.transcript
                    file = self.tts_service.text_to_speech(transcript)
                    file = self.handle_user_message(file)
                    transcript = self.whisper_service.transcribe(file)
                    calls += 1
                    if calls > 3:
                        break

        except Exception as e:

            raise HTTPException(status_code=500, detail=str(e))