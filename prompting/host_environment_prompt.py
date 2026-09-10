"""
The one part of Nova's system prompt that depends on which machine it is on.

Nova runs in two places, and the deployment changes what its own tools mean.
On the Windows tower, `run_terminal_command` is the tower's shell and
`run_mac_command` reaches across the Mac agent's websocket to Nate's laptop.
Run the same backend on the laptop and both tools land on the same machine —
at which point telling Nate that something "ran over on the Mac" is noise,
and warning him that the Mac needs to be awake is nonsense.

The persona prompt stays a static file because none of it moves. This block
moves, so it is built here.
"""

import os
import platform
import socket

# Anything that is not macOS is treated as the tower: that is where the
# Windows deployment lives, and a Linux box would have the same split (local
# shell here, Mac over the link) even if the shell syntax differed.
_MAC_HOST = "mac"
_TOWER_HOST = "tower"


def _host_kind() -> str:
    """Which deployment this process is, honouring an explicit override."""
    override = (os.getenv("NOVA_HOST") or "").strip().lower()
    if override in {_MAC_HOST, _TOWER_HOST}:
        return override
    return _MAC_HOST if platform.system() == "Darwin" else _TOWER_HOST


def _machine_line() -> str:
    """One factual line naming the box, for when Nate asks what it is on."""
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "unknown"
    return f"Host: {hostname} ({platform.system()} {platform.release()})."


_MAC_BLOCK = """# Environment: where you are running

You are running ON Nate's Mac — the same machine he writes code on. Nova is
not reaching the laptop over a link right now; it is on the laptop.

- `run_terminal_command` and `run_mac_command` both run right here, on this
  Mac. Either is fine. They differ only in where they start: the first in the
  active project's workspace, the second in his repos root (`~/Desktop`). Pass
  a working directory to either when it matters.
- It is macOS: zsh and POSIX commands, his real toolchain, his real repos.
- Do not describe a command as having run "over on the Mac" or "on the tower",
  do not present the two tools as two different machines, and never warn that
  the Mac has to be awake or connected. There is one machine and you are on
  it."""

_TOWER_BLOCK = """# Environment: where you are running

You are running on Nate's Windows tower — the always-on machine Nova's backend
lives on. It is NOT the machine he writes code on, and that distinction picks
the shell tool:

- `run_terminal_command` runs here on the tower: Nova's own service, its
  checkout, its logs, its database. Windows shell, so Windows commands.
- `run_mac_command` runs on his Mac laptop, through the link the Mac agent
  holds open: his repos under `~/Desktop`, his toolchain, his dev servers.
  zsh, so POSIX commands. It needs the Mac awake and connected — when it is
  not, the call fails, and the honest answer is that his laptop is offline,
  not a retry.

So anything about his code or his machine goes to `run_mac_command`; anything
about Nova's own service goes to `run_terminal_command`. The two hosts share
no filesystem — a path that exists on one does not exist on the other — so
say which machine you ran on whenever it could matter."""


def host_environment_prompt() -> str:
    """
    The host section of the system prompt for this process.

    Stable for the life of the process, so it can sit inside the prompt
    cache's stable prefix alongside the persona.
    """
    block = _MAC_BLOCK if _host_kind() == _MAC_HOST else _TOWER_BLOCK
    return f"{block}\n\n{_machine_line()}"
