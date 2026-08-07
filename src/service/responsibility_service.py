from typing import Optional
from src.dao.responsibility_dao import ResponsibilityDao
from src.service.claude_service import ClaudeService

class ResponsibilityService:
    def __init__(self) -> None:
        self.responsibility_dao = ResponsibilityDao()
        self.claude_service = ClaudeService()

    def preform_responsibility(self, responsibility_id: int, prompt: Optional[str] = None) -> str:
        responsibility = self.responsibility_dao.get(responsibility_id)
        if responsibility is None:
            raise ValueError(f"Responsibility with id {responsibility_id} not found")

        if prompt is None:
            prompt = responsibility.prompt

        response = self.claude_service.get_response(prompt)
        return response

    def check_for_responsibilities(self) -> None:
        """
        Checks for responsibilities that are past their due for expected run time.
        """
        pass