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
import re
from collections import deque
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    get_session_messages,
    list_sessions,
)

from . import protocol, worktree
from .config import Config
from .permissions import make_guard

# How many events a session remembers for replay after a reconnect. Bounded on
# purpose: a long session emits thousands, and the authoritative record is
# Claude Code's own .jsonl on disk, not this buffer.
_REPLAY_BUFFER = 400

Sink = Callable[[dict[str, Any]], Awaitable[None]]

# How much of one message to keep when flattening a transcript for Nova.
# Whole tool payloads are what make a transcript enormous, and they are the
# least useful part of "remind me what we discussed".
_MESSAGE_CHARS = 700


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _ms_to_iso(value: Any) -> str | None:
    """Claude Code stores timestamps as epoch-millisecond strings."""
    millis = _as_int(value)
    if millis is None:
        return None
    return datetime.fromtimestamp(millis / 1000, tz=timezone.utc).isoformat()


_TOOL_MARKERS = ("[tool result]",)


def _is_prose(text: str) -> bool:
    """Whether a flattened message says anything a person wrote or read."""
    if not text:
        return False
    remaining = text
    for marker in _TOOL_MARKERS:
        remaining = remaining.replace(marker, "")
    # "[used Edit]" and friends are generated markers, not speech.
    remaining = re.sub(r"\[used [^\]]+\]", "", remaining)
    return bool(remaining.strip())


def _flatten(message: Any) -> dict[str, Any]:
    """
    One stored message, reduced to something worth reading.

    Content arrives as a list of blocks (text, tool_use, tool_result) or as a
    bare string. Tool traffic is named but not quoted: knowing the agent ran
    Edit on a file is context, and the diff it wrote is noise here.
    """
    data = message if isinstance(message, dict) else message.__dict__
    body = data.get("message") or {}
    content = body.get("content")

    if isinstance(content, str):
        text = content
    else:
        parts: list[str] = []
        for block in content or []:
            block = block if isinstance(block, dict) else getattr(block, "__dict__", {})
            kind = block.get("type")
            if kind == "text":
                parts.append(str(block.get("text") or ""))
            elif kind == "tool_use":
                parts.append(f"[used {block.get('name')}]")
            elif kind == "tool_result":
                parts.append("[tool result]")
        text = "\n".join(part for part in parts if part.strip())

    text = text.strip()
    if len(text) > _MESSAGE_CHARS:
        text = text[:_MESSAGE_CHARS] + "…"

    return {"role": body.get("role") or data.get("type"), "text": text}


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
        isolate: bool = False,
    ) -> dict[str, Any]:
        """
        Open a new session against a repo.

        By default the session works in the repo's ACTUAL working tree, which
        is the point: Nate has that directory open in an editor, and work that
        lands anywhere else is work he cannot see happening. A worktree would
        be safer and was the original design, but "safer somewhere he isn't
        looking" is not what this is for.

        `isolate=True` still cuts a worktree, for the occasional change too
        risky to make under a live editor.

        The cost of sharing the tree is that two agents in it would fight, so
        a repo admits one session at a time — see `_conflicting_session`.
        """
        if session_id in self.sessions:
            raise ValueError(f"Session {session_id} is already running.")

        repo_path = worktree.resolve_repo(self.config.repos_root, repo)
        name = title or instructions

        if isolate:
            workspace = worktree.create(
                repo_path, self.config.worktree_root, name, base=base
            )
        else:
            existing = self._conflicting_session(repo_path)
            if existing is not None:
                raise ValueError(
                    f"'{existing.title}' is already working in {repo_path.name}. "
                    f"Two agents in one working tree overwrite each other — "
                    f"send feedback to that task, stop it, or start this one "
                    f"with isolate=true to get its own worktree."
                )
            # branch=None: whatever is checked out is what we work on. Nova
            # switching branches under a live IDE would be its own outage.
            workspace = worktree.Workspace(
                path=repo_path, repo=repo_path, branch=None, is_worktree=False
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

    async def attach(
        self,
        session_id: str,
        repo: str | None = None,
        cwd: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        """
        Take up a conversation this process does not hold.

        Two callers, one mechanism. After an agent restart the client is gone
        but the conversation is not, so resuming by id continues the task
        rather than starting one that has forgotten it. And a thread Nate
        started himself in the desktop app is, from here, the same thing: a
        session id and a directory. Resuming it means Nova picks up a
        conversation already in progress, with all of its context, instead of
        being told about it second-hand.
        """
        if session_id in self.sessions:
            return self.sessions[session_id].snapshot()

        if cwd:
            path = Path(cwd).expanduser().resolve()
        elif repo:
            path = worktree.resolve_repo(self.config.repos_root, repo)
        else:
            raise ValueError("attach needs either a repo or a cwd.")
        client = ClaudeSDKClient(self._options(path, resume=session_id))
        await client.connect()

        session = Session(
            id=session_id,
            title=title or session_id,
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

    # ---------- reading Claude Code's own history ----------
    #
    # Everything below reads the .jsonl store under ~/.claude/projects that
    # Claude Code keeps for every session on this machine, whichever surface
    # created it. Nova did not write those and cannot: the desktop app, the
    # CLI and this agent all append to the same store, so a thread Nate has
    # been having in the app for a week is readable here with no export step.
    #
    # Both SDK calls are synchronous and read from disk — a 4 MB, 950-message
    # transcript comes back in about 30 ms — so they need no thread and no
    # await.

    def claude_sessions(self, repo: str, limit: int = 25) -> list[dict[str, Any]]:
        """Every Claude Code thread for a repo, newest first."""
        path = worktree.resolve_repo(self.config.repos_root, repo)
        found = list_sessions(directory=str(path), limit=limit)
        live = set(self.sessions)

        rows: list[dict[str, Any]] = []
        for info in found:
            data = info if isinstance(info, dict) else info.__dict__
            session_id = str(data.get("session_id") or "")
            rows.append(
                {
                    "session_id": session_id,
                    # custom_title is what Nate named it; summary is what
                    # Claude Code inferred. Prefer his.
                    "title": data.get("custom_title") or data.get("summary"),
                    "first_prompt": data.get("first_prompt"),
                    "git_branch": data.get("git_branch"),
                    "cwd": data.get("cwd"),
                    "last_modified": _ms_to_iso(data.get("last_modified")),
                    "created_at": _ms_to_iso(data.get("created_at")),
                    "size_bytes": _as_int(data.get("file_size")),
                    # Whether this agent is already holding it open, which
                    # decides whether Nova attaches or just talks to it.
                    "attached": session_id in live,
                }
            )
        return rows

    def transcript(
        self,
        session_id: str,
        repo: str,
        limit: int = 20,
        offset: int | None = None,
        prose_only: bool = True,
    ) -> dict[str, Any]:
        """
        A readable window onto one thread.

        Defaults to the TAIL, because "what have I been talking to Claude
        about" almost always means the recent part, and because a long thread
        cannot go anywhere near a model's context whole — the one that
        prompted this is 956 messages. `offset` pages backwards from there.
        """
        path = worktree.resolve_repo(self.config.repos_root, repo)
        stored = get_session_messages(session_id, directory=str(path))

        flat = [_flatten(m) for m in stored]
        # Drop the tool churn. A long agentic thread is mostly Edit / Bash /
        # tool_result pairs, and the tail of one is "[used Bash]" — true, and
        # useless for "what have I been discussing with Claude". Filtering
        # before windowing is what makes the last 20 the last 20 things SAID
        # rather than the last 20 things logged.
        if prose_only:
            flat = [m for m in flat if _is_prose(m["text"])]

        total = len(flat)
        limit = max(1, min(limit, 100))
        start = total - limit if offset is None else max(0, offset)
        window = flat[start : start + limit]

        return {
            "session_id": session_id,
            "cwd": str(path),
            "total_messages": total,
            "total_including_tool_traffic": len(stored),
            "offset": start,
            "messages": window,
        }

    # ---------- internals ----------

    def _conflicting_session(self, path: Path) -> Session | None:
        """A live session already working in this directory, if any."""
        for session in self.sessions.values():
            if session.status in ("closed", "error"):
                continue
            if session.workspace.path == path:
                return session
        return None

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
