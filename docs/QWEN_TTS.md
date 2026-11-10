# Qwen3-TTS: Nova's local TTS fallback

[Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) (Apache 2.0) runs locally on
the tower's RTX 3080 as a link in `TTSService`'s fallback chain:

```
ElevenLabs → Cartesia → Qwen3-TTS (local) → OpenAI
```

Code: `src/service/qwen_tts_service.py`, wired into the chain in
`src/service/tts_service.py`. It is optional and lazily loaded — nothing here
runs, and nothing here is even imported, unless `TTSService` reaches that link
in the chain and actually calls it.

## Why it's here

ElevenLabs and Cartesia are paid APIs that can run out of quota or lapse a
plan — a same-day problem, hence their 3-hour cooldown once that happens.
Qwen3-TTS has no quota to run out, but it does depend on the GPU actually
being free and the weights being on disk, so it gets a much shorter cooldown
(`QWEN_TTS_COOLDOWN_SECONDS`, default 60s) and falls straight through to
OpenAI if the GPU/model isn't usable.

## Install (Windows tower)

These are **not** run automatically by this change — run them by hand on the
tower when you're ready to turn this on.

1. **CUDA build of torch.** torch is already a base dependency of this repo,
   and `pyproject.toml` (`[tool.uv.sources]`) pulls it from the PyTorch
   CUDA 12.8 index on Windows, so a normal sync installs the CUDA build
   (`2.11.0+cu128`). It needs NVIDIA driver 570 or newer; `nvidia-smi`
   should show `CUDA Version: 12.8` or higher. Stop the API's uvicorn
   first, then:
   ```powershell
   nvidia-smi
   uv sync
   python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
   ```
   Expect `2.11.0+cu128 True NVIDIA GeForce RTX 3080`. Don't use the old
   `cu121` index: it stops at torch 2.5.1 and has no Python 3.13 wheels.
   If the driver is too old for cu128, update the driver rather than
   changing the index; cu126 is the fallback if you can't (change the index
   URL in `pyproject.toml` and run `uv lock`).

2. **The optional `qwen` extra** (mp3 encoding via `lameenc`):
   ```powershell
   uv pip install -e ".[qwen]"
   ```

3. **The `qwen-tts` package itself.** As of writing it is not published on
   PyPI; install it from the Qwen3-TTS repo:
   ```powershell
   git clone https://github.com/QwenLM/Qwen3-TTS.git
   cd Qwen3-TTS
   pip install -e .
   ```
   **Not verified in this change** (no CUDA GPU was available to test
   against) — confirm the package name, the installed module's import path
   (`import qwen_tts`), and the exact shape of its streaming generation call
   against whatever version you install; `qwen_tts_service._generate_pcm_chunks`
   documents the assumed API and is the one place to adjust if it differs.

4. **Optional: `flash-attn`.** Qwen3-TTS, like most recent Qwen models, can
   use FlashAttention for faster inference if it's installed. It is **not**
   required — skip it unless you hit a performance wall; building it on
   Windows is its own project (prebuilt wheels exist for some
   torch/CUDA/Python combinations — check the
   [flash-attention releases](https://github.com/Dao-AILab/flash-attention/releases)
   before building from source).

5. **Weights.** `Qwen3TTS.from_pretrained(...)` downloads the checkpoint from
   Hugging Face on first use (the lazy load in `qwen_tts_service._load_model`)
   to the default Hugging Face cache, normally
   `C:\Users\natha\.cache\huggingface\hub` on the tower. Set `HF_HOME` to
   redirect that if disk space on `C:` is tight. Default checkpoint:
   `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` (~0.6B params — picked to fit
   comfortably in the ~4.5GB of VRAM typically free on the tower's 3080
   alongside everything else already using it).

## CustomVoice, not Base

Nova uses the **CustomVoice** checkpoint (preset voices), not **Base**
(voice cloning) — a deliberate choice, not a placeholder: CustomVoice's
preset-voice API is simpler to wire and is all Nova needs. This provider
does not implement any voice-cloning plumbing; `QWEN_TTS_VOICE` only ever
selects a preset voice name on the CustomVoice checkpoint.

## Env vars

| Var | Default | Meaning |
|---|---|---|
| `QWEN_TTS_MODEL` | `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` | Hugging Face repo id. Set to a larger (e.g. 1.7B) **CustomVoice** checkpoint once more VRAM is free — see "CustomVoice, not Base" above for why this isn't a `-Base` checkpoint. |
| `QWEN_TTS_VOICE` | `default` | CustomVoice preset voice name. |
| `QWEN_TTS_DEVICE` | `cuda` | `cuda` or `cpu`. `cpu` works but is slow — only useful for testing without a GPU. |
| `QWEN_TTS_SAMPLE_RATE` | `24000` | PCM sample rate the model is assumed to produce; only change this if a different checkpoint family documents a different native rate. |
| `QWEN_TTS_MP3_BIT_RATE` | `128` | mp3 encode bit rate (kbps), matching the other providers' ~128kbps mp3 output. |
| `QWEN_TTS_COOLDOWN_SECONDS` | `60` | How long a failed Qwen3-TTS call is skipped before being retried, independent of `TTS_PROVIDER_COOLDOWN_SECONDS` (which only governs the paid providers). |
| `QWEN_TTS_WARMUP` | unset (off) | Set to `1` to load the model once at app startup (as a background task, so it never delays the app accepting traffic) instead of waiting for the first real request. |

`TTS_PROVIDER=openai` is still a full opt-out: it skips ElevenLabs, Cartesia
*and* Qwen3-TTS, same as before this change.

## Smoke test

Once the above is installed and weights have downloaded, from the repo root
on the tower:

```powershell
python -c "from src.service.qwen_tts_service import QwenTTSService; s = QwenTTSService(); open('smoke.mp3','wb').write(b''.join(s.stream_text_to_speech('Hello from Nova.')))"
```

This should produce a `smoke.mp3` you can play; if it raises instead, the
error message says what's missing (no CUDA, no `qwen-tts` package, or the
weights/checkpoint name).

## What wasn't verified

This change was written and tested with the model entirely mocked out (see
`tests/test_tts_service.py`'s `Qwen*` test classes) — there is no CUDA GPU in
the environment it was developed in. Specifically unverified against real
hardware:

- The exact Python call shape of `qwen_tts`'s streaming API
  (`qwen_tts_service._generate_pcm_chunks`).
- Real first-packet / end-to-end latency on the 3080 with ~4.5GB free VRAM,
  and whether the 0.6B checkpoint in bfloat16 actually fits alongside
  whatever else is using the GPU at the time.
- Actual mp3 encode throughput via `lameenc` keeping up with real-time audio
  generation (should be trivial — mp3 encoding is far cheaper than TTS
  inference — but not measured here).
- Whether `qwen-tts`'s package/import name matches what's assumed here; see
  the install steps above.
