"""
The wire contract between this agent and Nova.

Commands come down, events go up, and both are plain JSON so the tower can
persist them without knowing anything about the SDK's dataclasses.

Events are deliberately shaped to match what Nova already renders: a `text`
event is prose for the transcript, and a `tool` event carries an
`artifact` whose kind is one of the three the chat UI already knows how to
draw — 'diff', 'file', 'terminal'. Nothing new had to be invented on the
display side; the mapping is in `_artifact_for`.
"""

from __future__ import annotations

from typing import Any

# Commands (Nova -> agent)
CMD_START = "start"
CMD_FEEDBACK = "feedback"
CMD_INTERRUPT = "interrupt"
CMD_STOP = "stop"
CMD_REPLAY = "replay"
CMD_LIST = "list"
# Claude Code's own history on this Mac — threads Nova did not start, including
# the ones Nate has been having in the desktop app.
CMD_CLAUDE_SESSIONS = "claude_sessions"
CMD_TRANSCRIPT = "transcript"
CMD_ATTACH = "attach"
# A shell command, run on this Mac. Nova's run_terminal_command routes here
# rather than to the tower.
CMD_EXEC = "exec"

# Events (agent -> Nova)
EVT_HELLO = "hello"
EVT_STARTED = "started"
EVT_TEXT = "text"
EVT_THINKING = "thinking"
EVT_TOOL = "tool"
EVT_RESULT = "result"
EVT_RATE_LIMIT = "rate_limit"
EVT_ERROR = "error"
EVT_CLOSED = "closed"

# Tools whose output is worth showing. Everything else (Glob, Grep, TodoWrite,
# the hundred Reads a session does) is noise in a transcript — it is still in
# the session .jsonl if anyone wants it, but it does not need to travel.
_SHOWN_TOOLS = {"Edit", "Write", "NotebookEdit", "Bash", "Task", "WebFetch"}


def _truncate(value: str, limit: int = 4000) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + f"\n… [{len(value) - limit} more characters]"


def _artifact_for(tool: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Map a Claude Code tool call onto one of Nova's three artifact kinds."""
    if tool in ("Edit", "NotebookEdit"):
        path = str(payload.get("file_path") or payload.get("notebook_path") or "")
        old = str(payload.get("old_string", ""))
        new = str(payload.get("new_string", ""))
        body = "\n".join(
            ["--- " + path, "+++ " + path]
            + [f"-{line}" for line in old.splitlines()]
            + [f"+{line}" for line in new.splitlines()]
        )
        return {"kind": "diff", "title": path or "edit", "content": _truncate(body)}
    if tool == "Write":
        path = str(payload.get("file_path", ""))
        return {
            "kind": "file",
            "title": path or "file",
            "content": _truncate(str(payload.get("content", ""))),
        }
    if tool == "Bash":
        return {
            "kind": "terminal",
            "title": _truncate(str(payload.get("description") or "command"), 120),
            "content": _truncate(str(payload.get("command", ""))),
        }
    return None


def encode(message: Any) -> list[dict[str, Any]]:
    """
    Turn one SDK message into zero or more wire events.

    Zero is a normal outcome: most of what a coding session emits is
    bookkeeping the transcript is better off without.
    """
    kind = type(message).__name__
    events: list[dict[str, Any]] = []

    if kind == "AssistantMessage":
        for block in getattr(message, "content", []) or []:
            block_kind = type(block).__name__
            if block_kind == "TextBlock":
                text = (getattr(block, "text", "") or "").strip()
                if text:
                    events.append({"type": EVT_TEXT, "text": text})
            elif block_kind == "ThinkingBlock":
                text = (getattr(block, "thinking", "") or "").strip()
                if text:
                    events.append({"type": EVT_THINKING, "text": _truncate(text, 1500)})
            elif block_kind == "ToolUseBlock":
                name = getattr(block, "name", "") or ""
                payload = getattr(block, "input", {}) or {}
                event: dict[str, Any] = {"type": EVT_TOOL, "tool": name}
                if name in _SHOWN_TOOLS:
                    artifact = _artifact_for(name, payload)
                    if artifact is not None:
                        event["artifact"] = artifact
                    elif name in ("Task", "WebFetch"):
                        event["summary"] = _truncate(str(payload)[:400], 400)
                events.append(event)

    elif kind == "ResultMessage":
        events.append(
            {
                "type": EVT_RESULT,
                "subtype": getattr(message, "subtype", None),
                "is_error": bool(getattr(message, "is_error", False)),
                "result": _truncate(str(getattr(message, "result", "") or "")),
                "num_turns": getattr(message, "num_turns", None),
                "duration_ms": getattr(message, "duration_ms", None),
                "total_cost_usd": getattr(message, "total_cost_usd", None),
                "stop_reason": getattr(message, "stop_reason", None),
            }
        )

    elif kind == "RateLimitEvent":
        # Mostly telemetry, not trouble. The CLI emits one of these partway
        # through ordinary turns with `status: allowed` and the current
        # utilisation — the first test run treated that as a failure and
        # aborted a perfectly healthy task.
        #
        # It is still worth forwarding, because on a subscription this is the
        # limit that actually binds, and it lets Nova say "you are at 32% of
        # your weekly window" rather than discovering the ceiling by hitting
        # it. Only a status other than `allowed` is an error.
        info = getattr(message, "rate_limit_info", None)
        raw = getattr(info, "raw", {}) or {}
        windows = raw.get("unifiedWindows", {}) or {}
        status = getattr(info, "status", None)
        events.append(
            {
                "type": EVT_ERROR if status not in (None, "allowed") else EVT_RATE_LIMIT,
                "reason": "rate_limit",
                "status": status,
                "limit_type": getattr(info, "rate_limit_type", None),
                "resets_at": getattr(info, "resets_at", None),
                "utilization": {
                    name: window.get("utilization")
                    for name, window in windows.items()
                    if isinstance(window, dict)
                },
            }
        )

    return events
