import difflib
import os
import shutil
import subprocess
from pathlib import Path
from uuid import UUID

from src.dao.conversation_dao import ConversationDao
from src.dao.project_dao import ProjectDao
from src.model.project import Project

# Workspaces live inside the repo (gitignored) rather than at a machine-wide
# path, so a project's code sits alongside the backend that manages it.
# Anchored to the repo root rather than the cwd so it resolves the same way
# whether the backend, the worker, or a test starts the process.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_WORKSPACE_ROOT = str(_REPO_ROOT / "project_files")
_MAX_READ_CHARS = 60_000
_MAX_LIST_ENTRIES = 500
_MAX_COMMAND_OUTPUT_CHARS = 4_000
_MAX_DIFF_LINES = 200
_EDIT_TIMEOUT_SECONDS = 30
_IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
}


class CodeService:
    """
    Project-scoped file access for the agent.

    Every operation resolves to a project first, so code can never be written
    without attribution. Each project owns exactly one workspace directory
    (`project_files/project-<id>` inside this repo by default, overridable with
    NOVA_WORKSPACE_ROOT), keyed on the project id rather than its name so
    renames don't strand a folder.

    Paths are always relative to that workspace and are validated to stay
    inside it, so `..`, absolute paths, and symlinks can't reach the rest of
    the disk.
    """

    def __init__(self) -> None:
        self.project_dao = ProjectDao()
        self.conversation_dao = ConversationDao()
        self.workspace_root = Path(
            os.getenv("NOVA_WORKSPACE_ROOT", _DEFAULT_WORKSPACE_ROOT)
        ).expanduser()

    # ---------- project + path resolution ----------

    def _resolve_project(
        self,
        project_id: int | None = None,
        conversation_uuid: str | None = None,
    ) -> Project:
        """
        Find the project this operation belongs to.

        An explicit project_id wins; otherwise the project is taken from the
        active conversation. A conversation with no project is a hard error —
        that's the constraint that keeps code attributed.
        """
        if project_id is not None:
            project = self.project_dao.get(int(project_id))
            if project is None:
                raise ValueError(f"Project {project_id} does not exist.")
            return project

        if conversation_uuid:
            conversation = self.conversation_dao.get_by_uuid(UUID(str(conversation_uuid)))
            if conversation is None:
                raise ValueError(f"Conversation {conversation_uuid} does not exist.")
            if conversation.project_id is None:
                raise ValueError(
                    "This conversation is not attached to a project, and code "
                    "must belong to one. Create a project with create_project "
                    "and attach it with assign_conversation_to_project (or "
                    "switch_project), or pass an explicit project_id."
                )
            project = self.project_dao.get(conversation.project_id)
            if project is None:
                raise ValueError(
                    f"Project {conversation.project_id} attached to this "
                    "conversation no longer exists."
                )
            return project

        raise ValueError(
            "No project context available. Pass project_id explicitly, or run "
            "this from a conversation attached to a project."
        )

    def project_workspace(self, project: Project) -> Path:
        """Absolute path to a project's workspace, created on first use."""
        root = (self.workspace_root / f"project-{project.id}").resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def _resolve_path(root: Path, relative_path: str) -> Path:
        """
        Resolve a workspace-relative path, refusing anything that escapes.

        resolve() collapses `..` and follows symlinks before the containment
        check, so neither can be used to reach outside the workspace.
        """
        candidate = (relative_path or "").strip()
        if not candidate:
            raise ValueError("A file path is required.")
        if Path(candidate).is_absolute():
            raise ValueError(
                f"Path must be relative to the project workspace, got '{candidate}'."
            )

        target = (root / candidate).resolve()
        if target != root and not target.is_relative_to(root):
            raise ValueError(
                f"Path '{candidate}' escapes the project workspace and was refused."
            )
        return target

    def _context(
        self, project_id: int | None, conversation_uuid: str | None
    ) -> tuple[Project, Path]:
        project = self._resolve_project(project_id, conversation_uuid)
        return project, self.project_workspace(project)

    @staticmethod
    def _project_summary(project: Project, root: Path) -> dict:
        return {"id": project.id, "name": project.name, "workspace": str(root)}

    @staticmethod
    def _clip(text: str, limit: int) -> str:
        text = text or ""
        if len(text) <= limit:
            return text
        return text[:limit] + f"\n... [truncated {len(text) - limit} characters]"

    # ---------- tools ----------

    def list_project_files(
        self,
        subdirectory: str | None = None,
        project_id: int | None = None,
        conversation_uuid: str | None = None,
    ) -> dict:
        """List the files in a project's workspace so existing work is discoverable."""
        project, root = self._context(project_id, conversation_uuid)

        base = self._resolve_path(root, subdirectory) if subdirectory else root
        if not base.exists():
            raise ValueError(f"Directory does not exist: {subdirectory}")
        if not base.is_dir():
            raise ValueError(f"Not a directory: {subdirectory}")

        files: list[dict] = []
        truncated = False
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d not in _IGNORED_DIRECTORIES)
            for filename in sorted(filenames):
                if len(files) >= _MAX_LIST_ENTRIES:
                    truncated = True
                    break
                full_path = Path(dirpath) / filename
                try:
                    size = full_path.stat().st_size
                except OSError:
                    continue
                files.append(
                    {"path": str(full_path.relative_to(root)), "bytes": size}
                )
            if truncated:
                break

        return {
            "project": self._project_summary(project, root),
            "file_count": len(files),
            "files": files,
            "truncated": truncated,
            "note": None if files else "This project has no code files yet.",
        }

    def read_project_file(
        self,
        path: str,
        project_id: int | None = None,
        conversation_uuid: str | None = None,
    ) -> dict:
        """Read a file from a project's workspace."""
        project, root = self._context(project_id, conversation_uuid)
        target = self._resolve_path(root, path)

        if not target.exists():
            raise ValueError(f"File does not exist: {path}")
        if target.is_dir():
            raise ValueError(f"Path is a directory, not a file: {path}")

        try:
            content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"File is not valid UTF-8 text and cannot be read: {path}")

        clipped = self._clip(content, _MAX_READ_CHARS)
        return {
            "project": self._project_summary(project, root),
            "path": path,
            "content": clipped,
            "truncated": clipped != content,
            "line_count": content.count("\n") + 1 if content else 0,
        }

    def write_project_file(
        self,
        path: str,
        content: str,
        project_id: int | None = None,
        conversation_uuid: str | None = None,
    ) -> dict:
        """
        Write a file into a project's workspace, creating parent directories.

        Overwrites an existing file wholesale; use edit_project_file for
        targeted changes to a file that already exists.
        """
        project, root = self._context(project_id, conversation_uuid)
        target = self._resolve_path(root, path)

        if target.is_dir():
            raise ValueError(f"Path is a directory, not a file: {path}")

        existed = target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content or "", encoding="utf-8")

        return {
            "project": self._project_summary(project, root),
            "path": path,
            "status": "overwritten" if existed else "created",
            "bytes_written": len((content or "").encode("utf-8")),
        }

    def edit_project_file(
        self,
        path: str,
        command: str,
        project_id: int | None = None,
        conversation_uuid: str | None = None,
    ) -> dict:
        """
        Edit a file in place by running a shell command against it.

        The command runs with the project workspace as its working directory,
        so it can address the file by its relative path (e.g.
        `sed -i '' 's/old/new/g' main.py`). This avoids rewriting a whole file
        to change a few lines. Returns a diff of what actually changed so the
        edit can be verified without re-reading the file.
        """
        project, root = self._context(project_id, conversation_uuid)
        target = self._resolve_path(root, path)

        command = (command or "").strip()
        if not command:
            raise ValueError("A non-empty command is required.")
        if not target.exists():
            raise ValueError(f"File does not exist: {path}")
        if target.is_dir():
            raise ValueError(f"Path is a directory, not a file: {path}")

        try:
            before = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            before = None

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=_EDIT_TIMEOUT_SECONDS,
                cwd=str(root),
            )
        except subprocess.TimeoutExpired:
            return {
                "project": self._project_summary(project, root),
                "path": path,
                "timed_out": True,
                "note": (
                    f"Command exceeded {_EDIT_TIMEOUT_SECONDS}s and was killed. "
                    "The file may be in a partial state."
                ),
            }

        after = None
        if target.exists():
            try:
                after = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                after = None

        return {
            "project": self._project_summary(project, root),
            "path": path,
            "timed_out": False,
            "exit_code": result.returncode,
            "stdout": self._clip(result.stdout, _MAX_COMMAND_OUTPUT_CHARS),
            "stderr": self._clip(result.stderr, _MAX_COMMAND_OUTPUT_CHARS),
            "file_changed": before != after,
            "file_deleted": not target.exists(),
            "diff": self._build_diff(before, after, path),
        }

    def delete_project_file(
        self,
        path: str,
        recursive: bool = False,
        project_id: int | None = None,
        conversation_uuid: str | None = None,
    ) -> dict:
        """
        Delete a file from a project's workspace.

        Directories require recursive, and the workspace root itself can never
        be deleted through this tool.
        """
        project, root = self._context(project_id, conversation_uuid)
        target = self._resolve_path(root, path)

        if target == root:
            raise ValueError(
                "Refusing to delete the project workspace itself. Delete "
                "individual files, or remove the project with delete_project."
            )
        if not target.exists():
            raise ValueError(f"File does not exist: {path}")

        if target.is_dir():
            if not recursive:
                raise ValueError(
                    f"'{path}' is a directory. Confirm with the user, then retry "
                    "with recursive set to true to delete it and its contents."
                )
            file_count = sum(1 for item in target.rglob("*") if item.is_file())
            shutil.rmtree(target)
            return {
                "project": self._project_summary(project, root),
                "path": path,
                "status": "deleted",
                "kind": "directory",
                "files_deleted": file_count,
            }

        target.unlink()
        return {
            "project": self._project_summary(project, root),
            "path": path,
            "status": "deleted",
            "kind": "file",
        }

    # ---------- helpers ----------

    @staticmethod
    def _build_diff(before: str | None, after: str | None, path: str) -> str:
        if before is None or after is None:
            return "(binary or unreadable file; no diff available)"
        if before == after:
            return ""
        diff_lines = list(
            difflib.unified_diff(
                before.splitlines(),
                after.splitlines(),
                fromfile=f"{path} (before)",
                tofile=f"{path} (after)",
                lineterm="",
                n=2,
            )
        )
        if len(diff_lines) > _MAX_DIFF_LINES:
            omitted = len(diff_lines) - _MAX_DIFF_LINES
            diff_lines = diff_lines[:_MAX_DIFF_LINES]
            diff_lines.append(f"... [truncated {omitted} more diff lines]")
        return "\n".join(diff_lines)
