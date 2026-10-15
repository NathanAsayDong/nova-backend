"""
Photo uploads from the glasses client.

POST /vision/images takes the raw JPEG as the request body (Bearer auth, like
every other route behind AuthGate) and answers with the imageId the phone
lists on its next `stop`, plus who the face matcher saw. `?requestId=` marks
the upload as the answer to a `capture_request` from the `look` tool.

POST /vision/capture-failed tells a waiting `look` the phone could not take
the photo, so the tool fails at once instead of waiting out its timeout.
"""

import asyncio

from fastapi import APIRouter, Body, HTTPException, Request

from src.service.vision_service import MAX_UPLOAD_BYTES, InvalidImage, VisionService

router = APIRouter(prefix="/vision", tags=["vision"])
vision_service = VisionService()

_JPEG_TYPES = {"image/jpeg", "image/jpg", "image/pjpeg"}


async def read_jpeg_body(request: Request, limit: int = MAX_UPLOAD_BYTES) -> bytes:
    """
    The request body as JPEG bytes, refusing anything else or anything too big.

    Shared with the enrollment routes, which take samples the same way.
    """
    content_type = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    if content_type not in _JPEG_TYPES:
        raise HTTPException(status_code=415, detail="Send the photo as image/jpeg.")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise HTTPException(status_code=413, detail="That photo is larger than 5 MB.")
    body = bytearray()
    async for piece in request.stream():
        body.extend(piece)
        if len(body) > limit:
            raise HTTPException(status_code=413, detail="That photo is larger than 5 MB.")
    if not body:
        raise HTTPException(status_code=400, detail="The photo was empty.")
    return bytes(body)


@router.post("/images")
async def upload_image(request: Request, requestId: str | None = None) -> dict:
    jpeg = await read_jpeg_body(request)
    try:
        # Decoding, resizing and face matching are CPU work; keep them off the
        # loop the voice sockets run on.
        image = await asyncio.to_thread(vision_service.ingest, jpeg, requestId or None)
    except InvalidImage as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return image.response()


@router.post("/capture-failed")
async def capture_failed(payload: dict = Body(...)) -> dict:
    request_id = payload.get("requestId")
    if not isinstance(request_id, str) or not request_id:
        raise HTTPException(status_code=400, detail="'requestId' is required.")
    reason = payload.get("reason")
    resolved = vision_service.capture_failed(
        request_id, reason if isinstance(reason, str) else None
    )
    return {"resolved": resolved}
