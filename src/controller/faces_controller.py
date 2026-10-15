"""
Enrollment for face recognition: the people Nova may name through the glasses.

Not to be confused with face_controller.py, which relays the avatar face.

Everything here is behind AuthGate (Bearer). Adding a person requires
`consent: true` — the person's agreement to be recognised, confirmed by
Nathan — and samples are stored as embeddings only, never as photos.
"""

import asyncio

import numpy as np
from fastapi import APIRouter, Body, HTTPException, Request

from src.controller.vision_controller import read_jpeg_body
from src.service.face_service import (
    DuplicatePerson,
    EnrollmentError,
    FaceModelsMissing,
    FaceService,
    PersonNotFound,
)
from src.service.vision_service import InvalidImage, prepare

router = APIRouter(prefix="/faces", tags=["faces"])
face_service = FaceService()


@router.get("/people")
async def list_people() -> list[dict]:
    return await asyncio.to_thread(face_service.list_people)


@router.post("/people")
async def create_person(payload: dict = Body(...)) -> dict:
    try:
        return await asyncio.to_thread(
            face_service.create_person,
            payload.get("name") or "",
            payload.get("consent"),
            payload.get("consentNote"),
        )
    except DuplicatePerson as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except EnrollmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/people/{person_id}")
async def delete_person(person_id: int) -> dict:
    try:
        await asyncio.to_thread(face_service.delete_person, person_id)
    except PersonNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"deleted": True}


def _enroll(person_id: int, jpeg: bytes) -> int:
    _, rgb = prepare(jpeg)
    bgr = np.ascontiguousarray(np.asarray(rgb)[:, :, ::-1])
    return face_service.add_sample(person_id, bgr)


@router.post("/people/{person_id}/samples")
async def add_sample(person_id: int, request: Request) -> dict:
    jpeg = await read_jpeg_body(request)
    try:
        samples = await asyncio.to_thread(_enroll, person_id, jpeg)
    except PersonNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (EnrollmentError, InvalidImage) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except FaceModelsMissing as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"samples": samples}
