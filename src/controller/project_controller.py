"""Projects available to Nova and to the client."""

import asyncio

from fastapi import APIRouter, HTTPException

from src.service.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])

project_service = ProjectService()


@router.get("")
async def list_projects() -> list[dict]:
    return await asyncio.to_thread(project_service.list_projects)


@router.get("/{project_id}")
async def get_project(project_id: int) -> dict:
    project = await asyncio.to_thread(project_service.get_project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return {"id": project.id, **project.to_payload()}
