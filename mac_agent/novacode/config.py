"""
Where the agent gets its settings, and what it refuses to pass on.

Everything is environment-driven so the launchd plist is the single place
deployment details live. The one piece of real logic here is `child_env`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# The variable that would silently move Nova's coding work off the Claude
# subscription and onto metered API billing.
#
# Claude Code skips the login prompt entirely when it sees this, so a stray
# export — or one line added to nova-backend's .env, which main.py and
# worker.py both push into the process environment — would reroute the billing
# with no error and no visible change in behaviour. The agent therefore
# strips it from every CLI subprocess rather than trusting the environment it
# happens to inherit. Subscription auth is a property of this code.
_BILLING_OVERRIDE_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")

DEFAULT_WS_URL = "ws://localhost:8000/ws/coding"


def load_env_file(path: Path | None = None, override: bool = False) -> None:
    """
    Read `mac_agent/.env` into the process environment.

    launchd does not read dotfiles and cannot be told to, so the alternative
    would be baking values into the plist — and the token in there is a
    long-lived credential to a Claude account sitting in a world-readable
    corner of ~/Library. A 0600 file next to the code is the better home.

    Existing environment variables win by default, so a value exported for one
    run is not silently overridden by the file. `override` flips that, which is
    what a reload wants: the file is the source of truth and the stale value in
    os.environ is exactly what needs replacing.
    """
    path = path or Path(__file__).resolve().parent.parent / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and (override or key not in os.environ):
            os.environ[key] = value


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"false", "0", "no", "off"}


@dataclass(frozen=True)
class Config:
    ws_url: str
    token: str
    repos_root: Path
    worktree_root: Path
    permission_mode: str
    sandbox: bool
    max_budget_usd: float | None
    model: str | None

    @classmethod
    def from_env(cls, reload: bool = False) -> "Config":
        load_env_file(override=reload)
        home = Path.home()
        budget = os.getenv("NOVA_CODE_MAX_BUDGET_USD")
        return cls(
            ws_url=os.getenv("NOVA_CODE_WS_URL") or DEFAULT_WS_URL,
            token=os.getenv("NOVA_CODE_TOKEN", ""),
            repos_root=Path(
                os.getenv("NOVA_CODE_REPOS_ROOT") or home / "Desktop"
            ).expanduser(),
            worktree_root=Path(
                os.getenv("NOVA_CODE_WORKTREE_ROOT") or home / ".nova" / "worktrees"
            ).expanduser(),
            # 'acceptEdits' lets the agent edit without prompting for every
            # write — there is no human at this terminal to answer — while
            # still routing anything riskier through can_use_tool.
            permission_mode=os.getenv("NOVA_CODE_PERMISSION_MODE") or "acceptEdits",
            sandbox=_flag("NOVA_CODE_SANDBOX", True),
            max_budget_usd=float(budget) if budget else None,
            model=os.getenv("NOVA_CODE_MODEL") or None,
        )

    def child_env(self) -> dict[str, str]:
        """The environment handed to the Claude Code CLI, minus the billing override."""
        env = {k: v for k, v in os.environ.items() if k not in _BILLING_OVERRIDE_VARS}
        return env
