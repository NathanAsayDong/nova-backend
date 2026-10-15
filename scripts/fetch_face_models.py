"""
Download the face detector and recognizer that FaceService runs on.

Both come from opencv_zoo (Apache-2.0) and run on the CPU through OpenCV's
dnn module, so they never contend with ASR for the GPU:

  YuNet   face_detection_yunet_2023mar.onnx    finds faces and 5 landmarks
  SFace   face_recognition_sface_2021dec.onnx  128-d embedding per aligned face

The URLs are pinned to one opencv_zoo commit and every file is checked against
its SHA-256 before it is moved into place, so a changed or truncated download
never reaches the matcher. Files already present with the right hash are left
alone, which makes this safe to re-run.

Run with:
    uv run python scripts/fetch_face_models.py
"""

import hashlib
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models" / "faces"

_ZOO_COMMIT = "47534e27c9851bb1128ccc0102f1145e27f23f98"
_ZOO_MEDIA = f"https://media.githubusercontent.com/media/opencv/opencv_zoo/{_ZOO_COMMIT}/models"

MODELS = [
    (
        "face_detection_yunet_2023mar.onnx",
        f"{_ZOO_MEDIA}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    ),
    (
        "face_recognition_sface_2021dec.onnx",
        f"{_ZOO_MEDIA}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    ),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(name: str, url: str, expected: str) -> bool:
    target = MODELS_DIR / name
    if target.exists() and sha256(target) == expected:
        print(f"ok:         {name} (already present)")
        return True

    print(f"fetching:   {name}")
    with tempfile.NamedTemporaryFile(dir=MODELS_DIR, delete=False, suffix=".part") as temp:
        partial = Path(temp.name)
    try:
        urllib.request.urlretrieve(url, partial)
        actual = sha256(partial)
        if actual != expected:
            print(f"MISMATCH:   {name}\n  expected {expected}\n  got      {actual}")
            return False
        partial.replace(target)
        print(f"ok:         {name}")
        return True
    finally:
        if partial.exists():
            partial.unlink()


def main() -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    results = [fetch(name, url, expected) for name, url, expected in MODELS]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
