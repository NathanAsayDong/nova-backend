"""
Giving a session its own working directory inside your repo.

The point of running on this Mac is that Nova works on the same repos you do.
The point of a worktree is that it does not work on the same *files* you have
open — same repo, same history, same remote, separate checkout. You keep
editing on your branch while a session builds on its own, and the result
arrives as a branch you can review like anyone else's.

Worktrees live outside the repo (under ~/.nova/worktrees by default) so a
session can never see, index, or accidentally commit a sibling task's files.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


class WorktreeError(RuntimeError):
    pass


@dataclass(frozen=True)
class Workspace:
    """Where a session runs, and whether we are responsible for cleaning it up."""

    path: Path
    repo: Path
    branch: str | None
    is_worktree: bool


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise WorktreeError(
            f"git {' '.join(args)} failed in {repo}: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def slugify(value: str, fallback: str = "task") -> str:
    slug = _SAFE.sub("-", (value or "").strip().lower()).strip("-")
    return (slug or fallback)[:48]


def resolve_repo(repos_root: Path, repo: str) -> Path:
    """Accept either an absolute path or a directory name under the repos root."""
    candidate = Path(repo).expanduser()
    if not candidate.is_absolute():
        candidate = repos_root / repo
    candidate = candidate.resolve()
    if not (candidate / ".git").exists():
        raise WorktreeError(f"{candidate} is not a git repository.")
    return candidate


def create(
    repo: Path, worktree_root: Path, name: str, base: str | None = None
) -> Workspace:
    """Cut a new branch and a worktree for it."""
    branch = f"nova/{slugify(name)}"
    path = (worktree_root / repo.name / slugify(name)).resolve()

    if path.exists():
        raise WorktreeError(f"A worktree already exists at {path}.")
    path.parent.mkdir(parents=True, exist_ok=True)

    # Branch from the repo's current HEAD unless told otherwise, so a session
    # starts from what you were last working on rather than a stale default.
    start_point = base or _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    _git(repo, "worktree", "add", str(path), "-b", branch, start_point)
    return Workspace(path=path, repo=repo, branch=branch, is_worktree=True)


def remove(workspace: Workspace, force: bool = False) -> None:
    """
    Drop the worktree, keeping the branch.

    The branch is the deliverable — removing the checkout after a task is
    tidiness, losing the commits would be data loss. Never prune a worktree
    with uncommitted changes unless explicitly forced.
    """
    if not workspace.is_worktree:
        return
    args = ["worktree", "remove", str(workspace.path)]
    if force:
        args.append("--force")
    _git(workspace.repo, *args)
