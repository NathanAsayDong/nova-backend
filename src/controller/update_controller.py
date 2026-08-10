"""
Updates produced by background work (sub-agents, responsibilities).

The client polls the unviewed list to drive its updates badge; marking
viewed happens either through these endpoints or through Nova's
mark_all_updates_viewed tool after it reports on updates in chat.
"""

import asyncio

from fastapi import APIRouter, HTTPException

from src.service.update_service import UpdateService

router = APIRouter(prefix="/updates", tags=["updates"])

update_service = UpdateService()


@router.get("")
async def list_updates() -> dict:
    """All updates, newest first, plus the unviewed count for the badge."""
    updates = await asyncio.to_thread(update_service.get_all_updates)
    return {
        "updates": updates,
        "unviewedCount": sum(1 for update in updates if not update["is_viewed"]),
    }


@router.get("/unviewed")
async def list_unviewed_updates() -> dict:
    """Unviewed updates only, oldest first. Drives the yellow-dot indicator."""
    updates = await asyncio.to_thread(update_service.get_unviewed_updates)
    return {"updates": updates, "unviewedCount": len(updates)}


@router.post("/viewed")
async def mark_all_updates_viewed() -> dict:
    """Mark every unviewed update as viewed (user dismissed the badge)."""
    return await asyncio.to_thread(update_service.mark_all_updates_viewed)


@router.post("/{update_id}/viewed")
async def mark_update_viewed(update_id: int) -> dict:
    try:
        return await asyncio.to_thread(update_service.mark_update_viewed, update_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Update not found.")
