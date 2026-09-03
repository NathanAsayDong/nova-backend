"""
Coding sessions, from the tower's side.

Two audiences read this. The UI wants the event tail and enough state to draw
a panel. Nova wants a sentence it can say out loud — which is why `rollup`
exists and is maintained deterministically on every event rather than being
generated. A spoken "how's it going" has to answer in the time it takes to
say it; an LLM summary would cost a round trip and a chunk of the reply
budget to say something the counters already know.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.dao.coding_session_dao import CodingSessionDao
from src.model.coding_session import CodingEvent, CodingSession, CodingStatus

# Event types that say the session moved on rather than just chattered.
_MILESTONE_TYPES = {"started", "result", "error", "closed"}


class CodingService:
    def __init__(self) -> None:
        self.dao = CodingSessionDao()
        # Set by coding_controller once the socket layer exists; injected
        # rather than imported so the service stays testable without a live
        # websocket, and so the import graph has no cycle.
        self.link: Any = None
        self.loop: Any = None
        self.update_service: Any = None

    # ---------- commands ----------

    async def start(
        self,
        repo: str,
        instructions: str,
        title: str | None = None,
        project_id: int | None = None,
    ) -> dict:
        session_id = uuid.uuid4()
        title = (title or instructions).strip()[:120]

        # Persist before dispatching. If the Mac is asleep the row is what
        # lets Nova say "queued, waiting for your laptop" instead of losing
        # the request entirely.
        session = CodingSession(
            session_id=session_id,
            title=title,
            status=CodingStatus.STARTING,
            repo=repo,
            instructions=instructions,
            project_id=project_id,
            rollup="Starting up.",
        )
        await asyncio.to_thread(self.dao.create, session)

        if self.link is None or not self.link.connected:
            await asyncio.to_thread(
                self.dao.update,
                session_id,
                status=CodingStatus.QUEUED,
                rollup="Waiting for the Mac to come online.",
            )
            return {
                "sessionId": str(session_id),
                "status": CodingStatus.QUEUED,
                "message": (
                    "Saved the task, but the Mac agent is offline — it will need "
                    "to be started before this can run."
                ),
            }

        result = await self.link.call(
            "start",
            session_id=str(session_id),
            repo=repo,
            instructions=instructions,
            title=title,
        )
        await asyncio.to_thread(
            self.dao.update,
            session_id,
            status=CodingStatus.WORKING,
            branch=(result or {}).get("branch"),
            cwd=(result or {}).get("cwd"),
            rollup="Working.",
        )
        return {
            "sessionId": str(session_id),
            "status": CodingStatus.WORKING,
            "branch": (result or {}).get("branch"),
            "cwd": (result or {}).get("cwd"),
        }

    async def feedback(self, session_id: UUID, text: str, steer: bool = False) -> dict:
        result = await self.link.call(
            "feedback", session_id=str(session_id), text=text, steer=steer
        )
        queued = bool((result or {}).get("queued"))
        await asyncio.to_thread(
            self.dao.update,
            session_id,
            rollup=("Noted — it will pick that up after this step."
                    if queued else "Working on your feedback."),
        )
        return {"queued": queued, "sessionId": str(session_id)}

    async def stop(self, session_id: UUID) -> dict:
        try:
            await self.link.call("stop", session_id=str(session_id))
        finally:
            await asyncio.to_thread(
                self.dao.update,
                session_id,
                status=CodingStatus.CLOSED,
                closed_at=datetime.now(timezone.utc).isoformat(),
                rollup="Stopped.",
            )
        return {"sessionId": str(session_id), "status": CodingStatus.CLOSED}

    # ---------- the agent's events ----------

    def record_event(self, event: dict) -> None:
        """
        Persist one event from the Mac and fold it into the session's state.

        Called from a thread, so everything here is synchronous. Failures are
        swallowed per-event: a malformed or unexpected event should cost that
        event, never the connection carrying the rest of the session.
        """
        try:
            raw_id = event.get("session_id")
            if not raw_id:
                return
            session_id = UUID(str(raw_id))
            seq = int(event.get("seq") or 0)
            kind = str(event.get("type") or "unknown")

            session = self.dao.get(session_id)
            if session is None:
                return  # an event for a session this tower never started

            self.dao.append_event(
                CodingEvent(session_id=session_id, seq=seq, type=kind, payload=event)
            )

            fields: dict[str, Any] = {"last_seq": max(seq, session.last_seq)}
            fields["rollup"] = self._rollup(session_id, session, event)

            if kind == "started":
                fields.update(
                    status=CodingStatus.WORKING,
                    branch=event.get("branch"),
                    cwd=event.get("cwd"),
                )
            elif kind == "result":
                fields.update(
                    status=CodingStatus.ERROR if event.get("is_error") else CodingStatus.IDLE,
                    last_result=(event.get("result") or "")[:4000],
                )
            elif kind == "error":
                fields["status"] = CodingStatus.ERROR
            elif kind == "closed":
                fields.update(
                    status=CodingStatus.CLOSED,
                    closed_at=datetime.now(timezone.utc).isoformat(),
                )

            self.dao.update(session_id, **fields)

            if kind in _MILESTONE_TYPES:
                self.dao.prune_events(session_id)
        except Exception as exc:
            print(f"Could not record coding event: {exc}")

    def _rollup(self, session_id: UUID, session: CodingSession, event: dict) -> str:
        """
        One sentence describing where the session is, rebuilt from counters.

        Deliberately dumb and deliberately cheap. It reads the recent event
        tail and counts, which costs one query and no tokens — so Nova can
        answer out loud the instant it is asked, however long the task has
        been running.
        """
        kind = event.get("type")
        if kind == "result":
            if event.get("is_error"):
                return "It stopped with an error."
            return (event.get("result") or "Finished.").strip().split("\n")[0][:200]
        if kind == "error":
            if event.get("reason") == "rate_limit":
                return "Paused — the Claude usage window is used up."
            return f"It hit a problem: {str(event.get('detail') or '')[:120]}"
        if kind == "closed":
            return "Stopped."

        recent = self.dao.events(session_id, after_seq=max(0, session.last_seq - 60))
        edits = sum(1 for e in recent if e.payload.get("tool") in ("Edit", "Write", "NotebookEdit"))
        commands = sum(1 for e in recent if e.payload.get("tool") == "Bash")

        if kind == "tool":
            artifact = event.get("artifact") or {}
            target = artifact.get("title") or event.get("tool") or "something"
            doing = f"Working on {target}"
        elif kind == "text":
            doing = (event.get("text") or "").strip().split("\n")[0][:160] or "Working"
        else:
            doing = "Working"

        tally = []
        if edits:
            tally.append(f"{edits} edit{'s' if edits != 1 else ''}")
        if commands:
            tally.append(f"{commands} command{'s' if commands != 1 else ''}")
        return f"{doing}. {' and '.join(tally)} so far." if tally else f"{doing}."

    # ---------- the tool surface ----------
    #
    # ToolService refuses async callables, and rightly: the agent loop is a
    # sync generator on a worker thread and cannot await. But the websocket to
    # the Mac lives on the app's event loop, so these hop across — schedule the
    # coroutine there, block this thread for the answer.
    #
    # `loop` is set at startup in main.py. Without it the tools degrade to a
    # clear error rather than a mysterious hang.

    def _run(self, coro, timeout: float = 120.0):
        if self.loop is None:
            raise RuntimeError(
                "The coding agent link is not initialised on this server."
            )
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=timeout)

    def start_coding_task(
        self,
        repo: str,
        instructions: str,
        title: str | None = None,
        project_id: int | None = None,
        conversation_uuid: str | None = None,
    ) -> dict:
        """Tool entry point: hand a coding task to the Mac."""
        return self._run(
            self.start(
                repo=repo,
                instructions=instructions,
                title=title,
                project_id=project_id,
            )
        )

    def send_feedback_to_coding_task(
        self,
        session_id: str,
        text: str,
        steer: bool = False,
        conversation_uuid: str | None = None,
    ) -> dict:
        return self._run(self.feedback(UUID(session_id), text, steer=steer))

    def stop_coding_task(
        self, session_id: str, conversation_uuid: str | None = None
    ) -> dict:
        return self._run(self.stop(UUID(session_id)))

    def check_coding_task(
        self, session_id: str | None = None, conversation_uuid: str | None = None
    ) -> dict:
        """
        What the sessions are doing right now.

        Reads the database, not the Mac — so it answers instantly, works while
        the laptop is asleep, and costs nothing. With no session_id it
        summarises everything still open, which is the shape of the question
        actually asked out loud ("how's that going?").
        """
        if session_id:
            session = self.dao.get(UUID(session_id))
            if session is None:
                return {"found": False}
            recent = self.dao.events(UUID(session_id), after_seq=max(0, session.last_seq - 12))
            return {
                "found": True,
                **self._to_dict(session),
                "recent": [
                    {"type": e.type, "text": e.payload.get("text"), "tool": e.payload.get("tool")}
                    for e in recent
                ],
            }
        return {"sessions": [self._to_dict(s) for s in self.dao.list_open()]}

    # ---------- reads ----------

    def list_sessions(self, limit: int = 20) -> list[dict]:
        return [self._to_dict(s) for s in self.dao.list_recent(limit=limit)]

    def get_session_detail(self, session_id: UUID, after_seq: int = 0) -> dict | None:
        session = self.dao.get(session_id)
        if session is None:
            return None
        events = self.dao.events(session_id, after_seq=after_seq)
        return {
            "session": self._to_dict(session),
            "events": [
                {"seq": e.seq, "type": e.type, "payload": e.payload} for e in events
            ],
        }

    @staticmethod
    def _to_dict(session: CodingSession) -> dict:
        return {
            "sessionId": str(session.session_id),
            "title": session.title,
            "status": session.status,
            "repo": session.repo,
            "branch": session.branch,
            "cwd": session.cwd,
            "instructions": session.instructions,
            "rollup": session.rollup,
            "lastResult": session.last_result,
            "lastSeq": session.last_seq,
            "projectId": session.project_id,
            "createdAt": session.created_at.isoformat() if session.created_at else None,
            "updatedAt": session.updated_at.isoformat() if session.updated_at else None,
        }
