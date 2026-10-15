"""
What Nova sees through the glasses camera.

Photos reach the tower over HTTP, not the voice socket: while a turn runs the
socket handler is busy inside the `stop` event and is not reading, so a photo
sent on it would sit unread until the turn it was meant for was over. The
phone uploads to POST /vision/images as soon as it has the shot (usually
while the user is still talking), gets an imageId back, and lists the ids on
`stop`. The `look` tool goes the other way: it sends `capture_request` down
the socket mid-turn and waits for the upload that answers it.

At upload time each photo is normalised and run through the face matcher, so
that work overlaps with the user still speaking and with ASR. Claude gets the
image plus an `<in_view>` text block naming only the enrolled people the
matcher found; it is never asked who anyone is.

Photos live in memory for five minutes and are never written to disk.
"""

from __future__ import annotations

import asyncio
import base64
import io
import threading
import time
import uuid
from concurrent.futures import Future, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from src.service.tool_service import ToolExecutionError

IMAGE_TTL_SECONDS = 5 * 60
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_LONG_EDGE = 1280
JPEG_QUALITY = 85
# How many photos the store holds at once, whatever their age. A personal
# deployment takes a photo every few minutes; this only bounds a runaway.
_MAX_IMAGES = 64

# How long `look` waits for the phone to take and upload a photo. The glasses
# camera can need a few seconds to wake; past this the user is better served
# by "I couldn't get a picture" than by more silence.
LOOK_TIMEOUT_SECONDS = 10.0
_SEND_TIMEOUT_SECONDS = 3.0

IN_VIEW_OPEN = "<in_view>"
IN_VIEW_CLOSE = "</in_view>"


class InvalidImage(ValueError):
    """The upload is not a JPEG we can read."""


class CaptureFailed(RuntimeError):
    """The phone could not take the photo `look` asked for."""


@dataclass
class VisionImage:
    image_id: str
    jpeg: bytes
    width: int
    height: int
    people: list[dict[str, Any]] = field(default_factory=list)
    unknown_faces: int = 0
    faces_available: bool = True
    created_at: float = field(default_factory=time.monotonic)

    def response(self) -> dict[str, Any]:
        return {
            "imageId": self.image_id,
            "width": self.width,
            "height": self.height,
            "people": self.people,
            "unknownFaces": self.unknown_faces,
        }


class ImageStore:
    """
    Recent photos by imageId, plus the `look` requests waiting on one.

    Thread-safe: uploads land on the event loop (via to_thread), and `look`
    waits on the agent loop's worker thread, so the waiters are
    concurrent.futures Futures rather than asyncio ones.
    """

    def __init__(self, ttl: float = IMAGE_TTL_SECONDS) -> None:
        self.ttl = ttl
        self._lock = threading.Lock()
        self._images: dict[str, VisionImage] = {}
        self._pending: dict[str, Future] = {}

    def _prune(self, now: float) -> None:
        expired = [
            key for key, image in self._images.items()
            if now - image.created_at > self.ttl
        ]
        for key in expired:
            del self._images[key]
        while len(self._images) > _MAX_IMAGES:
            oldest = min(self._images, key=lambda key: self._images[key].created_at)
            del self._images[oldest]

    def put(self, image: VisionImage) -> None:
        with self._lock:
            self._images[image.image_id] = image
            self._prune(time.monotonic())

    def get(self, image_id: str) -> VisionImage | None:
        with self._lock:
            self._prune(time.monotonic())
            return self._images.get(image_id)

    def expect(self, request_id: str) -> Future:
        """Register a `look` waiting on the upload for `request_id`."""
        future: Future = Future()
        with self._lock:
            self._pending[request_id] = future
        return future

    def forget(self, request_id: str) -> None:
        with self._lock:
            self._pending.pop(request_id, None)

    def resolve(self, request_id: str, image_id: str) -> bool:
        with self._lock:
            future = self._pending.pop(request_id, None)
        if future is None or future.done():
            return False
        future.set_result(image_id)
        return True

    def fail(self, request_id: str, reason: str) -> bool:
        with self._lock:
            future = self._pending.pop(request_id, None)
        if future is None or future.done():
            return False
        future.set_exception(CaptureFailed(reason))
        return True


def prepare(jpeg: bytes) -> tuple[bytes, Any]:
    """
    Validate and normalise an uploaded photo.

    Returns the JPEG to send to Claude and the decoded, upright RGB image for
    the face matcher. The phone's EXIF orientation is applied (Claude and the
    matcher both want pixels the right way up), and the long edge is capped
    at MAX_LONG_EDGE. The bytes are only re-encoded when something changed,
    so a photo the phone already sized correctly goes through untouched.
    """
    from PIL import Image, ImageOps, UnidentifiedImageError

    if not jpeg:
        raise InvalidImage("The photo was empty.")
    try:
        with Image.open(io.BytesIO(jpeg)) as probe:
            if probe.format != "JPEG":
                raise InvalidImage(f"Expected a JPEG, got {probe.format or 'unknown'}.")
            probe.verify()
        # verify() leaves the image unusable; decode again for real.
        image = Image.open(io.BytesIO(jpeg))
        image.load()
    except InvalidImage:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise InvalidImage(f"Could not read that photo: {exc}") from exc

    # 0x0112 is the EXIF Orientation tag; 1 means already upright.
    rotated = image.getexif().get(0x0112, 1) not in (1, None)
    rgb = ImageOps.exif_transpose(image).convert("RGB")
    resized = max(rgb.size) > MAX_LONG_EDGE
    if resized:
        rgb.thumbnail((MAX_LONG_EDGE, MAX_LONG_EDGE), Image.Resampling.LANCZOS)

    if resized or rotated:
        out = io.BytesIO()
        rgb.save(out, format="JPEG", quality=JPEG_QUALITY)
        jpeg = out.getvalue()
    return jpeg, rgb


def _in_view_text(images: list[VisionImage], missing: int) -> str:
    """
    The face matcher's findings, as the only source of names Claude gets.

    Phrased as plain facts about the photo, so the model repeats them rather
    than reasoning about faces itself.
    """
    lines: list[str] = []
    if missing:
        lines.append(
            "A photo the user took didn't arrive (it failed to upload or expired). "
            "Say you couldn't see it."
            if missing == 1
            else f"{missing} photos the user took didn't arrive. Say you couldn't see them."
        )
    for index, image in enumerate(images, start=1):
        prefix = f"Photo {index}: " if len(images) > 1 else ""
        if not image.faces_available:
            lines.append(
                f"{prefix}Face matching is unavailable right now, so nobody in this "
                "photo can be named. Refer to any people as someone."
            )
            continue
        parts: list[str] = []
        if image.people:
            names = ", ".join(person["name"] for person in image.people)
            parts.append(f"recognized enrolled people: {names}")
        if image.unknown_faces:
            count = image.unknown_faces
            parts.append(
                "1 person not recognized (call them someone)"
                if count == 1
                else f"{count} people not recognized (call them someone)"
            )
        if not parts:
            parts.append("no recognized people")
        lines.append(prefix + "; ".join(parts) + ".")
    return f"{IN_VIEW_OPEN}\n" + "\n".join(lines) + f"\n{IN_VIEW_CLOSE}"


class VisionService:
    # Class-level for the same reason as CodingService: ToolService builds a
    # fresh VisionService for every `look` call, and those instances must see
    # the photos uploaded through the controller's instance, the event loop
    # bound at startup, and the glasses sockets registered by live turns.
    store = ImageStore()
    loop: Any = None
    # conversation_uuid -> coroutine function that sends one event down that
    # conversation's glasses socket. Present only while a glasses turn runs.
    cameras: dict[str, Callable[[dict], Awaitable[None]]] = {}

    def __init__(self, face_service: Any = None) -> None:
        self._face_service = face_service

    @property
    def face_service(self):
        if self._face_service is None:
            from src.service.face_service import FaceService

            self._face_service = FaceService()
        return self._face_service

    # ---------- wiring ----------

    @classmethod
    def bind_loop(cls, loop: Any) -> None:
        """Attach the event loop the voice sockets live on, process-wide."""
        cls.loop = loop

    @classmethod
    def register_camera(
        cls, conversation_uuid: str, send: Callable[[dict], Awaitable[None]]
    ) -> None:
        cls.cameras[str(conversation_uuid)] = send

    @classmethod
    def unregister_camera(
        cls, conversation_uuid: str, send: Callable[[dict], Awaitable[None]]
    ) -> None:
        # Only the registration this turn made; a newer turn on another
        # socket for the same conversation keeps its own.
        if cls.cameras.get(str(conversation_uuid)) is send:
            del cls.cameras[str(conversation_uuid)]

    # ---------- uploads ----------

    def ingest(self, jpeg: bytes, request_id: str | None = None) -> VisionImage:
        """
        Normalise a photo, run the face matcher over it, and keep it.

        When the upload answers a `capture_request`, the waiting `look` is
        released with the new imageId.
        """
        import numpy as np

        started = time.monotonic()
        jpeg, rgb = prepare(jpeg)
        image = VisionImage(
            image_id=uuid.uuid4().hex,
            jpeg=jpeg,
            width=rgb.width,
            height=rgb.height,
        )
        bgr = np.ascontiguousarray(np.asarray(rgb)[:, :, ::-1])
        found = self.face_service.identify(bgr)
        image.people = found.people
        image.unknown_faces = found.unknown_faces
        image.faces_available = found.available
        self.store.put(image)
        print(
            f"[vision] upload->ready ms={(time.monotonic() - started) * 1000:.0f} "
            f"size={image.width}x{image.height} bytes={len(jpeg)}"
            + (f" request={request_id}" if request_id else "")
        )
        if request_id:
            self.store.resolve(request_id, image.image_id)
        return image

    def capture_failed(self, request_id: str, reason: str | None) -> bool:
        """The phone gave up on a capture; fail the `look` waiting for it."""
        return self.store.fail(request_id, (reason or "").strip() or "unknown error")

    # ---------- what Claude sees ----------

    def content_blocks(self, image_ids: list[str]) -> list[dict[str, Any]]:
        """
        Claude content for these photos: the images, then `<in_view>`.

        Unknown or expired ids are skipped, and `<in_view>` says a photo did
        not arrive so Nova can say so instead of describing nothing.
        """
        images: list[VisionImage] = []
        missing = 0
        for image_id in dict.fromkeys(image_ids):
            image = self.store.get(image_id) if isinstance(image_id, str) else None
            if image is None:
                missing += 1
            else:
                images.append(image)
        blocks: list[dict[str, Any]] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.b64encode(image.jpeg).decode("ascii"),
                },
            }
            for image in images
        ]
        blocks.append({"type": "text", "text": _in_view_text(images, missing)})
        return blocks

    # ---------- the `look` tool ----------

    def look(self, conversation_uuid: str) -> list[dict[str, Any]]:
        """
        Tool entry point: take a photo through the user's glasses right now.

        Runs on the agent loop's worker thread. The capture request goes out
        on the glasses socket (owned by the event loop, hence
        run_coroutine_threadsafe), then this thread blocks until the phone's
        upload names the request, the phone reports a failure, or the
        timeout passes.
        """
        send = self.cameras.get(str(conversation_uuid))
        if send is None or self.loop is None:
            raise ToolExecutionError(
                "No camera is connected: the user isn't talking through the "
                "glasses right now, so you can't see anything.",
                recoverable=True,
            )

        request_id = uuid.uuid4().hex
        waiting = self.store.expect(request_id)
        started = time.monotonic()
        try:
            asyncio.run_coroutine_threadsafe(
                send(
                    {
                        "type": "capture_request",
                        "requestId": request_id,
                        "conversationId": str(conversation_uuid),
                    }
                ),
                self.loop,
            ).result(timeout=_SEND_TIMEOUT_SECONDS)
            image_id = waiting.result(timeout=LOOK_TIMEOUT_SECONDS)
        except CaptureFailed as exc:
            raise ToolExecutionError(
                f"The glasses couldn't take a photo: {exc}", recoverable=True
            ) from exc
        except FutureTimeout as exc:
            raise ToolExecutionError(
                "The glasses didn't send a photo in time, so you can't see anything "
                "right now.",
                recoverable=True,
            ) from exc
        except Exception as exc:
            raise ToolExecutionError(
                f"Couldn't reach the glasses camera: {exc}", recoverable=True
            ) from exc
        finally:
            self.store.forget(request_id)
        print(f"[vision] look request->image ms={(time.monotonic() - started) * 1000:.0f}")
        return self.content_blocks([image_id])


def is_image_block(block: Any) -> bool:
    return isinstance(block, dict) and block.get("type") == "image"
