"""
Conversation state and transcripts.

Both ways of talking to Nova — chat and speech — write to the same
conversation, so this is the single place the client reads it back from.
"""

import asyncio
from uuid import UUID

from fastapi import APIRouter, HTTPException

from src.model.message import MessageRole
from src.service.conversation_service import ConversationService
from src.service.project_service import ProjectService

router = APIRouter(prefix="/conversations", tags=["conversations"])

conversation_service = ConversationService()
project_service = ProjectService()


def _project_payload(project_id: int | None) -> dict | None:
    if project_id is None:
        return None
    project = project_service.get_project(project_id)
    if project is None:
        return None
    return {"id": project.id, **project.to_payload()}


def _parse_uuid(conversation_id: str) -> UUID:
    try:
        return UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation id.")


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str) -> dict:
    """Current state of a conversation, including its attached project."""
    uuid_value = _parse_uuid(conversation_id)

    conversation = await asyncio.to_thread(
        conversation_service.get_conversation, uuid_value
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    project = await asyncio.to_thread(_project_payload, conversation.project_id)

    return {
        "conversationId": str(conversation.uuid),
        "isClosed": conversation.is_closed,
        "project": project,
    }


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str) -> dict:
    """
    Full persisted transcript, whether the turns came from chat or speech.

    Tool rows carry the json audit payload written by the agent loop; they are
    returned so the client can show what Nova did, not just what it said.
    """
    uuid_value = _parse_uuid(conversation_id)

    conversation = await asyncio.to_thread(
        conversation_service.get_conversation, uuid_value
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    messages = await asyncio.to_thread(conversation_service.get_messages, uuid_value)
    project = await asyncio.to_thread(_project_payload, conversation.project_id)

    return {
        "conversationId": str(conversation.uuid),
        "isClosed": conversation.is_closed,
        "project": project,
        "messages": [
            {
                "id": message.id,
                "role": str(message.role),
                "content": message.content or "",
                "format": "markdown" if message.role == MessageRole.NOVA else "text",
                "createdAt": (
                    message.created_at.isoformat()
                    if hasattr(message.created_at, "isoformat")
                    else message.created_at
                ),
            }
            for message in messages
        ],
    }


@router.post("/{conversation_id}/close")
async def close_conversation(conversation_id: str) -> dict:
    """Close a conversation permanently. Closed conversations cannot be reopened."""
    uuid_value = _parse_uuid(conversation_id)

    conversation = await asyncio.to_thread(
        conversation_service.close_conversation, uuid_value
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    # Drop in-process LLM history so a replayed id can't keep accumulating.
    from src.controller.nova_controller import agent_loop

    agent_loop.conversations.pop(uuid_value, None)

    return {"conversationId": str(uuid_value), "isClosed": True}
