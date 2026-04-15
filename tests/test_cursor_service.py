import json
import unittest
from unittest.mock import patch

from src.service.cursor_service import CursorService, CursorServiceError


class _FakeResponse:
    def __init__(self, status_code: int, payload=None, reason: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.reason = reason
        if payload is None:
            self.text = ""
            self.content = b""
        else:
            self.text = json.dumps(payload)
            self.content = self.text.encode("utf-8")

    def json(self):
        return self._payload


class CursorServiceTests(unittest.TestCase):
    @patch("src.service.cursor_service.requests.request")
    def test_launch_agent_builds_request(self, mock_request):
        mock_request.return_value = _FakeResponse(200, {"id": "bc_abc123", "status": "RUNNING"})
        service = CursorService(api_key="cursor-key", base_url="https://api.cursor.com", timeout_seconds=12)

        result = service.launch_agent(
            prompt_text="Add unit tests",
            repository_url="https://github.com/acme/api",
            ref="main",
            branch_name="cursor/add-tests",
            model="default",
            auto_create_pr=True,
        )

        self.assertEqual(result["id"], "bc_abc123")
        self.assertEqual(mock_request.call_count, 1)

        kwargs = mock_request.call_args.kwargs
        self.assertEqual(kwargs["method"], "POST")
        self.assertEqual(kwargs["url"], "https://api.cursor.com/v0/agents")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer cursor-key")
        self.assertEqual(kwargs["json"]["prompt"]["text"], "Add unit tests")
        self.assertEqual(kwargs["json"]["source"]["repository"], "https://github.com/acme/api")
        self.assertEqual(kwargs["json"]["source"]["ref"], "main")
        self.assertEqual(kwargs["json"]["target"]["branchName"], "cursor/add-tests")
        self.assertEqual(kwargs["json"]["model"], "default")

    def test_missing_api_key_raises(self):
        service = CursorService(api_key="")
        with self.assertRaises(CursorServiceError) as ctx:
            service.list_agents()
        self.assertIn("CURSOR_API_KEY", str(ctx.exception))

    @patch("src.service.cursor_service.requests.request")
    def test_http_error_maps_to_service_error(self, mock_request):
        mock_request.return_value = _FakeResponse(401, {"message": "Unauthorized"}, reason="Unauthorized")
        service = CursorService(api_key="cursor-key")

        with self.assertRaises(CursorServiceError) as ctx:
            service.get_agent_status("bc_abc123")

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Unauthorized", str(ctx.exception))

    def test_list_limit_validation(self):
        service = CursorService(api_key="cursor-key")
        with self.assertRaises(CursorServiceError):
            service.list_agents(limit=0)
        with self.assertRaises(CursorServiceError):
            service.list_agents(limit=101)


if __name__ == "__main__":
    unittest.main()
