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
   uv sync --extra qwen
   python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
   ```
   Expect `2.11.0+cu128 True NVIDIA GeForce RTX 3080`. Don't use the old
   `cu121` index: it stops at torch 2.5.1 and has no Python 3.13 wheels.
   If the driver is too old for cu128, update the driver rather than
   changing the index; cu126 is the fallback if you can't (change the index
   URL in `pyproject.toml` and run `uv lock`).

2. **The `qwen` extra** — `qwen-tts` (on PyPI since 0.1.x), the matching
   CUDA `torchaudio`, and `lameenc` for mp3 encoding, all installed by the
   `uv sync --extra qwen` in step 1. Check it:
   ```powershell
   python -c "import qwen_tts; print('qwen-tts ok')"
   ```
   **Always pass `--extra qwen` on the tower from now on** — a plain
   `uv sync` removes the extra's packages again. Import-time warnings about
   SoX not being found or flash-attn not being installed are harmless.

3. **Check the voice and language names** once weights are downloaded
   (step 5 happens automatically here):
   ```powershell
   python -c "from qwen_tts import Qwen3TTSModel; m = Qwen3TTSModel.from_pretrained('Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice', device_map='cuda:0'); print(m.get_supported_speakers()); print(m.get_supported_languages())"
   ```
   The default voice is `Ryan` (English); `Aiden` is the other English
   preset.

4. **Optional: `flash-attn`.** Qwen3-TTS, like most recent Qwen models, can
   use FlashAttention for faster inference if it's installed. It is **not**
   required — skip it unless you hit a performance wall; building it on
   Windows is its own project (prebuilt wheels exist for some
   torch/CUDA/Python combinations — check the
   [flash-attention releases](https://github.com/Dao-AILab/flash-attention/releases)
   before building from source).

5. **Weights.** `Qwen3TTSModel.from_pretrained(...)` downloads the checkpoint from
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
| `QWEN_TTS_VOICE` | `Ryan` | CustomVoice preset speaker: Vivian, Serena, Uncle_Fu, Dylan, Eric, Ryan, Aiden, Ono_Anna or Sohee (Ryan and Aiden are native English). Case-insensitive. |
| `QWEN_TTS_LANGUAGE` | `English` | Passed as `language=`; `Auto` lets the model detect it per line. |
| `QWEN_TTS_ATTN` | auto | Attention backend: `flash_attention_2` when flash-attn is installed, else `sdpa` (retried with the model's own default if it rejects that). Set explicitly to force one, or `default` to pass nothing. |
| `QWEN_TTS_DEVICE` | `cuda` | `cuda` or `cpu`. `cpu` works but is slow — only useful for testing without a GPU. |
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

## How generation works (and its latency)

`qwen-tts`'s Python API (`Qwen3TTSModel.generate_custom_voice`) returns a
whole line as `(wavs, sample_rate)`; it has no chunk-yielding streaming
call (its `non_streaming_mode=False` flag only simulates streaming *text
input*). So the provider synthesizes each line in full, then mp3-encodes
and yields it in half-second slices. Time to first audio byte is the full
generation time for that line, which is fine for a fallback that only
speaks when ElevenLabs and Cartesia are both down, but slower than they are.

## What wasn't verified

The API calls were checked against the installed `qwen-tts` 0.1.1 package
(class, `from_pretrained`, and `generate_custom_voice` signatures), and the
unit tests mock the model. Not yet measured on the tower's GPU:

- Real generation time per line on the 3080, and whether the 0.6B
  checkpoint in bfloat16 fits in the free VRAM alongside everything else.
- Whether the model accepts `sdpa` attention or falls back to its default
  (either works; the load retries automatically).
