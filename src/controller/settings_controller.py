"""
Controller for managing Nova settings and preferences.
Handles model selection, credits checking, and other user preferences.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import logging

router = APIRouter(prefix="/api/settings", tags=["settings"])
logger = logging.getLogger(__name__)


class ModelSwitchRequest(BaseModel):
    """Request body for switching models."""

    model: str


@router.get("/models")
def get_available_models() -> Dict[str, Any]:
    """
    Get list of available Claude models.

    Returns:
        JSON with the models this account can use and the current selection.

        `models` is the one a picker should render: each entry carries the id
        to send back and the display_name to show, both straight from
        Anthropic. `available_models` is the same set as bare ids, kept so
        anything already reading it keeps working.
    """
    from src.service.claude_service import ClaudeService

    claude_service = ClaudeService()
    options = claude_service.get_model_options()
    return {
        "models": options,
        "available_models": [model["id"] for model in options],
        "current_model": claude_service.get_current_model(),
        "current_model_id": claude_service.get_current_model_id(),
        # Resolved server-side: the stored id may be an alias
        # (claude-haiku-4-5) while the list carries the dated snapshot it
        # names, so a UI matching the two itself would show a bare id.
        "current_model_name": claude_service.get_current_model_name(),
    }


@router.post("/models")
def set_model(request: ModelSwitchRequest) -> Dict[str, Any]:
    """
    Switch the Claude model.

    Args:
        request: ModelSwitchRequest with model name.

    Returns:
        JSON with success status and current model.

    Raises:
        HTTPException: If model is invalid or switching fails.
    """
    if not request.model:
        raise HTTPException(status_code=400, detail="Model not specified")

    from src.service.claude_service import ClaudeService

    claude_service = ClaudeService()
    if claude_service.set_model(request.model):
        return {
            "success": True,
            "current_model": claude_service.get_current_model(),
            "current_model_id": claude_service.get_current_model_id(),
            "current_model_name": claude_service.get_current_model_name(),
        }
    else:
        raise HTTPException(
            status_code=400, detail=f"Invalid model: {request.model}"
        )


@router.get("/claude-credits")
def get_claude_credits() -> Dict[str, Any]:
    """
    Get remaining Claude API credits.

    Returns:
        JSON with credits remaining and account status.

    Raises:
        HTTPException: If unable to fetch credit information.
    """
    from src.service.claude_credits_service import ClaudeCreditsService

    credits_service = ClaudeCreditsService()
    usage_info = credits_service.get_usage_summary()

    if usage_info is None:
        raise HTTPException(
            status_code=500, detail="Unable to fetch credit information"
        )

    return usage_info


@router.get("/all")
def get_all_settings() -> Dict[str, Any]:
    """
    Get all current Nova settings.

    Returns:
        JSON with all user preferences.
    """
    from src.service.settings_service import SettingsService

    settings_service = SettingsService()
    return {"settings": settings_service.get_all_settings()}
