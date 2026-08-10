"""
Read-only view of the tools Nova can call.

Every registered tool is always enabled, so there is no toggle endpoint —
this exists for introspection and debugging only.
"""

import asyncio

from fastapi import APIRouter

from src.model.tool import Tool
from src.service.tool_service import ToolService

router = APIRouter(prefix="/tools", tags=["tools"])

tool_service = ToolService()


@router.get("")
async def list_tools() -> list[Tool]:
    return await asyncio.to_thread(tool_service.list_tools)
