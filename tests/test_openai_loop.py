import asyncio
import os
import unittest
from dataclasses import dataclass

from src.service.openai_service import OpenAIService
from src.service.tool_registry import ToolExecutionError


@dataclass
class FakeFunctionCall:
    name: str
    call_id: str
    arguments: str
    type: str = "function_call"


@dataclass
class FakeResponse:
    id: str
    output: list
    output_text: str


class FakeResponsesAPI:
    def __init__(self, responses: list[FakeResponse | Exception]) -> None:
        self._responses = responses
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise RuntimeError("No more fake responses configured")
        next_item = self._responses.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item


class FakeClient:
    def __init__(self, responses: list[FakeResponse | Exception]) -> None:
        self.responses = FakeResponsesAPI(responses)


class FakeToolService:
    def __init__(self, unrecoverable: bool = False) -> None:
        self.unrecoverable = unrecoverable

    def as_openai_tools(self):
        return [
            {
                "type": "function",
                "name": "demo_tool",
                "description": "demo",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
                "strict": True,
            }
        ]

    def execute(self, name, arguments):
        if self.unrecoverable:
            raise ToolExecutionError("boom", recoverable=False)
        return {"ok": True, "name": name, "arguments": arguments}


class OpenAILoopTests(unittest.TestCase):
    def setUp(self):
        os.environ["OPENAI_APIKEY"] = "test-key"

    def _build_service(self, fake_responses, max_iterations=5, tool_service=None):
        service = OpenAIService()
        service.client = FakeClient(fake_responses)
        service.max_iterations = max_iterations
        service.enable_dynamic_progress_updates = False
        if tool_service is not None:
            service.tool_service = tool_service
        return service

    def test_stops_when_no_tool_calls(self):
        service = self._build_service(
            [FakeResponse(id="resp-1", output=[], output_text="Final answer")]
        )

        result = asyncio.run(service.run_agent_loop("hello"))
        self.assertEqual(result.final_text, "Final answer")
        self.assertEqual(result.iterations_used, 1)
        self.assertEqual(result.progress_messages, [])

    def test_chains_function_call_outputs(self):
        responses = [
            FakeResponse(
                id="resp-1",
                output=[FakeFunctionCall(name="demo_tool", call_id="call-1", arguments='{"x":1}')],
                output_text="",
            ),
            FakeResponse(id="resp-2", output=[], output_text="Done"),
        ]
        service = self._build_service(responses, tool_service=FakeToolService())

        result = asyncio.run(service.run_agent_loop("do work"))

        self.assertEqual(result.final_text, "Done")
        self.assertEqual(result.iterations_used, 2)
        self.assertEqual(len(result.progress_messages), 1)

        second_call_input = service.client.responses.calls[1]["input"]
        input_types = {item.get("type") for item in second_call_input if isinstance(item, dict)}
        self.assertIn("function_call", input_types)
        self.assertIn("function_call_output", input_types)
        function_outputs = [item for item in second_call_input if item.get("type") == "function_call_output"]
        self.assertEqual(function_outputs[0]["call_id"], "call-1")

    def test_unrecoverable_tool_error_stops(self):
        responses = [
            FakeResponse(
                id="resp-1",
                output=[FakeFunctionCall(name="demo_tool", call_id="call-1", arguments="{}")],
                output_text="",
            )
        ]
        service = self._build_service(responses, tool_service=FakeToolService(unrecoverable=True))

        result = asyncio.run(service.run_agent_loop("do work"))
        self.assertIn("tool execution issue", result.final_text)
        self.assertEqual(result.iterations_used, 1)

    def test_stops_at_iteration_limit(self):
        responses = [
            FakeResponse(
                id="resp-1",
                output=[FakeFunctionCall(name="demo_tool", call_id="call-1", arguments="{}")],
                output_text="",
            ),
            FakeResponse(
                id="resp-2",
                output=[FakeFunctionCall(name="demo_tool", call_id="call-2", arguments="{}")],
                output_text="",
            ),
        ]
        service = self._build_service(responses, max_iterations=2, tool_service=FakeToolService())

        result = asyncio.run(service.run_agent_loop("keep going"))
        self.assertIn("loop limit", result.final_text)
        self.assertEqual(result.iterations_used, 2)

    def test_timeout_error_returns_fallback_message(self):
        service = self._build_service([TimeoutError("timed out while waiting")])

        result = asyncio.run(service.run_agent_loop("hello"))

        self.assertIn("backend timeout", result.final_text.lower())
        self.assertEqual(result.iterations_used, 0)

    def test_loop_timeout_returns_fallback_message(self):
        service = self._build_service([])
        service.loop_timeout_seconds = 0

        result = asyncio.run(service.run_agent_loop("hello"))

        self.assertIn("time limit", result.final_text.lower())
        self.assertEqual(result.iterations_used, 0)

    def test_replays_history_without_previous_response_id(self):
        responses = [
            FakeResponse(id="resp-1", output=[], output_text="First"),
            FakeResponse(id="resp-2", output=[], output_text="Second"),
        ]
        service = self._build_service(responses)

        first = asyncio.run(service.run_agent_loop("hello"))
        second = asyncio.run(service.run_agent_loop("again"))

        self.assertEqual(first.final_text, "First")
        self.assertEqual(second.final_text, "Second")
        self.assertNotIn("previous_response_id", service.client.responses.calls[0])
        self.assertNotIn("previous_response_id", service.client.responses.calls[1])
        first_call_roles = [item["role"] for item in service.client.responses.calls[0]["input"]]
        second_call_roles = [item["role"] for item in service.client.responses.calls[1]["input"]]
        self.assertEqual(first_call_roles, ["user"])
        self.assertEqual(second_call_roles, ["user", "assistant", "user"])

    def test_progress_callback_receives_messages(self):
        responses = [
            FakeResponse(
                id="resp-1",
                output=[FakeFunctionCall(name="demo_tool", call_id="call-1", arguments="{}")],
                output_text="",
            ),
            FakeResponse(id="resp-2", output=[], output_text="Done"),
        ]
        service = self._build_service(responses, tool_service=FakeToolService())

        captured: list[tuple[int, str]] = []

        async def on_progress(text: str, iteration: int) -> None:
            captured.append((iteration, text))

        result = asyncio.run(service.run_agent_loop("check", progress_callback=on_progress))

        self.assertEqual(result.final_text, "Done")
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][0], 1)
        self.assertTrue(captured[0][1])


if __name__ == "__main__":
    unittest.main()
