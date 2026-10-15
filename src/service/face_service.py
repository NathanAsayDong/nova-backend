"""
Face matching for the glasses camera, on the tower, on the CPU.

This is the ONLY thing in Nova that decides who a face belongs to. Claude is
never shown an identity it did not get from here: the vision path hands it a
plain-text list of names this matcher produced, and the prompt forbids it to
guess anyone from how they look.

What it will and will not do:
  - It only knows people Nathan enrolled, with their agreement recorded on
    the `person` row (see FaceService.create_person).
  - It stores embeddings, never photos, and only for enrolled people. A face
    it does not recognise is counted, reported as "someone", and forgotten.
  - Deleting a person deletes all of their samples (on delete cascade).

Models (opencv_zoo, Apache-2.0; fetched by scripts/fetch_face_models.py):
  YuNet finds faces and five landmarks; SFace aligns each face on those
  landmarks and turns it into a 128-d embedding. Both run through OpenCV's
  dnn module on the CPU, tens of milliseconds per frame, so they never queue
  behind ASR for the GPU.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

_MODELS_DIR = Path(__file__).resolve().parents[2] / "models" / "faces"
YUNET_PATH = _MODELS_DIR / "face_detection_yunet_2023mar.onnx"
SFACE_PATH = _MODELS_DIR / "face_recognition_sface_2021dec.onnx"

# Matching rule: the nearest enrolled person must clear MATCH_THRESHOLD in
# cosine similarity AND beat the next-nearest person by MATCH_MARGIN.
# Otherwise the face is "someone". The margin is what keeps two enrolled
# siblings from being confidently confused for each other. Both are starting
# points from SFace's published operating point (~0.363 cosine); tune them on
# real glasses photos (see the vision notes).
MATCH_THRESHOLD = 0.40
MATCH_MARGIN = 0.05

# YuNet's own confidence below which a detection is not a face at all.
DETECT_SCORE = 0.8
# Faces smaller than this (box width or height, pixels) are skipped: too few
# pixels to embed reliably, and a face that small is across the room.
MIN_FACE_PX = 40
# A face must be at least this big to be NAMED; smaller ones are counted as
# "someone". Measured on a crowded real photo: strangers' 40-52 px faces
# scored up to 0.44 against each other (above MATCH_THRESHOLD), while every
# pair of faces of 60 px or more stayed under 0.35. At conversational distance
# through the glasses' 720x1280 camera a face is well over 100 px.
NAME_MIN_FACE_PX = 60
# An enrollment sample is held to more: it becomes the reference every later
# match is measured against.
ENROLL_MIN_FACE_PX = 64

DEFAULT_CONSENT_NOTE = (
    "Nathan confirmed this person agreed to be recognized by Nova."
)


class FaceModelsMissing(RuntimeError):
    """The YuNet / SFace weights are not on disk, or OpenCV cannot load them."""


class EnrollmentError(ValueError):
    """A sample or person that cannot be enrolled; the message says why."""


class DuplicatePerson(EnrollmentError):
    """Someone by that name (any case) is already enrolled."""


class PersonNotFound(LookupError):
    pass


@dataclass
class GalleryPerson:
    person_id: int
    name: str
    # One L2-normalised row per sample.
    embeddings: np.ndarray


@dataclass
class Identification:
    """Who the matcher saw in one image. Unknown faces are a count, nothing more."""

    people: list[dict[str, Any]] = field(default_factory=list)
    unknown_faces: int = 0
    # False when the models are missing or the gallery could not be read: the
    # turn must then say matching was unavailable, not that nobody was there.
    available: bool = True


def _normalise(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm else vector


def match(
    embedding: np.ndarray,
    gallery: list[GalleryPerson],
    threshold: float = MATCH_THRESHOLD,
    margin: float = MATCH_MARGIN,
) -> tuple[GalleryPerson, float] | None:
    """
    The enrolled person this embedding belongs to, with their score, or None.

    A person's score is their best sample's cosine similarity. The winner has
    to clear `threshold` and lead the runner-up person by `margin`.
    """
    if not gallery:
        return None
    probe = _normalise(embedding)
    scored = sorted(
        (
            (float(np.max(person.embeddings @ probe)), person)
            for person in gallery
            if len(person.embeddings)
        ),
        key=lambda pair: pair[0],
        reverse=True,
    )
    if not scored:
        return None
    best_score, best = scored[0]
    if best_score < threshold:
        return None
    if len(scored) > 1 and best_score - scored[1][0] < margin:
        return None
    return best, best_score


class FaceService:
    # Class-level, like CodingService's link: ToolService and the controllers
    # each build their own instance, but there is one set of models and one
    # gallery per process. The lock serialises the OpenCV calls (the detector
    # carries per-call input size state) and gallery reloads.
    _lock = threading.Lock()
    _detector: Any = None
    _recognizer: Any = None
    _gallery: list[GalleryPerson] | None = None

    def __init__(self, dao: Any = None) -> None:
        self._dao = dao

    @property
    def dao(self):
        if self._dao is None:
            from src.dao.person_dao import PersonDao

            self._dao = PersonDao()
        return self._dao

    # ---------- models ----------

    @classmethod
    def _models(cls) -> tuple[Any, Any]:
        """Load YuNet and SFace once. Call with the lock held."""
        if cls._detector is None or cls._recognizer is None:
            if not YUNET_PATH.exists() or not SFACE_PATH.exists():
                raise FaceModelsMissing(
                    "Face models are not installed. Run "
                    "`uv run python scripts/fetch_face_models.py` on the server."
                )
            try:
                import cv2

                cls._detector = cv2.FaceDetectorYN.create(
                    str(YUNET_PATH), "", (320, 320), DETECT_SCORE, 0.3, 5000
                )
                cls._recognizer = cv2.FaceRecognizerSF.create(str(SFACE_PATH), "")
            except Exception as exc:
                raise FaceModelsMissing(f"Could not load the face models: {exc}") from exc
        return cls._detector, cls._recognizer

    @staticmethod
    def _face_size(face: np.ndarray) -> float:
        return float(min(face[2], face[3]))

    def faces(self, bgr: np.ndarray, min_px: int = MIN_FACE_PX) -> list[tuple[np.ndarray, np.ndarray]]:
        """
        Every face big enough to embed, as (detection row, unit embedding).

        A detection row is YuNet's: x, y, w, h, five landmark pairs, score.
        """
        height, width = bgr.shape[:2]
        with self._lock:
            detector, recognizer = self._models()
            detector.setInputSize((width, height))
            _, detections = detector.detect(bgr)
            found = []
            for face in detections if detections is not None else []:
                if self._face_size(face) < min_px:
                    continue
                aligned = recognizer.alignCrop(bgr, face)
                found.append((face, _normalise(recognizer.feature(aligned))))
        return found

    # ---------- gallery ----------

    @classmethod
    def invalidate(cls) -> None:
        """Drop the cached gallery; the next match reloads it."""
        with cls._lock:
            cls._gallery = None

    def gallery(self) -> list[GalleryPerson]:
        with self._lock:
            if FaceService._gallery is not None:
                return FaceService._gallery
        by_person: dict[int, tuple[str, list[np.ndarray]]] = {}
        for person_id, name, embedding in self.dao.all_samples():
            entry = by_person.setdefault(person_id, (name, []))
            entry[1].append(_normalise(np.asarray(embedding, dtype=np.float32)))
        built = [
            GalleryPerson(person_id, name, np.vstack(rows))
            for person_id, (name, rows) in by_person.items()
            if rows
        ]
        with self._lock:
            FaceService._gallery = built
        return built

    # ---------- matching ----------

    def identify(self, bgr: np.ndarray) -> Identification:
        """
        Name the enrolled people in a frame; count everyone else.

        Never raises for a missing model or an unreachable gallery: the photo
        is still worth describing, so the result is marked unavailable and
        the turn goes on without names.
        """
        started = time.monotonic()
        try:
            found = self.faces(bgr)
        except FaceModelsMissing as exc:
            print(f"[vision] face matching unavailable: {exc}")
            return Identification(available=False)
        if not found:
            return Identification()
        try:
            gallery = self.gallery()
        except Exception as exc:
            print(f"[vision] face gallery unavailable: {exc}")
            return Identification(unknown_faces=len(found), available=False)

        best_by_name: dict[str, float] = {}
        unknown = 0
        for face, embedding in found:
            if self._face_size(face) < NAME_MIN_FACE_PX:
                unknown += 1
                continue
            result = match(embedding, gallery)
            if result is None:
                unknown += 1
                continue
            person, score = result
            best_by_name[person.name] = max(score, best_by_name.get(person.name, 0.0))

        people = [
            {"name": name, "confidence": round(score, 2)}
            for name, score in sorted(best_by_name.items(), key=lambda item: -item[1])
        ]
        print(
            f"[vision] faces ms={(time.monotonic() - started) * 1000:.0f} "
            f"found={len(found)} named={len(people)} unknown={unknown}"
        )
        return Identification(people=people, unknown_faces=unknown)

    # ---------- enrollment ----------

    def list_people(self) -> list[dict[str, Any]]:
        return [self._public(person) for person in self.dao.list_people()]

    def create_person(
        self, name: str, consent: Any, consent_note: str | None = None
    ) -> dict[str, Any]:
        """
        Enroll a person. Refused unless `consent` is literally True.

        Consent is the person's agreement to be recognised, confirmed by
        Nathan when he adds them; the note saying so is stored on the row.
        """
        from src.model.person import Person

        if consent is not True:
            raise EnrollmentError(
                "Consent is required: confirm the person agreed to be recognized by Nova."
            )
        name = (name or "").strip()
        if not name:
            raise EnrollmentError("A name is required.")
        if len(name) > 80:
            raise EnrollmentError("That name is too long.")
        note = (consent_note or "").strip() or DEFAULT_CONSENT_NOTE
        try:
            person = self.dao.create(Person(name=name, consent_note=note))
        except Exception as exc:
            if "23505" in str(exc) or "duplicate" in str(exc).lower():
                raise DuplicatePerson(f"{name} is already enrolled.") from exc
            raise
        return self._public(person)

    def delete_person(self, person_id: int) -> None:
        if not self.dao.delete(person_id):
            raise PersonNotFound(f"No person with id {person_id}.")
        self.invalidate()

    def add_sample(self, person_id: int, bgr: np.ndarray) -> int:
        """
        Embed the one face in `bgr` as a sample of `person_id`; return their count.

        The photo itself is not kept, only the embedding. Refused unless the
        image holds exactly one face, and that face is big enough to be a
        good reference.
        """
        if self.dao.get(person_id) is None:
            raise PersonNotFound(f"No person with id {person_id}.")
        found = self.faces(bgr)
        if len(found) != 1:
            raise EnrollmentError(
                "No clear face found in that photo."
                if not found
                else f"Found {len(found)} faces; a sample needs exactly one."
            )
        face, embedding = found[0]
        if self._face_size(face) < ENROLL_MIN_FACE_PX:
            raise EnrollmentError("That face is too small; get closer and try again.")
        self.dao.add_sample(person_id, [float(value) for value in embedding])
        self.invalidate()
        return self.dao.count_samples(person_id)

    @staticmethod
    def _public(person: Any) -> dict[str, Any]:
        consented_at = person.consented_at
        return {
            "id": person.id,
            "name": person.name,
            "samples": person.samples,
            "consentedAt": consented_at.isoformat() if consented_at else None,
        }
