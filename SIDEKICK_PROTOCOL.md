# Sidekick protocol: `WS /ws/sidekick`

In Sidekick mode Nova overhears the conversation around the glasses and decides on its own when to chime in. The server side is in:
- `src/controller/sidekick_controller.py` (the socket)
- `src/service/sidekick_service.py` (the session, the gate, the direct-turn counter)

This file records the protocol as built.

## Connecting
- **Auth:** the same bearer auth as `/ws/transcribe`. Send `Authorization: Bearer <token>` or `?token=`. The path is gated, not exempt. Without a valid session the server closes the socket with code 4401 before accepting it, which Starlette surfaces as HTTP 403.
- **Ready:** on accept the server immediately sends `{"type":"ready","message":"Connected. Send start, then utterances."}`. Count the socket as open only after this message.

## Client → server
| Message | Meaning |
|---|---|
| `{"event":"start","conversationId"?}` | Begin a session. The server replies `{"type":"sidekick_started","conversationId"}`. |
| `{"event":"utterance_start"}` | An overheard utterance begins. |
| binary frames | Raw 16 kHz mono Int16 LE PCM for the open utterance. |
| `{"event":"utterance_end"}` | The utterance is complete; the server transcribes it. |
| `{"event":"interrupted"}` | The user said "Hey Nova" (or a direct turn is under way). Stop speaking the current interjection. |
| `{"event":"stop"}` | End the session. The server replies `sidekick_ended {reason:"stopped"}`. |
| `{"event":"ping"}` | The server replies `{"type":"pong"}`. |

### `start`
- **With `conversationId`:** that conversation is the session's conversation.
- **Without one, or if the conversation is closed:** a new conversation id is minted. Its row is created on the first interjection.
- **Invalid UUID:** the server replies `error {message:"Invalid conversationId."}` and no session starts.
- **A second `start` while a session is running** (e.g. the app reconnecting) keeps the session and repeats `sidekick_started` with the same id.

### Utterances
- **Audio before `start`:** `utterance_start` without a session gets `error {message:"Send start first."}`.
- **Size cap:** an utterance is capped at 60 s of audio (1,920,000 bytes). Frames beyond that are dropped.
- **Where audio is ignored:** binary frames outside `utterance_start` … `utterance_end`.
- **Empty audio:** an empty utterance is ignored.

## Server → client
| Message | When |
|---|---|
| `{"type":"heard","text"}` | After each utterance is transcribed. Not sent when the transcript is empty. |
| `{"type":"speech_text","text","role","conversationId"}` | A line of the interjection, as on `/ws/transcribe`. `role` is `"status"` or `"final"`. |
| `assistant_audio_stream_start` / `_chunk` / `_end` | The spoken audio, produced by `stream_tts_audio` exactly as on `/ws/transcribe`. |
| `{"type":"tool_call","tool","input","conversationId"}` | A tool is about to run during an interjection, usually `look`. |
| `{"type":"done","message","conversationId","assistantText"}` | The interjection finished (or was interrupted, see below). |
| `{"type":"silent","conversationId"}` | Sent **instead of** `done` when the turn passed and said nothing. |
| `{"type":"capture_request","requestId","conversationId"}` | `look` wants a photo. Answer through `POST /vision/images?requestId=` or `POST /vision/capture-failed`, as for glasses turns. |
| `{"type":"sidekick_ended","reason"}` | `reason` is one of `"be_quiet"`, `"timeout"`, `"stopped"` or `"error"`. |
| `{"type":"error","message"}` | Something failed; the session continues unless `sidekick_ended` follows. |

### Interjections
- **Event order:** `speech_text` / audio / `tool_call` events, then exactly one `done` or `silent`.
- **Not sent:** `text`, `text_final`, `status_text` and `artifact` events, because Sidekick has no screen.
- **Interrupted:** after `interrupted` the server cancels the audio in flight and sends no more `speech_text` or audio for that interjection. The turn finishes unheard on the server, so the remark is still persisted whole, and is then reported as `done` with `"message":"Interrupted."`.
  - An audio stream cut off this way may get a `_start` with no matching `_end`.
- **Message text:** a normal finish has `"message":"Remark complete."`.

## Server behaviour
- **Transcription:**
  - Each utterance is wrapped as WAV (`audio_file_bytes`) and transcribed with `transcribe_serialized(..., background=True)`. It queues behind spoken turns on the shared ASR lock.
  - Utterances are transcribed one at a time, in arrival order.
  - The receive loop never blocks: transcription, the gate and interjections all run as tasks behind one send lock.
- **Gate:**
  - Every heard utterance restarts a 1.5 s lull timer. When it fires, the gate model is asked.
  - The gate is a separate `ClaudeService` instance with `MODEL = "claude-haiku-5-5"` and web search off, called through `get_response`. It returns strict JSON `{"speak": bool, "why": str, "look": bool}`.
  - It reads the last 2 minutes of transcript, Nova's recent remarks, and the seconds since the last remark.
  - Any reply that is not that exact shape counts as `speak:false`.
- **The gate is skipped when:**
  - **Cooldown:** less than 60 s have passed since the last remark. A `silent` pass does not start the cooldown.
  - **Interjection running:** another interjection is still in progress.
  - **Direct turn:** a `/ws/transcribe` turn is in progress (`SidekickService.active_direct_turns > 0`). The gate waits until the turn is over, and the counter is checked again before an interjection starts.
- **Interjection:**
  - `agent_loop.conversation_loop_events(<overheard> excerpt + "Chime in now.", session_conversation, prompt_source=SIDEKICK_PROMPT)` runs on the default model.
  - When the gate set `look:true`, the prompt also asks for the look tool.
- **`[[pass]]`:**
  - When the model has nothing worth saying, it replies with the sentinel.
  - `AgentLoop` holds a Sidekick round's live events while the text could still be the sentinel. If it is, the held events are dropped, the turn is removed from history, no rows are written (not even tool rows from a `look`), and `{"type":"silent"}` is yielded.
- **Camera:**
  - `VisionService.cameras[str(session_conversation)]` points at this socket for the whole session and is unregistered when the session ends or the socket closes.
  - It is also re-registered at the start of each interjection (see deviations).
- **Be quiet:** an overheard line containing "Nova, be quiet", "be quiet Nova", "Nova quiet", "Nova shut up", "Nova hush", "stop sidekick", "sidekick off", "turn off sidekick", "end sidekick" or "Nova stop listening" ends the session with `be_quiet`. That line's `heard` is sent first.
- **Cap:** the server ends the session with `timeout` after 60 minutes.
- **Privacy:**
  - The overheard transcript and remarks live only in memory.
  - They are wiped whenever the session ends: `stop`, `be_quiet`, `timeout`, `error`, or the socket closing.
  - Only interjections are persisted, as two rows:
    - `(Sidekick, overheard) <the last line heard>`
    - Nova's remark
  - The full excerpt the model read is replaced by that one line in the in-memory history too, once the turn ends.
- **After `sidekick_ended`:** the socket stays open. Further utterances need a new `start`. (The iOS app disconnects at this point anyway.)

## Prompt and tools
- **`SIDEKICK_PROMPT`:**
  - Spoken and screenless.
  - Overhearing, not addressed. Speak only when there is clear value; one or two sentences; an occasional dry joke.
  - Includes the `[[pass]]` instruction, the one-sided-transcript note, `look` guidance, and the same `<in_view>` naming rules as the glasses.
- **`look`** is offered only to `GLASSES_PROMPT` and `SIDEKICK_PROMPT`. Chat, the voice UI, SMS and calls no longer see it.
- **`SIDEKICK_PROMPT` also excludes** `start_meeting` and `end_session`.

## Deviations from the brief and additions
1. **Camera re-registration:** the session registers the camera at `start` as specified, and also re-registers it before each interjection. A direct glasses turn on `/ws/transcribe` in the same conversation registers its own camera and then unregisters it when its turn ends. Without the re-registration, the sidekick's registration would be gone.
2. **`persist_prompt_as`:** this is a new optional kwarg on `AgentLoop.conversation_loop_events`. It keeps the 2-minute overheard excerpt out of the database and out of lingering in-memory history, so that "only interjection turns are persisted" holds.
3. **What a Sidekick turn persists:**
   - With `[[pass]]`, nothing is persisted, including the prompt row and any tool rows. To make this possible, a Sidekick turn writes its rows only after Nova's reply is known, instead of writing the user row behind.
   - Failure fallbacks ("I hit a time limit…") are still persisted and spoken, as for other media.
4. **Interrupted reporting:** `interrupted` does not abort the model turn, because its worker thread cannot be cancelled safely. It silences the turn instead, and ends with `done` (`message:"Interrupted."`), so the client always gets a terminal event.
5. **`sidekick_ended` with `"error"`:** sent only if the socket handler itself fails unexpectedly. A failed interjection sends `error` and the session continues. A failed gate call or transcription is logged and skipped.
6. **Extra error case:** `utterance_start` before `start` gets `error {message:"Send start first."}`.
7. **Existing test changed:** in `tests/test_vision.py`, the image-turn helper now runs under `GLASSES_PROMPT`, because `look` is no longer offered to chat turns.

## Tests
`tests/test_sidekick.py` covers:
- gate JSON parsing, the gate model and cooldown
- lull debounce
- `[[pass]]`: `silent` and nothing persisted, including after a `look`
- prompt redaction
- the direct-turn counter on `/ws/transcribe` and its effect on the gate
- the `look` exclusion
- auth gating

It also runs `/ws/sidekick` end to end:
- `heard` → gate → spoken interjection → `done`
- `silent`
- `tool_call`
- `interrupted`
- be quiet
- `stop`
- the 60-minute cap
- the transcript is wiped on close
