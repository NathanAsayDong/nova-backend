"""
Coverage for Nova's glasses camera: photo upload and normalisation, what the
agent loop sends Claude for a photo, the `look` tool's round trip through the
glasses socket, and the face matcher and enrollment rules.

Everything here runs offline. The face models are faked (FaceService.faces is
patched) except where a test says otherwise; the real YuNet/SFace check is a
manual step on the tower (see the vision notes).
"""

import asyncio
import base64
import io
import threading
import time
import unittest
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from src.controller import faces_controller, vision_controller
from src.harness.agent_loop import AgentLoop
from src.model.message import MessageRole
from src.model.person import Person
from src.model.tool import Tool
from src.service.claude_service import TurnStream
from src.service.face_service import (
    MATCH_MARGIN,
    MATCH_THRESHOLD,
    EnrollmentError,
    FaceService,
    GalleryPerson,
    Identification,
    PersonNotFound,
    match,
)
from src.service.tool_service import ToolExecutionError, ToolService
from src.service import vision_service as vision_module
from src.service.vision_service import (
    ImageStore,
    InvalidImage,
    VisionImage,
    VisionService,
    prepare,
)


def jpeg(width: int, height: int, orientation: int | None = None, color=(200, 30, 30)) -> bytes:
    image = Image.new("RGB", (width, height), color)
    out = io.BytesIO()
    if orientation is None:
        image.save(out, format="JPEG", quality=90)
    else:
        exif = Image.Exif()
        exif[0x0112] = orientation
        image.save(out, format="JPEG", quality=90, exif=exif)
    return out.getvalue()


def unit(vector) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float32)
    return vector / np.linalg.norm(vector)


def face_row(size: float) -> np.ndarray:
    """A YuNet detection row (x, y, w, h, 10 landmark coords, score)."""
    return np.array([0, 0, size, size] + [0] * 10 + [0.95], dtype=np.float32)


class FakeFaceService:
    def __init__(self, result: Identification | None = None):
        self.result = result or Identification()
        self.seen_shapes: list[tuple] = []

    def identify(self, bgr):
        self.seen_shapes.append(bgr.shape)
        return self.result


# ---------- prepare ----------


class PrepareTests(unittest.TestCase):
    def test_a_small_upright_photo_passes_through_untouched(self):
        data = jpeg(640, 480)
        out, rgb = prepare(data)
        self.assertEqual(out, data)
        self.assertEqual(rgb.size, (640, 480))

    def test_the_long_edge_is_capped_at_1280(self):
        out, rgb = prepare(jpeg(2560, 1440))
        self.assertEqual(rgb.size, (1280, 720))
        with Image.open(io.BytesIO(out)) as reread:
            self.assertEqual(reread.size, (1280, 720))

    def test_exif_orientation_is_applied(self):
        # Orientation 6: stored landscape, meant to be shown rotated 90°.
        out, rgb = prepare(jpeg(400, 300, orientation=6))
        self.assertEqual(rgb.size, (300, 400))
        with Image.open(io.BytesIO(out)) as reread:
            self.assertEqual(reread.size, (300, 400))
            self.assertIn(reread.getexif().get(0x0112, 1), (1, None))

    def test_non_jpeg_is_refused(self):
        png = io.BytesIO()
        Image.new("RGB", (10, 10)).save(png, format="PNG")
        with self.assertRaises(InvalidImage):
            prepare(png.getvalue())
        with self.assertRaises(InvalidImage):
            prepare(b"not an image")
        with self.assertRaises(InvalidImage):
            prepare(b"")


# ---------- store and content ----------


class ImageStoreTests(unittest.TestCase):
    def test_images_expire(self):
        store = ImageStore(ttl=60)
        image = VisionImage("a", b"x", 1, 1)
        store.put(image)
        self.assertIs(store.get("a"), image)
        image.created_at -= 61
        self.assertIsNone(store.get("a"))

    def test_resolve_and_fail_release_a_waiter_once(self):
        store = ImageStore()
        waiting = store.expect("r1")
        self.assertTrue(store.resolve("r1", "img"))
        self.assertEqual(waiting.result(timeout=1), "img")
        self.assertFalse(store.resolve("r1", "img2"))
        failing = store.expect("r2")
        self.assertTrue(store.fail("r2", "glasses folded"))
        with self.assertRaises(vision_module.CaptureFailed):
            failing.result(timeout=1)
        self.assertFalse(store.fail("unknown", "x"))


class ContentBlocksTests(unittest.TestCase):
    def setUp(self):
        self.saved = VisionService.store
        VisionService.store = ImageStore()
        self.addCleanup(setattr, VisionService, "store", self.saved)

    def test_images_come_first_then_the_in_view_note(self):
        VisionService.store.put(
            VisionImage(
                "i1", b"\xff\xd8jpeg", 10, 10,
                people=[{"name": "Tom", "confidence": 0.71}], unknown_faces=1,
            )
        )
        blocks = VisionService().content_blocks(["i1"])
        self.assertEqual([b["type"] for b in blocks], ["image", "text"])
        self.assertEqual(blocks[0]["source"]["media_type"], "image/jpeg")
        self.assertEqual(base64.b64decode(blocks[0]["source"]["data"]), b"\xff\xd8jpeg")
        note = blocks[1]["text"]
        self.assertTrue(note.startswith("<in_view>") and note.endswith("</in_view>"))
        self.assertIn("Tom", note)
        self.assertIn("1 person not recognized", note)

    def test_unknown_ids_say_the_photo_did_not_arrive(self):
        blocks = VisionService().content_blocks(["gone"])
        self.assertEqual([b["type"] for b in blocks], ["text"])
        self.assertIn("didn't arrive", blocks[0]["text"])

    def test_unavailable_matching_names_nobody(self):
        VisionService.store.put(VisionImage("i2", b"x", 1, 1, faces_available=False))
        note = VisionService().content_blocks(["i2"])[-1]["text"]
        self.assertIn("unavailable", note)


# ---------- HTTP ----------


class VisionRoutesTests(unittest.TestCase):
    def setUp(self):
        self.saved_store = VisionService.store
        VisionService.store = ImageStore()
        self.faces = FakeFaceService(
            Identification(people=[{"name": "Tom", "confidence": 0.66}], unknown_faces=2)
        )
        self.service = VisionService(face_service=self.faces)
        patcher = patch.object(vision_controller, "vision_service", self.service)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(setattr, VisionService, "store", self.saved_store)
        app = FastAPI()
        app.include_router(vision_controller.router)
        self.client = TestClient(app)

    def post(self, body: bytes, content_type="image/jpeg", query=""):
        return self.client.post(
            f"/vision/images{query}", content=body, headers={"content-type": content_type}
        )

    def test_upload_round_trip(self):
        response = self.post(jpeg(1920, 1080))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual((body["width"], body["height"]), (1280, 720))
        self.assertEqual(body["people"], [{"name": "Tom", "confidence": 0.66}])
        self.assertEqual(body["unknownFaces"], 2)
        # The matcher saw the normalised frame, as BGR rows x cols x 3.
        self.assertEqual(self.faces.seen_shapes, [(720, 1280, 3)])
        self.assertIsNotNone(VisionService.store.get(body["imageId"]))

    def test_upload_answers_a_waiting_capture_request(self):
        waiting = VisionService.store.expect("req-1")
        body = self.post(jpeg(64, 64), query="?requestId=req-1").json()
        self.assertEqual(waiting.result(timeout=1), body["imageId"])

    def test_refuses_non_jpeg_bad_and_oversized_bodies(self):
        self.assertEqual(self.post(b"x", content_type="image/png").status_code, 415)
        self.assertEqual(self.post(b"not a jpeg").status_code, 400)
        self.assertEqual(self.post(b"").status_code, 400)
        big = b"\xff" * (vision_module.MAX_UPLOAD_BYTES + 1)
        self.assertEqual(self.post(big).status_code, 413)

    def test_capture_failed_releases_the_waiter(self):
        waiting = VisionService.store.expect("req-2")
        response = self.client.post(
            "/vision/capture-failed", json={"requestId": "req-2", "reason": "no glasses"}
        )
        self.assertEqual(response.json(), {"resolved": True})
        with self.assertRaises(vision_module.CaptureFailed):
            waiting.result(timeout=1)
        self.assertEqual(
            self.client.post("/vision/capture-failed", json={}).status_code, 400
        )


# ---------- the look tool ----------


class LookToolTests(unittest.TestCase):
    """
    One asyncio loop on a background thread stands in for the app's loop (the
    test_coding_service MacShell pattern); `look` runs on the test thread the
    way it runs on the agent's worker thread.
    """

    @classmethod
    def setUpClass(cls):
        cls._saved = (VisionService.loop, dict(VisionService.cameras), VisionService.store)
        cls.loop = asyncio.new_event_loop()
        cls._thread = threading.Thread(target=cls.loop.run_forever, daemon=True)
        cls._thread.start()
        VisionService.bind_loop(cls.loop)

    @classmethod
    def tearDownClass(cls):
        cls.loop.call_soon_threadsafe(cls.loop.stop)
        cls._thread.join(timeout=2)
        cls.loop.close()
        VisionService.loop, cameras, VisionService.store = cls._saved
        VisionService.cameras.clear()
        VisionService.cameras.update(cameras)

    def setUp(self):
        VisionService.store = ImageStore()
        VisionService.cameras.clear()
        self.conversation = str(uuid4())
        self.sent: list[dict] = []

    def register(self, on_request):
        async def send(payload: dict) -> None:
            self.sent.append(payload)
            on_request(payload)

        VisionService.register_camera(self.conversation, send)
        return send

    def test_look_resolves_with_the_uploaded_photo(self):
        service = VisionService(face_service=FakeFaceService())

        def phone(payload):
            # The phone uploads a moment later, from another thread.
            threading.Timer(
                0.05, service.ingest, args=(jpeg(32, 32), payload["requestId"])
            ).start()

        self.register(phone)
        blocks = VisionService().look(self.conversation)
        self.assertEqual(self.sent[0]["type"], "capture_request")
        self.assertEqual(self.sent[0]["conversationId"], self.conversation)
        self.assertEqual([b["type"] for b in blocks], ["image", "text"])

    def test_look_times_out_cleanly(self):
        self.register(lambda payload: None)
        started = time.monotonic()
        with patch.object(vision_module, "LOOK_TIMEOUT_SECONDS", 0.2):
            with self.assertRaises(ToolExecutionError) as caught:
                VisionService().look(self.conversation)
        self.assertTrue(caught.exception.recoverable)
        self.assertIn("in time", str(caught.exception))
        self.assertLess(time.monotonic() - started, 2)
        # The abandoned request is not left behind for a late upload to find.
        self.assertFalse(VisionService.store.resolve(self.sent[0]["requestId"], "late"))

    def test_capture_failure_fails_the_tool_at_once(self):
        self.register(
            lambda payload: VisionService().capture_failed(payload["requestId"], "folded")
        )
        with self.assertRaises(ToolExecutionError) as caught:
            VisionService().look(self.conversation)
        self.assertIn("folded", str(caught.exception))

    def test_no_glasses_socket_is_a_recoverable_error(self):
        with self.assertRaises(ToolExecutionError) as caught:
            VisionService().look(self.conversation)
        self.assertTrue(caught.exception.recoverable)
        self.assertIn("No camera", str(caught.exception))

    def test_a_turn_only_unregisters_its_own_camera(self):
        old = self.register(lambda payload: None)
        new = self.register(lambda payload: None)
        VisionService.unregister_camera(self.conversation, old)
        self.assertIs(VisionService.cameras[self.conversation], new)
        VisionService.unregister_camera(self.conversation, new)
        self.assertNotIn(self.conversation, VisionService.cameras)


# ---------- agent loop ----------


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeToolUseBlock:
    id: str
    name: str
    input: dict
    type: str = "tool_use"


@dataclass
class FakeMessage:
    content: list
    stop_reason: str = "end_turn"


class FakeConversationService:
    def __init__(self):
        self.recorded: list = []

    def ensure_open_conversation(self, conversation_uuid):
        return SimpleNamespace(uuid=conversation_uuid, id=1, is_closed=False, project_id=None)

    def load_history(self, conversation):
        return []

    def record_message(self, conversation, role, content):
        self.recorded.append((role, content))


IMAGE = {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "AAAA"}}
IN_VIEW = {"type": "text", "text": "<in_view>\nrecognized enrolled people: Tom.\n</in_view>"}


class AgentLoopImageTests(unittest.TestCase):
    def setUp(self):
        self.loop = AgentLoop()
        self.loop.memory_retrieval_enabled = False
        self.tools: list[Tool] = []
        tool_service = ToolService.__new__(ToolService)
        tool_service.tool_dao = SimpleNamespace(get_all=lambda: self.tools)
        self.loop.tool_service = tool_service
        self.conversations = FakeConversationService()
        self.loop.conversation_service = self.conversations
        self.conversation_id = uuid4()
        self.requests: list[list] = []
        self.replies: list[FakeMessage] = []

        def fake_stream(prompt, role=None, context=None, tools=None, system=None, mcp_servers=None):
            # Snapshot: history is mutated after the request goes out.
            self.requests.append([dict(m) for m in context])
            return TurnStream.completed(self.replies.pop(0))

        self.loop.claude_service.stream_response = fake_stream

    def turn(self, prompt, images=None, reply="Looks like a mug."):
        self.replies.append(FakeMessage(content=[FakeTextBlock(text=reply)]))
        return list(
            self.loop.conversation_loop_events(prompt, self.conversation_id, images=images)
        )

    def test_the_user_message_puts_images_before_the_words(self):
        self.turn("what do you see?", images=[IMAGE, IN_VIEW])
        sent = self.requests[0][-1]
        self.assertEqual(sent["role"], "user")
        self.assertEqual([b["type"] for b in sent["content"]], ["image", "text", "text"])
        self.assertEqual(sent["content"][-1]["text"], "what do you see?")

    def test_only_words_and_a_photo_note_are_persisted(self):
        self.turn("who is this?", images=[IMAGE, IN_VIEW])
        role, content = self.conversations.recorded[0]
        self.assertEqual(role, MessageRole.USER)
        self.assertTrue(content.startswith("who is this?"))
        self.assertIn("[photo]", content)
        self.assertIn("Tom", content)
        self.assertNotIn("AAAA", content)
        self.assertNotIn("<in_view>", content)

    def test_a_follow_up_keeps_the_latest_photo(self):
        self.turn("what is it?", images=[IMAGE, IN_VIEW])
        self.turn("what colour is it?")
        history = self.requests[1]
        self.assertTrue(AgentLoop._has_image(history[0]))

    def test_a_new_photo_strips_the_old_one(self):
        self.turn("what is it?", images=[IMAGE, IN_VIEW])
        self.turn("and this?", images=[IMAGE, IN_VIEW])
        history = self.loop.conversations[self.conversation_id]
        self.assertFalse(AgentLoop._has_image(history[0]))
        self.assertIn({"type": "text", "text": "[photo]"}, history[0]["content"])
        self.assertTrue(AgentLoop._has_image(history[2]))

    def test_list_tool_results_pass_through_as_content_blocks(self):
        self.tools = [
            Tool(
                id=1,
                name="look",
                description="see",
                config={
                    "type": "service_method",
                    "callable_path": "src.service.vision_service.VisionService.look",
                    "input_schema": {"type": "object", "properties": {}},
                    "context_kwargs": ["conversation_uuid"],
                },
            )
        ]
        self.loop.tool_service.call_tool = lambda tool, arguments, context=None: [IMAGE, IN_VIEW]
        self.replies.append(
            FakeMessage(
                content=[
                    FakeTextBlock(text="Taking a look."),
                    FakeToolUseBlock(id="t1", name="look", input={}),
                ],
                stop_reason="tool_use",
            )
        )
        self.turn("read that sign", reply="It says exit.")
        tool_message = self.requests[1][-1]
        result = tool_message["content"][0]
        self.assertEqual(result["type"], "tool_result")
        self.assertEqual(result["content"], [IMAGE, IN_VIEW])
        persisted = [c for r, c in self.conversations.recorded if r == MessageRole.TOOL]
        self.assertNotIn("AAAA", persisted[0])
        self.assertIn("[photo]", persisted[0])

    def test_non_block_lists_are_still_json(self):
        self.assertEqual(AgentLoop._tool_result_content([1, 2]), "[1, 2]")
        self.assertEqual(AgentLoop._tool_result_content([]), "[]")
        self.assertEqual(AgentLoop._tool_result_content({"a": 1}), '{"a": 1}')


# ---------- face matcher ----------


class MatchTests(unittest.TestCase):
    def setUp(self):
        self.tom = GalleryPerson(1, "Tom", np.vstack([unit([1, 0, 0]), unit([1, 0.1, 0])]))
        self.ann = GalleryPerson(2, "Ann", np.vstack([unit([0, 1, 0])]))

    def probe(self, cosine_to_tom: float, toward=(0, 0, 1)) -> np.ndarray:
        other = unit(toward)
        return unit(cosine_to_tom * unit([1, 0, 0]) + np.sqrt(1 - cosine_to_tom**2) * other)

    def test_a_clear_match_is_named(self):
        person, score = match(self.probe(0.8), [self.tom, self.ann])
        self.assertEqual(person.name, "Tom")
        self.assertAlmostEqual(score, 0.8, places=2)

    def test_below_threshold_is_someone(self):
        self.assertIsNone(match(self.probe(MATCH_THRESHOLD - 0.02), [self.tom, self.ann]))
        self.assertIsNotNone(match(self.probe(MATCH_THRESHOLD + 0.02), [self.tom, self.ann]))

    def test_too_close_to_a_second_person_is_someone(self):
        tom = GalleryPerson(1, "Tom", unit([1, 0, 0])[None, :])
        # Halfway between Tom and Ann: both clear the threshold, neither leads.
        between = unit([1, 1, 0.2])
        self.assertIsNone(match(between, [tom, self.ann]))
        # Nudged toward Tom past the margin, he is named.
        leaning = unit([1, 1 - 3 * MATCH_MARGIN, 0.2])
        person, _ = match(leaning, [tom, self.ann])
        self.assertEqual(person.name, "Tom")

    def test_an_empty_gallery_names_nobody(self):
        self.assertIsNone(match(unit([1, 0, 0]), []))


class FakePersonDao:
    def __init__(self):
        self.people: dict[int, Person] = {}
        self.samples: list[tuple[int, list[float]]] = []
        self.next_id = 1

    def list_people(self):
        return [
            Person(**p.model_dump(exclude={"samples"}), samples=self.count_samples(p.id))
            for p in self.people.values()
        ]

    def get(self, id):
        return self.people.get(id)

    def create(self, person):
        if any(p.name.lower() == person.name.lower() for p in self.people.values()):
            raise Exception("duplicate key value violates unique constraint (23505)")
        stored = Person(id=self.next_id, name=person.name, consent_note=person.consent_note)
        self.people[self.next_id] = stored
        self.next_id += 1
        return stored

    def delete(self, id):
        if self.people.pop(id, None) is None:
            return False
        self.samples = [s for s in self.samples if s[0] != id]
        return True

    def add_sample(self, person_id, embedding):
        self.samples.append((person_id, embedding))

    def count_samples(self, person_id):
        return sum(1 for s in self.samples if s[0] == person_id)

    def all_samples(self):
        return [(pid, self.people[pid].name, emb) for pid, emb in self.samples]


class FaceServiceTests(unittest.TestCase):
    def setUp(self):
        FaceService.invalidate()
        self.addCleanup(FaceService.invalidate)
        self.dao = FakePersonDao()
        self.service = FaceService(dao=self.dao)
        self.frame = np.zeros((10, 10, 3), dtype=np.uint8)

    def with_faces(self, faces):
        return patch.object(FaceService, "faces", lambda self, bgr, min_px=40: faces)

    def test_enrollment_requires_explicit_consent(self):
        for consent in (None, False, "true", 1):
            with self.assertRaises(EnrollmentError):
                self.service.create_person("Tom", consent)
        with self.assertRaises(EnrollmentError):
            self.service.create_person("  ", True)
        person = self.service.create_person("Tom", True)
        self.assertEqual(person["name"], "Tom")
        self.assertTrue(self.dao.people[person["id"]].consent_note)

    def test_samples_need_exactly_one_clear_face(self):
        person = self.service.create_person("Tom", True)
        with self.with_faces([]):
            with self.assertRaises(EnrollmentError):
                self.service.add_sample(person["id"], self.frame)
        two = [(face_row(120), unit([1, 0, 0])), (face_row(120), unit([0, 1, 0]))]
        with self.with_faces(two):
            with self.assertRaises(EnrollmentError):
                self.service.add_sample(person["id"], self.frame)
        with self.with_faces([(face_row(50), unit([1, 0, 0]))]):
            with self.assertRaises(EnrollmentError):
                self.service.add_sample(person["id"], self.frame)
        with self.with_faces([(face_row(120), unit([1, 0, 0]))]):
            self.assertEqual(self.service.add_sample(person["id"], self.frame), 1)
        self.assertEqual(len(self.dao.samples), 1)
        with self.assertRaises(PersonNotFound):
            self.service.add_sample(999, self.frame)

    def test_identify_names_enrolled_people_and_counts_the_rest(self):
        person = self.service.create_person("Tom", True)
        self.dao.add_sample(person["id"], [1.0, 0.0, 0.0])
        faces = [
            (face_row(150), unit([1, 0.05, 0])),   # Tom
            (face_row(150), unit([0, 0, 1])),      # a stranger
            (face_row(45), unit([1, 0, 0])),       # Tom-like, but too small to name
        ]
        with self.with_faces(faces):
            found = self.service.identify(self.frame)
        self.assertEqual([p["name"] for p in found.people], ["Tom"])
        self.assertEqual(found.unknown_faces, 2)
        self.assertTrue(found.available)
        # Strangers leave no trace.
        self.assertEqual(len(self.dao.samples), 1)

    def test_deleting_a_person_forgets_their_face(self):
        person = self.service.create_person("Tom", True)
        self.dao.add_sample(person["id"], [1.0, 0.0, 0.0])
        with self.with_faces([(face_row(150), unit([1, 0, 0]))]):
            self.assertEqual(len(self.service.identify(self.frame).people), 1)
            self.service.delete_person(person["id"])
            found = self.service.identify(self.frame)
        self.assertEqual(found.people, [])
        self.assertEqual(found.unknown_faces, 1)
        self.assertEqual(self.dao.samples, [])

    def test_missing_models_mark_matching_unavailable(self):
        from src.service import face_service as face_module

        with patch.object(
            FaceService,
            "faces",
            lambda self, bgr, min_px=40: (_ for _ in ()).throw(face_module.FaceModelsMissing("x")),
        ):
            found = self.service.identify(self.frame)
        self.assertFalse(found.available)


class FacesRoutesTests(unittest.TestCase):
    def setUp(self):
        FaceService.invalidate()
        self.addCleanup(FaceService.invalidate)
        self.dao = FakePersonDao()
        patcher = patch.object(faces_controller, "face_service", FaceService(dao=self.dao))
        patcher.start()
        self.addCleanup(patcher.stop)
        app = FastAPI()
        app.include_router(faces_controller.router)
        self.client = TestClient(app)

    def test_people_lifecycle(self):
        self.assertEqual(self.client.get("/faces/people").json(), [])
        self.assertEqual(
            self.client.post("/faces/people", json={"name": "Tom"}).status_code, 400
        )
        self.assertEqual(
            self.client.post("/faces/people", json={"name": "Tom", "consent": False}).status_code,
            400,
        )
        created = self.client.post("/faces/people", json={"name": "Tom", "consent": True})
        self.assertEqual(created.status_code, 200)
        person_id = created.json()["id"]
        self.assertEqual(
            self.client.post("/faces/people", json={"name": "tom", "consent": True}).status_code,
            409,
        )
        listed = self.client.get("/faces/people").json()
        self.assertEqual(listed[0]["name"], "Tom")
        self.assertEqual(listed[0]["samples"], 0)
        self.assertIn("consentedAt", listed[0])
        self.assertEqual(self.client.delete(f"/faces/people/{person_id}").status_code, 200)
        self.assertEqual(self.client.delete(f"/faces/people/{person_id}").status_code, 404)

    def test_samples_are_422_unless_one_face(self):
        person_id = self.client.post(
            "/faces/people", json={"name": "Tom", "consent": True}
        ).json()["id"]
        post = lambda: self.client.post(
            f"/faces/people/{person_id}/samples",
            content=jpeg(200, 200),
            headers={"content-type": "image/jpeg"},
        )
        with patch.object(FaceService, "faces", lambda self, bgr, min_px=40: []):
            self.assertEqual(post().status_code, 422)
        two = [(face_row(120), unit([1, 0, 0])), (face_row(120), unit([0, 1, 0]))]
        with patch.object(FaceService, "faces", lambda self, bgr, min_px=40: two):
            self.assertEqual(post().status_code, 422)
        one = [(face_row(120), unit([1, 0, 0]))]
        with patch.object(FaceService, "faces", lambda self, bgr, min_px=40: one):
            response = post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"samples": 1})
        missing = self.client.post(
            "/faces/people/999/samples",
            content=jpeg(200, 200),
            headers={"content-type": "image/jpeg"},
        )
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()
