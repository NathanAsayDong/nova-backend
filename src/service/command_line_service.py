import os
import subprocess
import tempfile
import time
from pathlib import Path

from src.service import process_supervisor as supervisor

_DEFAULT_TIMEOUT_SECONDS = 30
_MAX_TIMEOUT_SECONDS = 120
_MAX_OUTPUT_CHARS = 8_000


class CommandLineService:
    """
    Shell access for the agent loop.

    Commands run with the backend process's privileges and, by default, its
    working directory. Output is truncated so a chatty command can't flood
    the model context or the message table, and every call is bounded by a
    timeout so a hanging command can't wedge a turn.

    Two things are deliberately not pipes and not bare kills. Output goes to
    files on disk, because a pipe stays open until its last writer closes it —
    so a command that spawns a dev server used to block for its entire timeout
    even when it had "detached" with `&` or `start`. And a timeout kills the
    whole process group, because killing just the shell orphaned the server it
    started, leaving it holding a port with no handle left to stop it.
    Long-lived commands belong in process_supervisor; this class routes them
    there rather than pretending they will finish.
    """

    def __init__(self):
        pass

    def run_terminal_command(
        self,
        command: str,
        working_directory: str | None = None,
        timeout_seconds: int | None = None,
        conversation_uuid: str | None = None,
    ) -> dict:
        """
        Run a shell command and return a structured result the model can act on.

        Always returns exit_code/stdout/stderr rather than raising on non-zero
        exit — a failed command is information, not an error in the tool layer.

        With no explicit working_directory, commands run in the active
        conversation's project workspace when it has one, so shell work and the
        code tools agree on where "here" is.

        A command that will never finish on its own — a dev server, a watcher —
        is started in the background instead of being run to a timeout, and the
        result says so. Waiting 30s to kill a server that was working fine is
        not a useful way to spend a turn.
        """
        command = (command or "").strip()
        if not command:
            raise ValueError("A non-empty command is required.")

        if not working_directory and conversation_uuid:
            working_directory = self._project_workspace(conversation_uuid)

        cwd = self._resolve_cwd(working_directory)

        mode, reason = supervisor.classify(command)
        if mode == "background":
            return supervisor.start(command, cwd=cwd, note=reason, host="tower")

        timeout = _DEFAULT_TIMEOUT_SECONDS if timeout_seconds is None else int(timeout_seconds)
        timeout = max(1, min(timeout, _MAX_TIMEOUT_SECONDS))
        return self._run_foreground(command, cwd, timeout)

    # ---------- long-lived commands ----------

    def start_background_command(
        self,
        command: str,
        working_directory: str | None = None,
        wait_for_port: int | None = None,
        wait_for_log: str | None = None,
        wait_timeout_seconds: int | None = None,
        conversation_uuid: str | None = None,
    ) -> dict:
        """
        Start a command that is meant to keep running, and report whether it came up.

        Returns a process_id immediately rather than waiting for an exit that
        will never come. `wait_for_port` / `wait_for_log` are what make the
        answer worth having: without one of them "started" only means Popen
        did not raise, and Nova would report a healthy server moments before
        the next request got connection refused.
        """
        if not working_directory and conversation_uuid:
            working_directory = self._project_workspace(conversation_uuid)
        return supervisor.start(
            command,
            cwd=self._resolve_cwd(working_directory),
            wait_for_port=wait_for_port,
            wait_for_log=wait_for_log,
            wait_timeout_seconds=wait_timeout_seconds,
            host="tower",
        )

    def check_background_command(
        self,
        process_id: str | None = None,
        conversation_uuid: str | None = None,
    ) -> dict:
        """Output and status for one background process, or a list of all of them."""
        return supervisor.check(process_id)

    def stop_background_command(
        self,
        process_id: str,
        conversation_uuid: str | None = None,
    ) -> dict:
        """Stop a background process and everything it started."""
        return supervisor.stop(process_id)

    # ---------- internals ----------

    def _run_foreground(self, command: str, cwd: str | None, timeout: int) -> dict:
        """
        Run to completion, or kill the whole tree trying.

        stdout and stderr go to temp files rather than pipes. That costs two
        files and buys the thing that matters: the call returns when the
        command exits, not when the last process holding an inherited pipe
        closes it.
        """
        out_path, err_path = self._scratch_pair()
        try:
            with open(out_path, "wb", buffering=0) as out, open(err_path, "wb", buffering=0) as err:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=out,
                    stderr=err,
                    stdin=subprocess.DEVNULL,
                    cwd=cwd,
                    **supervisor.spawn_kwargs(),
                )
                try:
                    exit_code = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    supervisor.kill_tree(process)
                    return {
                        "timed_out": True,
                        "timeout_seconds": timeout,
                        "exit_code": None,
                        "stdout": self._clip(supervisor.read_log(out_path)),
                        "stderr": self._clip(supervisor.read_log(err_path)),
                        "note": (
                            f"Command and everything it started were killed after {timeout}s. "
                            "The output above is what it had produced by then. If this is "
                            "meant to keep running (a server, a watcher), start it with "
                            "start_background_command instead of raising the timeout."
                        ),
                    }

            return {
                "timed_out": False,
                "exit_code": exit_code,
                "stdout": self._clip(supervisor.read_log(out_path)),
                "stderr": self._clip(supervisor.read_log(err_path)),
            }
        finally:
            for path in (out_path, err_path):
                try:
                    os.unlink(path)
                except OSError:
                    pass

    @staticmethod
    def _scratch_pair() -> tuple[str, str]:
        root = Path(tempfile.gettempdir()) / "nova-processes"
        root.mkdir(parents=True, exist_ok=True)
        stamp = f"{os.getpid()}-{time.time_ns()}"
        return str(root / f"cmd-{stamp}.out"), str(root / f"cmd-{stamp}.err")

    @staticmethod
    def _resolve_cwd(working_directory: str | None) -> str | None:
        if not working_directory:
            return None
        cwd = os.path.expanduser(str(working_directory))
        if not os.path.isdir(cwd):
            raise ValueError(f"Working directory does not exist: {working_directory}")
        return cwd

    @staticmethod
    def _project_workspace(conversation_uuid: str) -> str | None:
        """
        Workspace of the conversation's project, if it has one.

        Imported lazily to avoid a circular import, and failures are swallowed
        — defaulting the working directory is a convenience, not a
        precondition for running a command.
        """
        try:
            from src.service.code_service import CodeService

            code_service = CodeService()
            project = code_service._resolve_project(conversation_uuid=conversation_uuid)
            return str(code_service.project_workspace(project))
        except Exception:
            return None

    @staticmethod
    def _decode(stream: str | bytes | None) -> str:
        if stream is None:
            return ""
        if isinstance(stream, bytes):
            return stream.decode("utf-8", errors="replace")
        return stream

    @staticmethod
    def _clip(text: str) -> str:
        text = text or ""
        if len(text) <= _MAX_OUTPUT_CHARS:
            return text
        omitted = len(text) - _MAX_OUTPUT_CHARS
        return text[:_MAX_OUTPUT_CHARS] + f"\n... [truncated {omitted} characters]"
