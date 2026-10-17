"""
WS /ws/sidekick: Nova overhears and chimes in on its own.

The glasses app streams every utterance that was not addressed to Nova here
("Hey Nova, …" still goes to /ws/transcribe as a direct turn). Each one is
transcribed at background priority, added to the session's in-memory
transcript, and echoed as `heard`. After a lull the gate model is asked
whether a remark would help; when it says yes, a full agent turn runs under
SIDEKICK_PROMPT and is spoken with the same events a voice turn uses.

Unlike /ws/transcribe, the receive loop never blocks on a turn: transcription,
the gate and interjections all run as tasks, writing to the socket behind one
send lock, so `interrupted` and `stop` are read the moment they arrive.

The protocol, as the iOS app relies on it, is in SIDEKICK_PROTOCOL.md.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import time
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from prompting.prompt_source_prompt import PromptSourceEnum
from src.controller import nova_controller
from src.controller.audio_ws import audio_file_bytes, transcribe_serialized
from src.harness.streaming import iter_in_thread
from src.service import sidekick_service as sidekick
from src.service.sidekick_service import (
    GateDecision,
    SidekickGate,
    SidekickService,
    SidekickSession,
    has_be_quiet_phrase,
)
from src.service.vision_service import VisionService

router = APIRouter(tags=["sidekick"])
gate = SidekickGate()

PCM_MIME = "audio/pcm;rate=16000;channels=1"
LANGUAGE = "en"
# One utterance is at most this much audio (60 s of 16 kHz mono Int16); the
# rest is dropped rather than buffered without bound.
MAX_UTTERANCE_BYTES = 60 * 16000 * 2
# How often a gate that is waiting out a direct turn looks again.
DIRECT_TURN_POLL_SECONDS = 0.25


def _remove(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def transcribe_utterance(pcm: bytes) -> str:
    """Overheard audio to text, queued behind any turn a person is waiting on."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
        temp.write(audio_file_bytes(PCM_MIME, pcm))
        path = Path(temp.name)
    try:
        return (transcribe_serialized(path, LANGUAGE, background=True) or "").strip()
    finally:
        _remove(path)


class SidekickConnection:
    """One socket's worth of Sidekick: the session and the tasks serving it."""

    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket
        self.send_lock = asyncio.Lock()
        self.session: SidekickSession | None = None
        self.utterance: list[bytes] | None = None
        self.utterance_bytes = 0
        self.utterances: asyncio.Queue[bytes] = asyncio.Queue()
        self.transcriber: asyncio.Task | None = None
        self.gate_task: asyncio.Task | None = None
        self.interjection: asyncio.Task | None = None
        self.interrupted = False
        self.speaker: asyncio.Task | None = None
        self.cap_task: asyncio.Task | None = None
        # One reference for the camera registry: it unregisters by identity,
        # and every `self.send` access makes a new bound method.
        self.camera = self.send

    # ---------- sending ----------

    async def send(self, payload: dict) -> None:
        async with self.send_lock:
            await self.websocket.send_json(payload)

    async def try_send(self, payload: dict) -> None:
        """For background tasks: a closed socket is the receive loop's problem."""
        try:
            await self.send(payload)
        except Exception:
            pass

    # ---------- session lifecycle ----------

    async def start(self, payload: dict) -> None:
        if self.session is not None:
            # A repeated start (the app reconnecting) keeps the session.
            await self.send(
                {
                    "type": "sidekick_started",
                    "conversationId": str(self.session.conversation_uuid),
                }
            )
            return

        raw = payload.get("conversationId")
        conversation_uuid: UUID | None = None
        if raw:
            try:
                conversation_uuid = UUID(str(raw))
            except ValueError:
                await self.send({"type": "error", "message": "Invalid conversationId."})
                return
            existing = await asyncio.to_thread(
                nova_controller.conversation_service.get_conversation, conversation_uuid
            )
            if existing is not None and existing.is_closed:
                conversation_uuid = None
        if conversation_uuid is None:
            conversation_uuid = nova_controller.agent_loop.new_conversation_id()

        self.session = SidekickSession(conversation_uuid)
        # The glasses are this session's camera for as long as it lasts, so
        # `look` works in the middle of an interjection.
        VisionService.register_camera(str(conversation_uuid), self.camera)
        self.transcriber = asyncio.create_task(self._transcribe_loop())
        self.cap_task = asyncio.create_task(self._cap())
        print(f"[sidekick] started in {conversation_uuid}")
        await self.send(
            {"type": "sidekick_started", "conversationId": str(conversation_uuid)}
        )

    async def end(self, reason: str, notify: bool = True) -> None:
        """
        End the session: stop every task, forget the transcript.

        The socket stays open; the client may start again or hang up.
        """
        session = self.session
        if session is None:
            return
        self.session = None
        current = asyncio.current_task()
        for task in (self.transcriber, self.gate_task, self.interjection, self.cap_task):
            if task is not None and task is not current and not task.done():
                task.cancel()
        self.transcriber = self.gate_task = self.interjection = self.cap_task = None
        self.utterance = None
        self.utterances = asyncio.Queue()
        VisionService.unregister_camera(str(session.conversation_uuid), self.camera)
        session.wipe()
        print(f"[sidekick] ended ({reason})")
        if notify:
            await self.try_send({"type": "sidekick_ended", "reason": reason})

    async def _cap(self) -> None:
        await asyncio.sleep(sidekick.SESSION_MAX_SECONDS)
        await self.end("timeout")

    # ---------- utterances ----------

    async def utterance_start(self) -> None:
        if self.session is None:
            await self.send({"type": "error", "message": "Send start first."})
            return
        self.utterance = []
        self.utterance_bytes = 0

    def audio(self, data: bytes) -> None:
        if self.utterance is None or not data:
            return
        if self.utterance_bytes + len(data) > MAX_UTTERANCE_BYTES:
            return
        self.utterance.append(data)
        self.utterance_bytes += len(data)

    def utterance_end(self) -> None:
        if self.utterance is None or self.session is None:
            return
        pcm = b"".join(self.utterance)
        self.utterance = None
        if pcm:
            self.utterances.put_nowait(pcm)

    async def _transcribe_loop(self) -> None:
        """One utterance at a time, so the transcript keeps the order they were said."""
        while True:
            pcm = await self.utterances.get()
            try:
                text = await asyncio.to_thread(transcribe_utterance, pcm)
            except Exception as exc:
                print(f"[sidekick] transcription failed: {exc}")
                continue
            if not text or self.session is None:
                continue
            await self.try_send({"type": "heard", "text": text})
            if has_be_quiet_phrase(text):
                await self.end("be_quiet")
                return
            self.session.add(text)
            self._schedule_gate()

    # ---------- deciding ----------

    def _schedule_gate(self) -> None:
        # Every new utterance restarts the lull; only the last one in a burst
        # reaches the gate.
        if self.gate_task is not None and not self.gate_task.done():
            self.gate_task.cancel()
        self.gate_task = asyncio.create_task(self._gate_after_lull())

    async def _gate_after_lull(self) -> None:
        await asyncio.sleep(sidekick.LULL_SECONDS)
        while SidekickService.direct_turn_active():
            await asyncio.sleep(DIRECT_TURN_POLL_SECONDS)

        session = self.session
        if session is None:
            return
        if self.interjection is not None and not self.interjection.done():
            return
        if session.cooling_down():
            return
        transcript = session.recent()
        if not transcript:
            return

        try:
            decision = await asyncio.to_thread(
                gate.decide, transcript, session.seconds_since_remark(), session.remarks
            )
        except Exception as exc:
            print(f"[sidekick] gate failed: {exc}")
            return
        print(
            f"[sidekick] gate speak={decision.speak} look={decision.look} why={decision.why!r}"
        )
        if not decision.speak or self.session is not session:
            return
        # The user may have woken Nova while the gate was thinking.
        if SidekickService.direct_turn_active():
            return
        self.interjection = asyncio.create_task(self._interject(session, decision))

    # ---------- speaking ----------

    def interrupt(self) -> None:
        """
        "Hey Nova" over an interjection: go quiet now.

        The turn itself is left to finish unheard on its worker thread, so
        what Nova was saying is still persisted whole; only the speaking and
        the events stop.
        """
        if self.interjection is not None and not self.interjection.done():
            self.interrupted = True
            if self.speaker is not None and not self.speaker.done():
                self.speaker.cancel()

    async def _interject(self, session: SidekickSession, decision: GateDecision) -> None:
        conversation_uuid = session.conversation_uuid
        conversation_id = str(conversation_uuid)
        self.interrupted = False
        # A direct glasses turn in the same conversation registers and then
        # unregisters itself as the camera; take it back.
        VisionService.register_camera(conversation_id, self.camera)

        event_stream = nova_controller.agent_loop.conversation_loop_events(
            session.interjection_prompt(decision),
            conversation_uuid,
            prompt_source=PromptSourceEnum.SIDEKICK_PROMPT,
            persist_prompt_as=session.persisted_prompt(),
        )

        speech_queue: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()

        async def speak_queued_lines() -> None:
            tts_available = True
            previous_line: str | None = None
            while True:
                item = await speech_queue.get()
                if item is None:
                    return
                if not tts_available or self.interrupted:
                    continue
                line, line_role = item
                tts_available = await nova_controller.stream_tts_audio(
                    self.websocket,
                    line,
                    role=line_role,
                    send_lock=self.send_lock,
                    previous_text=previous_line,
                )
                previous_line = line

        speaker = self.speaker = asyncio.create_task(speak_queued_lines())
        silent = False
        final_text: str | None = None
        spoken: list[str] = []
        try:
            async for event in iter_in_thread(event_stream):
                event_type = event.get("type")
                if event_type == "silent":
                    silent = True
                elif event_type == "text_final":
                    final_text = event["text"]
                if self.interrupted:
                    continue
                if event_type == "speech_text":
                    role = event.get("role", "final")
                    spoken.append(event["text"])
                    await self.send(
                        {
                            "type": "speech_text",
                            "text": event["text"],
                            "role": role,
                            "conversationId": conversation_id,
                        }
                    )
                    speech_queue.put_nowait((event["text"], role))
                elif event_type == "tool_call":
                    await self.send(
                        {
                            "type": "tool_call",
                            "tool": event.get("tool"),
                            "input": event.get("input"),
                            "conversationId": conversation_id,
                        }
                    )
                # text / status_text / artifact are for screens; there is none.
        except asyncio.CancelledError:
            speaker.cancel()
            raise
        except Exception as exc:
            print(f"[sidekick] interjection failed: {exc}")
            speaker.cancel()
            await self.try_send(
                {"type": "error", "message": f"Sidekick remark failed: {exc}"}
            )
            return
        finally:
            speech_queue.put_nowait(None)

        # Every queued line is spoken before the remark is reported done. A
        # speaker cancelled by an interruption just ends here.
        await asyncio.gather(speaker, return_exceptions=True)
        if silent:
            await self.try_send({"type": "silent", "conversationId": conversation_id})
            return
        said = final_text if final_text is not None else " ".join(spoken)
        session.note_remark(said)
        await self.try_send(
            {
                "type": "done",
                "message": "Interrupted." if self.interrupted else "Remark complete.",
                "conversationId": conversation_id,
                "assistantText": said,
            }
        )


@router.websocket("/ws/sidekick")
async def sidekick_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json(
        {
            "type": "ready",
            "message": "Connected. Send start, then utterances.",
        }
    )
    connection = SidekickConnection(websocket)
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            data = message.get("bytes")
            if data is not None:
                connection.audio(data)
                continue

            text = message.get("text")
            if text is None:
                continue
            try:
                payload = json.loads(text)
            except ValueError:
                await connection.send({"type": "error", "message": "Invalid JSON."})
                continue
            event = payload.get("event") if isinstance(payload, dict) else None

            if event == "start":
                await connection.start(payload)
            elif event == "utterance_start":
                await connection.utterance_start()
            elif event == "utterance_end":
                connection.utterance_end()
            elif event == "interrupted":
                connection.interrupt()
            elif event == "stop":
                await connection.end("stopped")
            elif event == "ping":
                await connection.send({"type": "pong"})
            else:
                await connection.send(
                    {"type": "error", "message": f"Unknown event: {event}"}
                )
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        print(f"[sidekick] socket failed: {exc}")
        await connection.end("error")
    finally:
        # However the socket went, the overheard transcript goes with it.
        await connection.end("closed", notify=False)
