"""
Report what speech-to-text will actually run on, without loading a model.

Checks each link in the order it fails in practice: which provider this machine
resolves to, whether the NVIDIA library wheels are installed and loadable,
whether CTranslate2 can see a GPU, and the device/precision that results. Use
it when transcription silently falls back to CPU, or fails with a message like
"Library cublas64_12.dll is not found or cannot be loaded".

Run with:
    uv run python scripts/check_asr_env.py
"""

import platform
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

from src.service.asr_service import (  # noqa: E402
    _nvidia_wheel_dll_dirs,
    _platform_default_provider,
    _resolve_whisper_device,
    _setup_cuda_libraries,
    missing_cuda_libraries,
)


def main() -> int:
    print(f"platform          : {sys.platform} / {platform.machine()}")
    print(f"provider for auto : {_platform_default_provider()}")

    if sys.platform == "win32":
        report = _setup_cuda_libraries()
        dll_dirs = report["wheel_dirs"] or [str(d) for d in _nvidia_wheel_dll_dirs()]
        print(f"nvidia wheel dirs : {dll_dirs or 'NOT INSTALLED (run `uv sync`)'}")
        print(f"preloaded DLLs    : {report['preloaded'] or 'none'}")
        if report["unloadable"]:
            print("failed to load    :")
            for name, error in report["unloadable"].items():
                print(f"  - {name}: {error}")
        missing = missing_cuda_libraries()
        print(f"required, missing : {missing or 'none — all loadable'}")

    try:
        import ctranslate2

        count = ctranslate2.get_cuda_device_count()
        print(f"ctranslate2       : {ctranslate2.__version__}, CUDA devices: {count}")
    except Exception as exc:  # noqa: BLE001 - report rather than crash
        print(f"ctranslate2       : unavailable ({exc})")

    device, compute_type = _resolve_whisper_device()
    print(f"resolved device   : {device} ({compute_type})")

    if device == "cpu" and sys.platform == "win32":
        print(
            "\nTranscription will run on the CPU. That works, but to use the GPU: "
            "confirm `uv sync` installed nvidia-cublas-cu12 and nvidia-cudnn-cu12, "
            "and that `nvidia-smi` reports a driver supporting CUDA 12."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
