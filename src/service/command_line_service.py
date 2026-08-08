import os
import subprocess

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
    """

    def __init__(self):
        pass

    def run_terminal_command(
        self,
        command: str,
        working_directory: str | None = None,
        timeout_seconds: int | None = None,
    ) -> dict:
        """
        Run a shell command and return a structured result the model can act on.

        Always returns exit_code/stdout/stderr rather than raising on non-zero
        exit — a failed command is information, not an error in the tool layer.
        """
        command = (command or "").strip()
        if not command:
            raise ValueError("A non-empty command is required.")

        timeout = _DEFAULT_TIMEOUT_SECONDS if timeout_seconds is None else int(timeout_seconds)
        timeout = max(1, min(timeout, _MAX_TIMEOUT_SECONDS))

        cwd = None
        if working_directory:
            cwd = os.path.expanduser(str(working_directory))
            if not os.path.isdir(cwd):
                raise ValueError(f"Working directory does not exist: {working_directory}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "timed_out": True,
                "timeout_seconds": timeout,
                "exit_code": None,
                "stdout": self._clip(self._decode(exc.stdout)),
                "stderr": self._clip(self._decode(exc.stderr)),
                "note": "Command was killed after exceeding the timeout.",
            }

        return {
            "timed_out": False,
            "exit_code": result.returncode,
            "stdout": self._clip(result.stdout),
            "stderr": self._clip(result.stderr),
        }

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
