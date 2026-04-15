from __future__ import annotations

import os
from typing import Any

import requests


DEFAULT_CURSOR_API_BASE_URL = "https://api.cursor.com"
DEFAULT_CURSOR_API_TIMEOUT_SECONDS = 60.0
MAX_CURSOR_LIST_LIMIT = 100


class CursorServiceError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class CursorService:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = DEFAULT_CURSOR_API_TIMEOUT_SECONDS,
    ) -> None:
        self.api_key = (api_key or os.getenv("CURSOR_API_KEY") or "").strip()
        self.base_url = (base_url or os.getenv("CURSOR_API_BASE_URL") or DEFAULT_CURSOR_API_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds if timeout_seconds > 0 else DEFAULT_CURSOR_API_TIMEOUT_SECONDS

    def launch_agent(
        self,
        *,
        prompt_text: str,
        repository_url: str,
        ref: str = "main",
        branch_name: str | None = None,
        model: str | None = None,
        auto_create_pr: bool = True,
        open_as_cursor_github_app: bool = False,
        skip_reviewer_request: bool = False,
    ) -> dict[str, Any]:
        prompt = (prompt_text or "").strip()
        repository = (repository_url or "").strip()
        base_ref = (ref or "main").strip() or "main"

        if not prompt:
            raise CursorServiceError("'prompt_text' is required.")
        if not repository:
            raise CursorServiceError("'repository_url' is required.")

        payload: dict[str, Any] = {
            "prompt": {"text": prompt},
            "source": {
                "repository": repository,
                "ref": base_ref,
            },
            "target": {
                "autoCreatePr": auto_create_pr,
                "openAsCursorGithubApp": open_as_cursor_github_app,
                "skipReviewerRequest": skip_reviewer_request,
            },
        }

        if branch_name:
            payload["target"]["branchName"] = branch_name.strip()

        if model and model.strip():
            payload["model"] = model.strip()

        return self._request("POST", "/agents", payload=payload)

    def get_agent_status(self, agent_id: str) -> dict[str, Any]:
        cursor_agent_id = (agent_id or "").strip()
        if not cursor_agent_id:
            raise CursorServiceError("'agent_id' is required.")

        return self._request("GET", f"/agents/{cursor_agent_id}")

    def list_agents(
        self,
        *,
        limit: int = 20,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        if limit < 1 or limit > MAX_CURSOR_LIST_LIMIT:
            raise CursorServiceError(f"'limit' must be between 1 and {MAX_CURSOR_LIST_LIMIT}.")

        query_params: dict[str, Any] = {"limit": limit}
        cursor_token = (cursor or "").strip()
        if cursor_token:
            query_params["cursor"] = cursor_token

        return self._request("GET", "/agents", params=query_params)

    def add_followup(self, agent_id: str, prompt_text: str) -> dict[str, Any]:
        cursor_agent_id = (agent_id or "").strip()
        prompt = (prompt_text or "").strip()
        if not cursor_agent_id:
            raise CursorServiceError("'agent_id' is required.")
        if not prompt:
            raise CursorServiceError("'prompt_text' is required.")

        payload: dict[str, Any] = {
            "prompt": {
                "text": prompt,
            }
        }
        return self._request("POST", f"/agents/{cursor_agent_id}/followup", payload=payload)

    def get_agent_conversation(self, agent_id: str) -> dict[str, Any]:
        cursor_agent_id = (agent_id or "").strip()
        if not cursor_agent_id:
            raise CursorServiceError("'agent_id' is required.")

        return self._request("GET", f"/agents/{cursor_agent_id}/conversation")

    def delete_agent(self, agent_id: str) -> dict[str, Any]:
        cursor_agent_id = (agent_id or "").strip()
        if not cursor_agent_id:
            raise CursorServiceError("'agent_id' is required.")

        return self._request("DELETE", f"/agents/{cursor_agent_id}")

    def list_models(self) -> dict[str, Any]:
        return self._request("GET", "/models")

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/v0{path if path.startswith('/') else f'/{path}'}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self._headers(),
                params=params,
                json=payload,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise CursorServiceError(f"Cursor API request failed: {str(exc)}") from exc

        if response.status_code >= 400:
            details = self._parse_response_body(response)
            message = self._extract_error_message(details) or response.reason or "Unexpected Cursor API error"
            raise CursorServiceError(
                f"Cursor API error {response.status_code}: {message}",
                status_code=response.status_code,
                details=details,
            )

        parsed = self._parse_response_body(response)
        if isinstance(parsed, dict):
            return parsed
        if parsed is None:
            return {}
        return {"data": parsed}

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise CursorServiceError("CURSOR_API_KEY is not set.")

        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _parse_response_body(response: requests.Response) -> dict[str, Any] | list[Any] | None:
        if response.content is None or len(response.content) == 0:
            return {}

        try:
            return response.json()
        except ValueError:
            body = response.text.strip()
            if not body:
                return {}
            return {"raw": body}

    @staticmethod
    def _extract_error_message(details: dict[str, Any] | list[Any] | None) -> str:
        if isinstance(details, dict):
            if isinstance(details.get("error"), str):
                return details["error"]
            if isinstance(details.get("message"), str):
                return details["message"]
            nested_error = details.get("error")
            if isinstance(nested_error, dict):
                if isinstance(nested_error.get("message"), str):
                    return nested_error["message"]
            if isinstance(details.get("raw"), str):
                return details["raw"]
        return ""
