# WebSocket Transcribe API — Frontend Integration

This document describes the `/ws/transcribe` WebSocket protocol for the voice conversation MVP.

## Endpoints

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/ws/transcribe` | WebSocket | Voice input → transcription → Claude response → TTS audio |
| `GET /tools` | HTTP | Unchanged |

No new REST routes were added.

## Conversation ID

The backend maintains in-memory conversation history keyed by `conversationId`.

- **First turn:** omit `conversationId`; backend generates one and returns it in `done`.
- **Follow-up turns:** send the same `conversationId` on `start` (or `stop`) to continue context.
- **Persist** `conversationId` in app state or `sessionStorage` between turns and reconnects.

**v1 limitation:** history is in-memory only. A server restart clears server-side history even if the client resends an old ID.

## Client → Server

### `start`

```json
{
  "event": "start",
  "language": "en",
  "mimeType": "audio/webm",
  "conversationId": "550e8400-e29b-41d4-a716-446655440000"
}
```

`conversationId` is optional. Omit on the first conversation.

### `stop`

```json
{
  "event": "stop",
  "purpose": "turn",
  "conversationId": "550e8400-e29b-41d4-a716-446655440000"
}
```

`conversationId` on `stop` is a fallback if not sent on `start`.

Other events (`wake_greeting`, `ping`) are unchanged.

## Server → Client

### `assistant_text` (new)

The model response is generated **incrementally**, in sentence-sized chunks. Each chunk is sent as an `assistant_text` event so the chat UI can render text in real time:

```json
{
  "type": "assistant_text",
  "text": "Here is the first sentence of the reply.",
  "seq": 1,
  "conversationId": "550e8400-e29b-41d4-a716-446655440000",
  "markdownDisplay": "optional markdown string"
}
```

- `text` — plain-text sentence chunk. Append to the current assistant chat bubble in `seq` order.
- `seq` — 1-based position of the chunk within the turn.
- `conversationId` — the active conversation.
- `markdownDisplay` — **optional**; absent today. When present in the future, it will carry a markdown rendering of the content — prefer it over `text` for rich/interactive display.

**Ordering guarantee:** the `assistant_text` event for chunk N always arrives **before** the audio stream for chunk N.

### Audio streams (changed behavior)

Each sentence chunk is also sent as its own audio stream (`assistant_audio_stream_start` → `chunk`s → `assistant_audio_stream_end`, all with `role: "final"` and a unique `streamId`).

**A single turn can produce several sequential audio streams before `done`.** Queue them and play in arrival order — do not assume one stream per turn.

### `done` (changed)

```json
{
  "type": "done",
  "message": "Turn complete.",
  "conversationId": "550e8400-e29b-41d4-a716-446655440000",
  "assistantText": "Here is my answer..."
}
```

- `conversationId` — always present on successful turns. Save after the first turn.
- `assistantText` — authoritative full transcript of the turn (the `assistant_text` chunks joined together).
- `markdownDisplay` — **optional**; absent today. Reserved for a future markdown rendering of the full response.
- `iterationsUsed` — removed in v1 (single Claude turn, no tool loop).

### Removed in v1

- `assistant_progress` events (no multi-iteration tool loop yet).

### Unchanged

`ready`, `listening`, `chunk_received`, `assistant_audio_stream_start`, `assistant_audio_stream_chunk`, `assistant_audio_stream_end`, `no_speech`, `wake_greeting_done`, `wake_not_detected`, `follow_up_stopped`, `error`, `pong`.

## Recommended flow

1. Connect to `ws://<host>/ws/transcribe`.
2. Wait for `{ "type": "ready" }`.
3. Load stored `conversationId` if available.
4. Send `{ "event": "start", "conversationId": "..." }` (omit ID on first conversation).
5. Stream binary audio chunks while recording.
6. Send `{ "event": "stop", "purpose": "turn" }`.
7. Append `assistant_text` chunks to the chat UI as they arrive, and play `assistant_audio_stream_*` events for the spoken response (possibly several streams per turn — queue and play in order).
8. On `{ "type": "done" }`, save `conversationId`; `assistantText` is the authoritative full transcript if you need to reconcile the chat bubble.
9. Repeat from step 4 for follow-up turns.

## Error handling

| Event | Action |
|-------|--------|
| `{ "type": "error", "message": "Invalid conversationId." }` | Clear stored ID and retry without it |
| `{ "type": "no_speech" }` | Do not update conversation ID |
| `{ "type": "follow_up_stopped" }` | User said stop phrase; optionally clear `conversationId` for a fresh conversation |
