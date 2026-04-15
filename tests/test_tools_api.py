import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.service.tool_registry import ToolRegistry


class ToolsApiTests(unittest.TestCase):
    def _write_tool(self, tools_dir: Path, payload: dict) -> None:
        file_path = tools_dir / f"{payload['name']}.txt"
        file_path.write_text(json.dumps(payload), encoding="utf-8")

    def _tool_payload(self, name: str = "demo_tool", enabled: bool = True) -> dict:
        return {
            "name": name,
            "description": "Demo tool",
            "enabled": enabled,
            "handler_id": "get_current_time_handler",
            "json_schema": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        }

    def test_get_and_patch_tools(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["OPENAI_APIKEY"] = "test-key"
            from src.controller.transcribe_controller import openai_service, router, tool_service

            tools_dir = Path(temp_dir)
            self._write_tool(tools_dir, self._tool_payload(name="demo_tool", enabled=True))

            tool_service.registry = ToolRegistry(tools_dir=tools_dir)
            openai_service.tool_service = tool_service

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            get_response = client.get("/tools")
            self.assertEqual(get_response.status_code, 200)
            names = {tool["name"] for tool in get_response.json()}
            self.assertIn("demo_tool", names)
            self.assertIn("write_code", names)
            self.assertIn("github_list_repos", names)

            patch_response = client.patch("/tools/demo_tool", json={"enabled": False})
            self.assertEqual(patch_response.status_code, 200)
            self.assertFalse(patch_response.json()["enabled"])

            patch_write_code = client.patch("/tools/write_code", json={"enabled": False})
            self.assertEqual(patch_write_code.status_code, 200)
            self.assertFalse(patch_write_code.json()["enabled"])

            payload = json.loads((tools_dir / "demo_tool.txt").read_text(encoding="utf-8"))
            self.assertFalse(payload["enabled"])

            write_code_payload = json.loads((tools_dir / "write_code.txt").read_text(encoding="utf-8"))
            self.assertFalse(write_code_payload["enabled"])


if __name__ == "__main__":
    unittest.main()
