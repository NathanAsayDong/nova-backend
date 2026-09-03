"""
The guard on what a session is allowed to touch.

Two layers, and they do different jobs. Claude Code's own OS-level sandbox
(enabled in `sessions.py`) is the one that actually contains a process. This
callback is the cheaper, narrower check on top: it keeps a session inside the
directory Nova assigned it, so a task about nova-frontend cannot wander into
the meeting recordings or someone's SSH keys.

Treat it as a fence, not a jail. It reads tool arguments, so it constrains a
cooperative agent making a mistake — which is the realistic risk — rather than
a determined one.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)

# Tool arguments that name a path. Anything here gets containment-checked.
_PATH_ARGS = ("file_path", "notebook_path", "path", "target_file")

# Commands that are never a legitimate part of a coding task and are
# catastrophic when they are a mistake. Not a security boundary — the sandbox
# is — just the set worth refusing outright even inside the worktree.
_FORBIDDEN_FRAGMENTS = (
    "rm -rf /",
    "rm -rf ~",
    "mkfs",
    "dd if=",
    ":(){",
    "sudo ",
    "shutdown",
    "diskutil erase",
)


def _contained(candidate: str, root: Path) -> bool:
    try:
        resolved = Path(os.path.expanduser(candidate)).resolve()
    except (OSError, RuntimeError):
        return False
    return resolved == root or root in resolved.parents


def make_guard(root: Path):
    """Build a `can_use_tool` callback that pins a session to `root`."""
    root = root.resolve()

    async def can_use_tool(
        tool_name: str,
        tool_input: dict[str, Any],
        context: ToolPermissionContext,
    ) -> PermissionResultAllow | PermissionResultDeny:
        for arg in _PATH_ARGS:
            value = tool_input.get(arg)
            if isinstance(value, str) and value and not _contained(value, root):
                return PermissionResultDeny(
                    message=(
                        f"{tool_name} was denied: {value} is outside this task's "
                        f"working directory ({root}). Stay inside it, or ask Nate "
                        f"to widen the task."
                    ),
                )

        if tool_name == "Bash":
            command = str(tool_input.get("command", ""))
            lowered = command.lower()
            for fragment in _FORBIDDEN_FRAGMENTS:
                if fragment in lowered:
                    return PermissionResultDeny(
                        message=(
                            f"Refused: the command contains {fragment!r}, which is "
                            f"never part of a coding task."
                        ),
                        interrupt=True,
                    )

        return PermissionResultAllow()

    return can_use_tool
