"""
The live coding sessions, and the one event loop that owns them.

This is the part that makes a coding task a *thread* rather than a job. A
session outlives the request that started it: Nova can ask what it is doing,
send it a correction, interrupt it, and pick it up again tomorrow. That only
works if something holds the `ClaudeSDKClient` open between requests, and this
is that something.

Two constraints shape the design:

  - `ClaudeSDKClient` is async and long-lived, while Nova's agent loop is a
    sync generator run in a worker thread. The client therefore cannot live
    inside a tool call, which would kill it on return. Everything here runs on
    one asyncio loop that outlives every request touching it.
  - The link to Nova will drop — laptops sleep, wifi changes. So nothing here
    depends on it. Sessions keep working while disconnected, events buffer,
    and Claude Code's own on-disk session store means even a full agent
    restart can re-attach by session id rather than lose the work.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

from . import protocol, worktree
from .config import Config
from .permissions import make_guard

# How many events a session remembers for replay after a reconnect. Bounded on
# purpose: a long session emits thousands, and the authoritative record is
# Claude Code's own .jsonl on disk, not this buffer.
_REPLAY_BUFFER = 400

Sink = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass
class Session:
    id: str
    title: str
    workspace: worktree.Workspace
    client: ClaudeSDKClient
    status: str = "starting"
    seq: int = 0
    reader: asyncio.Task | None = None
    buffer: deque = field(default_factory=lambda: deque(maxlen=_REPLAY_BUFFER))
    pending_feedback: deque = field(default_factory=deque)
    last_result: dict[str, Any] | None = None

    def snapshot(self) -> dict[str, Any]:
        """What Nova needs to describe this session without reading the transcript."""
        return {
            "session_id": self.id,
            "title": self.title,
            "status": self.status,
            "seq": self.seq,
            "cwd": str(self.workspace.path),
            "repo": str(self.workspace.repo),
            "branch": self.workspace.branch,
            "pending_feedback": len(self.pending_feedback),
            "last_result": self.last_result,
        }


class SessionManager:
    def __init__(self, config: Config, sink: Sink) -> None:
        self.config = config
        self.sink = sink
        self.sessions: dict[str, Session] = {}

    # ---------- lifecycle ----------

    def _options(
        self, cwd: Path, session_id: str | None = None, resume: str | None = None
    ) -> ClaudeAgentOptions:
        sandbox: dict[str, Any] | None = None
        if self.config.sandbox:
            # The real containment. `autoAllowBashIfSandboxed` is what makes
            # unattended work possible: inside the sandbox a shell command
            # cannot reach past the workspace, so there is nothing for a
            # human to approve and nobody here to approve it.
            sandbox = {"enabled": True, "autoAllowBashIfSandboxed": True}

        return ClaudeAgentOptions(
            cwd=str(cwd),
            # Pin Claude Code's session id to the one Nova already knows.
            # Left unset the CLI mints its own, and `resume` would then be
            # handed an id resolving to nothing: the first test start had a
            # local uuid of 61d1c7fd… while the CLI was actually running
            # 7aace6e6…, so re-attaching after a restart would have silently
            # begun a fresh conversation instead of continuing the task.
            session_id=session_id,
            resume=resume,
            permission_mode=self.config.permission_mode,
            can_use_tool=make_guard(cwd),
            env=self.config.child_env(),
            model=self.config.model,
            max_budget_usd=self.config.max_budget_usd,
            sandbox=sandbox,
        )

    async def start(
        self,
        session_id: str,
        repo: str,
        instructions: str,
        title: str | None = None,
        base: str | None = None,
    ) -> dict[str, Any]:
        if session_id in self.sessions:
            raise ValueError(f"Session {session_id} is already running.")

        repo_path = worktree.resolve_repo(self.config.repos_root, repo)
        name = title or instructions
        workspace = worktree.create(
            repo_path, self.config.worktree_root, name, base=base
        )

        client = ClaudeSDKClient(self._options(workspace.path, session_id=session_id))
        await client.connect()

        session = Session(
            id=session_id,
            title=(title or instructions)[:120],
            workspace=workspace,
            client=client,
        )
        self.sessions[session_id] = session
        session.reader = asyncio.create_task(self._pump(session))

        await client.query(instructions)
        session.status = "working"
        await self._emit(session, {"type": protocol.EVT_STARTED, **session.snapshot()})
        return session.snapshot()

    async def attach(self, session_id: str, cwd: str) -> dict[str, Any]:
        """
        Re-open a session this process no longer holds.

        After an agent restart the client is gone but the conversation is not:
        Claude Code persisted it, so resuming by id continues the same thread
        rather than starting a new one that has forgotten the task.
        """
        if session_id in self.sessions:
            return self.sessions[session_id].snapshot()

        path = Path(cwd).expanduser().resolve()
        client = ClaudeSDKClient(self._options(path, resume=session_id))
        await client.connect()

        session = Session(
            id=session_id,
            title=session_id,
            workspace=worktree.Workspace(
                path=path, repo=path, branch=None, is_worktree=False
            ),
            client=client,
            status="idle",
        )
        self.sessions[session_id] = session
        session.reader = asyncio.create_task(self._pump(session))
        return session.snapshot()

    async def stop(self, session_id: str) -> dict[str, Any]:
        session = self._require(session_id)
        if session.reader is not None:
            session.reader.cancel()
        try:
            await session.client.disconnect()
        except Exception:
            pass
        session.status = "closed"
        self.sessions.pop(session_id, None)
        await self._emit(session, {"type": protocol.EVT_CLOSED, **session.snapshot()})
        return session.snapshot()

    # ---------- interaction ----------

    async def feedback(self, session_id: str, text: str, steer: bool = False) -> dict[str, Any]:
        """
        Send Nate's words into the session.

        Deliberately one entry point for both cases, because from where Nova
        stands the difference is invisible: if the agent is between turns the
        feedback starts the next one, and if it is mid-task the feedback waits
        for the turn to finish. `steer` is the exception — it cuts the current
        turn short, for when the agent is visibly going the wrong way and
        letting it finish would waste the window.
        """
        session = self._require(session_id)

        if session.status == "working" and not steer:
            session.pending_feedback.append(text)
            return {"queued": True, **session.snapshot()}

        if session.status == "working" and steer:
            await session.client.interrupt()

        await session.client.query(text)
        session.status = "working"
        return {"queued": False, **session.snapshot()}

    async def interrupt(self, session_id: str) -> dict[str, Any]:
        session = self._require(session_id)
        await session.client.interrupt()
        session.status = "idle"
        return session.snapshot()

    def replay(self, session_id: str, after_seq: int = 0) -> list[dict[str, Any]]:
        session = self._require(session_id)
        return [event for seq, event in session.buffer if seq > after_seq]

    def list(self) -> list[dict[str, Any]]:
        return [session.snapshot() for session in self.sessions.values()]

    # ---------- internals ----------

    def _require(self, session_id: str) -> Session:
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError(f"No live session {session_id}.")
        return session

    async def _emit(self, session: Session, event: dict[str, Any]) -> None:
        session.seq += 1
        event = {**event, "session_id": session.id, "seq": session.seq}
        session.buffer.append((session.seq, event))
        # A dead link must never stall a session: the buffer above is the
        # record, and the sink is best-effort delivery on top of it.
        try:
            await self.sink(event)
        except Exception:
            pass

    async def _pump(self, session: Session) -> None:
        """Drain the session's message stream for as long as it lives."""
        try:
            async for message in session.client.receive_messages():
                for event in protocol.encode(message):
                    await self._emit(session, event)
                    if event["type"] == protocol.EVT_RESULT:
                        session.last_result = event
                        session.status = "idle"
                        await self._drain_feedback(session)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            session.status = "error"
            await self._emit(
                session, {"type": protocol.EVT_ERROR, "reason": "stream", "detail": str(exc)}
            )

    async def _drain_feedback(self, session: Session) -> None:
        """A turn just ended — if Nate said something while it ran, act on it now."""
        if not session.pending_feedback:
            return
        # Collapse everything that arrived during the turn into one message:
        # three separate corrections should arrive as one instruction, not as
        # three turns each reacting to a third of the picture.
        combined = "\n\n".join(session.pending_feedback)
        session.pending_feedback.clear()
        await session.client.query(combined)
        session.status = "working"
