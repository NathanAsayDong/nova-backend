import inspect
import json
import os
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any

from openai import APIConnectionError, APITimeoutError, OpenAI

from src.service.tool_service import ToolExecutionError, ToolService

DEFAULT_OPENAI_RESPONSE_MODEL = "gpt-5.4-mini-2026-03-17"
DEFAULT_OPENAI_SYSTEM_PROMPT = (
    "You are NOVA, a fun, somewhat sarcastic, AI assistant like Jarvis from Iron Man."
    "When tools are available, call them when needed and produce a direct final answer."
    "Resonses should be concise and brief unless there is more info needed like coding or harder tasks. then you can be more verbose."
    "Dont ever ask if the user needs help with anything else"
    "Make sure when using tools, that when you reply with information, its concise and human interpratble, like when getting time, it should be 'Oh the time is 10 AM!"
    "The goal should be to summarize, not regurgitate the information. Thinks like exact urls and stuff like that are just too much. You need to be good at SUMMARIZING and being BREIF"
    "Only add a joke or sarcasm every 8 or 9 messages."
    "You have access to a list of tools for the users information that you can call and iterate on to get all the info you need."
    "** Note that your outputs are put into a text to speech model so we want clear sentences and words that can be vocally spoken or read. Thinks like file paths or formatting need to be considered."
)
DEFAULT_OPENAI_MAX_TOOL_ITERATIONS = 5
MAX_LOCAL_CHAT_MESSAGES = 30
DEFAULT_OPENAI_LOOP_TIMEOUT_SECONDS = 90.0
DEFAULT_OPENAI_REQUEST_TIMEOUT_SECONDS = 45.0
DEFAULT_PROGRESS_REQUEST_TIMEOUT_SECONDS = 4.0
DEFAULT_PROGRESS_INSTRUCTIONS = (
    "You are generating a brief spoken progress update for a voice assistant. "
    "Return exactly one short sentence (4-12 words), plain text only, no markdown. "
    "Do not say step numbers, iteration numbers, or repeat yourself."
)


@dataclass
class LoopResult:
    progress_messages: list[str]
    final_text: str
    iterations_used: int


class OpenAIService:
    def __init__(self, tool_service: ToolService | None = None) -> None:
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_APIKEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        self.client = OpenAI(api_key=api_key)
        self.response_model = DEFAULT_OPENAI_RESPONSE_MODEL
        self.system_prompt = DEFAULT_OPENAI_SYSTEM_PROMPT
        self.max_iterations = DEFAULT_OPENAI_MAX_TOOL_ITERATIONS
        self.loop_timeout_seconds = self._read_timeout_env(
            "OPENAI_LOOP_TIMEOUT_SECONDS", DEFAULT_OPENAI_LOOP_TIMEOUT_SECONDS
        )
        self.request_timeout_seconds = self._read_timeout_env(
            "OPENAI_REQUEST_TIMEOUT_SECONDS", DEFAULT_OPENAI_REQUEST_TIMEOUT_SECONDS
        )
        self.progress_timeout_seconds = self._read_timeout_env(
            "OPENAI_PROGRESS_TIMEOUT_SECONDS", DEFAULT_PROGRESS_REQUEST_TIMEOUT_SECONDS
        )
        self.progress_model = (os.getenv("OPENAI_PROGRESS_MODEL") or self.response_model).strip()
        self.enable_dynamic_progress_updates = (
            os.getenv("OPENAI_DYNAMIC_PROGRESS_UPDATES", "1").strip().lower() not in {"0", "false", "no"}
        )

        self.tool_service = tool_service or ToolService()
        self.chat_history: list[dict[str, str]] = []

    @staticmethod
    def _read_timeout_env(name: str, fallback: float) -> float:
        raw_value = os.getenv(name, "").strip()
        if not raw_value:
            return fallback
        try:
            parsed = float(raw_value)
        except ValueError:
            return fallback
        return parsed if parsed > 0 else fallback

    @staticmethod
    def _extract_function_calls(response_output: list[Any]) -> list[Any]:
        return [item for item in response_output if getattr(item, "type", None) == "function_call"]

    @staticmethod
    def _safe_json_parse(arguments: str) -> dict[str, Any]:
        if not arguments:
            return {}

        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise ToolExecutionError(f"Invalid tool arguments JSON: {str(exc)}", recoverable=True) from exc

        if not isinstance(parsed, dict):
            raise ToolExecutionError("Tool arguments must be a JSON object.", recoverable=True)
        return parsed

    def _trim_chat_history(self) -> None:
        if len(self.chat_history) > MAX_LOCAL_CHAT_MESSAGES:
            self.chat_history = self.chat_history[-MAX_LOCAL_CHAT_MESSAGES:]

    def _history_as_openai_input(self) -> list[dict[str, str]]:
        window = self.chat_history[-MAX_LOCAL_CHAT_MESSAGES:]
        return [{"role": message["role"], "content": message["text"]} for message in window]

    @staticmethod
    def _sanitize_progress_text(value: str) -> str:
        text = (value or "").strip().replace("\n", " ")
        text = " ".join(text.split())
        text = re.sub(r"^\s*step\s*[\w-]+\s*[:,-]?\s*", "", text, flags=re.IGNORECASE)
        if text.startswith('"') and text.endswith('"') and len(text) > 1:
            text = text[1:-1].strip()
        if len(text) > 120:
            text = text[:117].rstrip() + "..."
        return text

    @staticmethod
    def _terminal_log_tool_event(label: str, payload: dict[str, Any]) -> None:
        try:
            rendered = json.dumps(payload, indent=2, default=str)
        except Exception:
            rendered = str(payload)
        print(f"[NOVA_TOOL_{label}] {rendered}", flush=True)

    def _fallback_progress_message(self, function_calls: list[Any]) -> str:
        if not function_calls:
            return "Let me check that quickly."

        tool_name = str(getattr(function_calls[0], "name", "tool"))
        fallback_map = {
            "get_current_time": "Let me check the time real quick.",
            "write_code": "I'll kick off a coding agent now.",
            "check_prs": "I'll check the pull requests now.",
            "check_coding_agent": "I'll check that coding agent status now.",
            "code_planner": "I'll draft a quick code plan for that.",
            "github_list_repos": "I'll pull your GitHub repos now.",
        }
        if tool_name in fallback_map:
            return fallback_map[tool_name]
        return "Let me check that quickly."

    def _build_tool_progress_message(self, user_text: str, function_calls: list[Any]) -> str:
        fallback = self._fallback_progress_message(function_calls)
        if not self.enable_dynamic_progress_updates:
            return fallback

        call_summaries: list[str] = []
        for call in function_calls[:3]:
            tool_name = str(getattr(call, "name", "tool"))
            raw_args = str(getattr(call, "arguments", "") or "")
            summarized_args = raw_args[:180] + ("..." if len(raw_args) > 180 else "")
            call_summaries.append(f"{tool_name}({summarized_args})")

        summary_prompt = (
            f"User request: {user_text}\n"
            f"Tool calls: {'; '.join(call_summaries) if call_summaries else 'none'}\n"
            "Generate the one-sentence spoken status update now."
        )

        try:
            response = self.client.responses.create(
                model=self.progress_model,
                instructions=DEFAULT_PROGRESS_INSTRUCTIONS,
                input=[
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": summary_prompt}],
                    }
                ],
                timeout=self.progress_timeout_seconds,
            )
            text = self._sanitize_progress_text(response.output_text or "")
            return text or fallback
        except Exception:
            return fallback

    async def run_agent_loop(
        self,
        user_text: str,
        progress_callback: Callable[[str, int], Awaitable[None] | None] | None = None,
    ) -> LoopResult:
        normalized_user_text = (user_text or "").strip()
        if not normalized_user_text:
            return LoopResult(
                progress_messages=[],
                final_text="I didn't catch any speech. Please try again.",
                iterations_used=0,
            )

        self.chat_history.append({"role": "user", "text": normalized_user_text})
        self._trim_chat_history()

        progress_messages: list[str] = []
        history_input = self._history_as_openai_input()
        tool_exchange_items: list[dict[str, Any]] = []
        next_input: Any = history_input
        final_text = ""
        loop_started_at = monotonic()

        for iteration in range(1, self.max_iterations + 1):
            if monotonic() - loop_started_at >= self.loop_timeout_seconds:
                final_text = (
                    "I reached the backend time limit for this turn before finishing. "
                    "Please try again."
                )
                self.chat_history.append({"role": "assistant", "text": final_text})
                self._trim_chat_history()
                return LoopResult(
                    progress_messages=progress_messages,
                    final_text=final_text,
                    iterations_used=max(0, iteration - 1),
                )

            try:
                #NOTE you cannot concat strings only list
                call_left = self.max_iterations - iteration
                if call_left > 0:
                    call_left_str = " you can make up to " + str(call_left) + " more calls to tools."
                else:
                    call_left_str = ""
                instructions = self.system_prompt + call_left_str
                response = self.client.responses.create(
                    model=self.response_model,
                    instructions=instructions,
                    input=next_input,
                    tools=self.tool_service.as_openai_tools(),
                    tool_choice="auto",
                    timeout=self.request_timeout_seconds,
                )
            except (APITimeoutError, APIConnectionError, TimeoutError):
                final_text = (
                    "I hit a backend timeout while generating your response. "
                    "Please try again in a moment."
                )
                self.chat_history.append({"role": "assistant", "text": final_text})
                self._trim_chat_history()
                return LoopResult(
                    progress_messages=progress_messages,
                    final_text=final_text,
                    iterations_used=max(0, iteration - 1),
                )
            except Exception as exc:
                final_text = f"The OpenAI responses endpoint failed: {str(exc)}"
                self.chat_history.append({"role": "assistant", "text": final_text})
                self._trim_chat_history()
                return LoopResult(
                    progress_messages=progress_messages,
                    final_text=final_text,
                    iterations_used=max(0, iteration - 1),
                )

            function_calls = self._extract_function_calls(response.output)
            if not function_calls:
                final_text = (response.output_text or "").strip()
                if not final_text:
                    final_text = "I finished processing but do not have a spoken response yet."
                self.chat_history.append({"role": "assistant", "text": final_text})
                self._trim_chat_history()
                return LoopResult(
                    progress_messages=progress_messages,
                    final_text=final_text,
                    iterations_used=iteration,
                )

            # Emit exactly one natural progress line before running any tool calls.
            progress_text = self._build_tool_progress_message(
                normalized_user_text,
                function_calls,
            )
            progress_messages.append(progress_text)
            if progress_callback is not None:
                callback_result = progress_callback(progress_text, iteration)
                if inspect.isawaitable(callback_result):
                    await callback_result

            function_call_items: list[dict[str, Any]] = []
            function_call_outputs: list[dict[str, Any]] = []
            unrecoverable_error = False

            for call in function_calls:
                call_id = getattr(call, "call_id", None)
                if not call_id:
                    unrecoverable_error = True
                    continue

                tool_name = getattr(call, "name", "")
                raw_args = getattr(call, "arguments", "") or "{}"
                tool_output: dict[str, Any] = {"ok": False, "tool": tool_name, "error": "Tool execution did not start."}
                try:
                    args = self._safe_json_parse(raw_args)
                    self._terminal_log_tool_event(
                        "CALL",
                        {
                            "iteration": iteration,
                            "call_id": call_id,
                            "tool": tool_name,
                            "arguments": args,
                        },
                    )
                    result = self.tool_service.execute(tool_name, args)
                    tool_output = {
                        "ok": True,
                        "tool": tool_name,
                        "result": result,
                    }
                except ToolExecutionError as exc:
                    tool_output = {
                        "ok": False,
                        "tool": tool_name,
                        "error": str(exc),
                        "recoverable": exc.recoverable,
                    }
                    if not exc.recoverable:
                        unrecoverable_error = True
                except Exception as exc:
                    tool_output = {
                        "ok": False,
                        "tool": tool_name,
                        "error": f"Unhandled tool error: {str(exc)}",
                        "recoverable": False,
                    }
                    unrecoverable_error = True
                finally:
                    self._terminal_log_tool_event(
                        "RESPONSE",
                        {
                            "iteration": iteration,
                            "call_id": call_id,
                            "tool": tool_name,
                            "output": tool_output,
                        },
                    )

                function_call_items.append(
                    {
                        "type": "function_call",
                        "call_id": call_id,
                        "name": tool_name,
                        "arguments": raw_args,
                    }
                )
                function_call_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(tool_output, separators=(",", ":")),
                    }
                )

            if unrecoverable_error:
                final_text = (
                    "I hit a tool execution issue that needs a follow-up fix. "
                    "Please try again after updating the configured tools."
                )
                self.chat_history.append({"role": "assistant", "text": final_text})
                self._trim_chat_history()
                return LoopResult(
                    progress_messages=progress_messages,
                    final_text=final_text,
                    iterations_used=iteration,
                )

            tool_exchange_items.extend(function_call_items)
            tool_exchange_items.extend(function_call_outputs)
            next_input = [*history_input, *tool_exchange_items]

        final_text = (
            "I reached my tool loop limit for this turn. "
            "I can continue in another turn if you want me to keep going."
        )
        self.chat_history.append({"role": "assistant", "text": final_text})
        self._trim_chat_history()
        return LoopResult(
            progress_messages=progress_messages,
            final_text=final_text,
            iterations_used=self.max_iterations,
        )
