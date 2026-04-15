from __future__ import annotations

import base64
import binascii
import os
from typing import Any
from urllib.parse import urlparse

import requests


DEFAULT_GITHUB_API_BASE_URL = "https://api.github.com"
DEFAULT_GITHUB_API_VERSION = "2026-03-10"
DEFAULT_GITHUB_API_TIMEOUT_SECONDS = 30.0
MAX_GITHUB_PER_PAGE = 100
DEFAULT_REPO_FILE_MAX_BYTES = 120_000
MIN_REPO_FILE_MAX_BYTES = 512
MAX_REPO_FILE_MAX_BYTES = 500_000


class GithubServiceError(Exception):
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


class GithubService:
    def __init__(
        self,
        *,
        token: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        timeout_seconds: float = DEFAULT_GITHUB_API_TIMEOUT_SECONDS,
    ) -> None:
        self.token = (token or os.getenv("GITHUB_TOKEN") or "").strip()
        self.base_url = (base_url or os.getenv("GITHUB_API_BASE_URL") or DEFAULT_GITHUB_API_BASE_URL).rstrip("/")
        self.api_version = (api_version or os.getenv("GITHUB_API_VERSION") or DEFAULT_GITHUB_API_VERSION).strip()
        self.timeout_seconds = timeout_seconds if timeout_seconds > 0 else DEFAULT_GITHUB_API_TIMEOUT_SECONDS

    def list_repositories(
        self,
        *,
        visibility: str = "all",
        affiliation: str = "owner,collaborator,organization_member",
        per_page: int = 30,
        page: int = 1,
        sort: str = "updated",
        direction: str = "desc",
    ) -> list[dict[str, Any]]:
        self._validate_per_page(per_page)
        if page < 1:
            raise GithubServiceError("'page' must be at least 1.")

        payload = self._request(
            "GET",
            "/user/repos",
            params={
                "visibility": visibility,
                "affiliation": affiliation,
                "per_page": per_page,
                "page": page,
                "sort": sort,
                "direction": direction,
            },
        )

        if not isinstance(payload, list):
            raise GithubServiceError("Unexpected GitHub response while listing repositories.")

        return [self._normalize_repository(repo) for repo in payload if isinstance(repo, dict)]

    def list_pull_requests(
        self,
        *,
        repository_url: str,
        state: str = "open",
        per_page: int = 30,
        page: int = 1,
        sort: str = "updated",
        direction: str = "desc",
    ) -> list[dict[str, Any]]:
        self._validate_per_page(per_page)
        if page < 1:
            raise GithubServiceError("'page' must be at least 1.")

        owner, repo = self.parse_repository_url(repository_url)

        payload = self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls",
            params={
                "state": state,
                "per_page": per_page,
                "page": page,
                "sort": sort,
                "direction": direction,
            },
        )

        if not isinstance(payload, list):
            raise GithubServiceError("Unexpected GitHub response while listing pull requests.")

        normalized: list[dict[str, Any]] = []
        for pr in payload:
            if not isinstance(pr, dict):
                continue
            normalized.append(
                {
                    "number": pr.get("number"),
                    "title": pr.get("title"),
                    "state": pr.get("state"),
                    "draft": bool(pr.get("draft", False)),
                    "html_url": pr.get("html_url"),
                    "api_url": pr.get("url"),
                    "created_at": pr.get("created_at"),
                    "updated_at": pr.get("updated_at"),
                    "user": (pr.get("user") or {}).get("login"),
                    "head_branch": (pr.get("head") or {}).get("ref"),
                    "base_branch": (pr.get("base") or {}).get("ref"),
                }
            )

        return normalized

    def read_repository_code(
        self,
        *,
        repository_url: str,
        path: str = "",
        ref: str | None = None,
        max_bytes: int = DEFAULT_REPO_FILE_MAX_BYTES,
    ) -> dict[str, Any]:
        owner, repo = self.parse_repository_url(repository_url)
        clean_path = path.strip().strip("/")
        max_file_bytes = self._coerce_max_bytes(max_bytes)

        endpoint = f"/repos/{owner}/{repo}/contents"
        if clean_path:
            endpoint = f"{endpoint}/{clean_path}"

        params: dict[str, Any] = {}
        if isinstance(ref, str) and ref.strip():
            params["ref"] = ref.strip()

        payload = self._request("GET", endpoint, params=params or None)
        normalized_repo_url = f"https://github.com/{owner}/{repo}"

        if isinstance(payload, list):
            entries: list[dict[str, Any]] = []
            for item in payload:
                if not isinstance(item, dict):
                    continue
                entries.append(
                    {
                        "type": item.get("type"),
                        "name": item.get("name"),
                        "path": item.get("path"),
                        "size": item.get("size"),
                        "url": item.get("html_url"),
                    }
                )
            return {
                "repository_url": normalized_repo_url,
                "path": clean_path,
                "ref": params.get("ref"),
                "kind": "directory",
                "count": len(entries),
                "entries": entries,
            }

        if not isinstance(payload, dict):
            raise GithubServiceError("Unexpected GitHub response while reading repository code.")

        item_type = str(payload.get("type") or "").lower()
        if item_type != "file":
            raise GithubServiceError("Requested path is not a file or directory.")

        encoding = str(payload.get("encoding") or "")
        raw_content = payload.get("content")
        if not isinstance(raw_content, str):
            raise GithubServiceError("GitHub returned file content in an unexpected format.")

        if encoding != "base64":
            raise GithubServiceError(f"Unsupported file encoding from GitHub: {encoding or 'unknown'}.")

        # GitHub includes newlines in base64 payloads for large files.
        compact_b64 = "".join(raw_content.splitlines())
        try:
            decoded_bytes = base64.b64decode(compact_b64, validate=False)
        except (binascii.Error, ValueError) as exc:
            raise GithubServiceError("Failed to decode GitHub file content.") from exc

        was_truncated = len(decoded_bytes) > max_file_bytes
        visible_bytes = decoded_bytes[:max_file_bytes]
        text = visible_bytes.decode("utf-8", errors="replace")

        return {
            "repository_url": normalized_repo_url,
            "path": payload.get("path") or clean_path,
            "ref": params.get("ref"),
            "kind": "file",
            "name": payload.get("name"),
            "size": payload.get("size"),
            "url": payload.get("html_url"),
            "encoding": "utf-8",
            "content": text,
            "truncated": was_truncated,
            "content_bytes_returned": len(visible_bytes),
            "content_bytes_total": len(decoded_bytes),
        }

    @staticmethod
    def normalize_repository_url(repository_url: str) -> str:
        owner, repo = GithubService.parse_repository_url(repository_url)
        return f"https://github.com/{owner}/{repo}"

    @staticmethod
    def parse_repository_url(repository_url: str) -> tuple[str, str]:
        raw = (repository_url or "").strip()
        if not raw:
            raise GithubServiceError("'repository_url' is required.")

        candidate = raw
        if "://" not in candidate:
            candidate = f"https://{candidate}"

        parsed = urlparse(candidate)

        host = (parsed.netloc or "").lower()
        if host.endswith("github.com"):
            path = parsed.path.strip("/")
        elif host:
            path = parsed.path.strip("/")
        else:
            # Handle owner/repo style without host.
            path = candidate.strip("/")

        pieces = [segment for segment in path.split("/") if segment]
        if len(pieces) < 2:
            raise GithubServiceError(
                "Invalid repository URL. Expected format like https://github.com/<owner>/<repo>."
            )

        owner = pieces[0].strip()
        repo = pieces[1].strip()
        if repo.endswith(".git"):
            repo = repo[:-4]

        if not owner or not repo:
            raise GithubServiceError(
                "Invalid repository URL. Expected format like https://github.com/<owner>/<repo>."
            )

        return owner, repo

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        url = f"{self.base_url}{path if path.startswith('/') else f'/{path}'}"

        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise GithubServiceError(f"GitHub API request failed: {str(exc)}") from exc

        if response.status_code >= 400:
            details = self._parse_response_body(response)
            message = self._extract_error_message(details) or response.reason or "Unexpected GitHub API error"
            raise GithubServiceError(
                f"GitHub API error {response.status_code}: {message}",
                status_code=response.status_code,
                details=details if isinstance(details, dict) else {},
            )

        parsed = self._parse_response_body(response)
        if isinstance(parsed, (dict, list)):
            return parsed
        return {}

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise GithubServiceError("GITHUB_TOKEN is not set.")

        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.api_version,
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
            if isinstance(details.get("message"), str):
                return details["message"]
            if isinstance(details.get("error"), str):
                return details["error"]
            if isinstance(details.get("raw"), str):
                return details["raw"]
        return ""

    @staticmethod
    def _normalize_repository(repo: dict[str, Any]) -> dict[str, Any]:
        owner = (repo.get("owner") or {}).get("login")
        name = repo.get("name")
        html_url = repo.get("html_url")

        if isinstance(owner, str) and isinstance(name, str) and not html_url:
            html_url = f"https://github.com/{owner}/{name}"

        return {
            "id": repo.get("id"),
            "name": name,
            "full_name": repo.get("full_name"),
            "private": bool(repo.get("private", False)),
            "default_branch": repo.get("default_branch"),
            "url": html_url,
            "clone_url": repo.get("clone_url"),
            "ssh_url": repo.get("ssh_url"),
            "owner": owner,
            "updated_at": repo.get("updated_at"),
            "pushed_at": repo.get("pushed_at"),
        }

    @staticmethod
    def _validate_per_page(per_page: int) -> None:
        if per_page < 1 or per_page > MAX_GITHUB_PER_PAGE:
            raise GithubServiceError(f"'per_page' must be between 1 and {MAX_GITHUB_PER_PAGE}.")

    @staticmethod
    def _coerce_max_bytes(max_bytes: int) -> int:
        if max_bytes < MIN_REPO_FILE_MAX_BYTES:
            raise GithubServiceError(f"'max_bytes' must be at least {MIN_REPO_FILE_MAX_BYTES}.")
        if max_bytes > MAX_REPO_FILE_MAX_BYTES:
            raise GithubServiceError(f"'max_bytes' must be at most {MAX_REPO_FILE_MAX_BYTES}.")
        return max_bytes
