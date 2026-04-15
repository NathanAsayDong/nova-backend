import json
import unittest
from unittest.mock import patch

from src.service.github_service import GithubService, GithubServiceError


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


class GithubServiceTests(unittest.TestCase):
    @patch("src.service.github_service.requests.request")
    def test_list_repositories_builds_request(self, mock_request):
        mock_request.return_value = _FakeResponse(
            200,
            [
                {
                    "id": 1,
                    "name": "api",
                    "full_name": "acme/api",
                    "private": True,
                    "default_branch": "main",
                    "html_url": "https://github.com/acme/api",
                    "clone_url": "https://github.com/acme/api.git",
                    "ssh_url": "git@github.com:acme/api.git",
                    "owner": {"login": "acme"},
                    "updated_at": "2026-04-12T00:00:00Z",
                    "pushed_at": "2026-04-12T00:00:00Z",
                }
            ],
        )
        service = GithubService(token="gh-token", base_url="https://api.github.com", api_version="2026-03-10")

        repos = service.list_repositories(per_page=30, page=1)
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["url"], "https://github.com/acme/api")

        kwargs = mock_request.call_args.kwargs
        self.assertEqual(kwargs["method"], "GET")
        self.assertEqual(kwargs["url"], "https://api.github.com/user/repos")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer gh-token")
        self.assertEqual(kwargs["headers"]["Accept"], "application/vnd.github+json")
        self.assertEqual(kwargs["headers"]["X-GitHub-Api-Version"], "2026-03-10")
        self.assertEqual(kwargs["params"]["per_page"], 30)
        self.assertEqual(kwargs["params"]["page"], 1)

    @patch("src.service.github_service.requests.request")
    def test_list_pull_requests_uses_repo_url_parser(self, mock_request):
        mock_request.return_value = _FakeResponse(
            200,
            [
                {
                    "number": 12,
                    "title": "feat: add health endpoint",
                    "state": "open",
                    "draft": False,
                    "html_url": "https://github.com/acme/api/pull/12",
                    "url": "https://api.github.com/repos/acme/api/pulls/12",
                    "created_at": "2026-04-12T00:00:00Z",
                    "updated_at": "2026-04-12T01:00:00Z",
                    "user": {"login": "alice"},
                    "head": {"ref": "feature/health"},
                    "base": {"ref": "main"},
                }
            ],
        )
        service = GithubService(token="gh-token")

        pulls = service.list_pull_requests(repository_url="https://github.com/acme/api.git", state="open", per_page=25, page=2)
        self.assertEqual(len(pulls), 1)
        self.assertEqual(pulls[0]["number"], 12)
        self.assertEqual(pulls[0]["head_branch"], "feature/health")

        kwargs = mock_request.call_args.kwargs
        self.assertEqual(kwargs["url"], "https://api.github.com/repos/acme/api/pulls")
        self.assertEqual(kwargs["params"]["state"], "open")
        self.assertEqual(kwargs["params"]["per_page"], 25)
        self.assertEqual(kwargs["params"]["page"], 2)

    def test_parse_repository_url(self):
        owner, repo = GithubService.parse_repository_url("https://github.com/openai/openai-python.git")
        self.assertEqual(owner, "openai")
        self.assertEqual(repo, "openai-python")

        owner2, repo2 = GithubService.parse_repository_url("github.com/acme/platform")
        self.assertEqual(owner2, "acme")
        self.assertEqual(repo2, "platform")

    def test_parse_repository_url_invalid(self):
        with self.assertRaises(GithubServiceError):
            GithubService.parse_repository_url("https://github.com/acme")

    def test_missing_token_raises(self):
        service = GithubService(token="")
        with self.assertRaises(GithubServiceError) as ctx:
            service.list_repositories()
        self.assertIn("GITHUB_TOKEN", str(ctx.exception))

    @patch("src.service.github_service.requests.request")
    def test_http_error_maps_to_service_error(self, mock_request):
        mock_request.return_value = _FakeResponse(403, {"message": "Resource not accessible"}, reason="Forbidden")
        service = GithubService(token="gh-token")

        with self.assertRaises(GithubServiceError) as ctx:
            service.list_repositories()

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Resource not accessible", str(ctx.exception))

    @patch("src.service.github_service.requests.request")
    def test_read_repository_code_directory(self, mock_request):
        mock_request.return_value = _FakeResponse(
            200,
            [
                {"type": "file", "name": "README.md", "path": "README.md", "size": 10, "html_url": "https://github.com/acme/api/blob/main/README.md"},
                {"type": "dir", "name": "src", "path": "src", "size": 0, "html_url": "https://github.com/acme/api/tree/main/src"},
            ],
        )
        service = GithubService(token="gh-token")

        result = service.read_repository_code(repository_url="https://github.com/acme/api", path="")
        self.assertEqual(result["kind"], "directory")
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["entries"][0]["name"], "README.md")

        kwargs = mock_request.call_args.kwargs
        self.assertEqual(kwargs["url"], "https://api.github.com/repos/acme/api/contents")

    @patch("src.service.github_service.requests.request")
    def test_read_repository_code_file(self, mock_request):
        mock_request.return_value = _FakeResponse(
            200,
            {
                "type": "file",
                "name": "app.py",
                "path": "src/app.py",
                "size": 18,
                "html_url": "https://github.com/acme/api/blob/main/src/app.py",
                "encoding": "base64",
                "content": "cHJpbnQoImhlbGxvIikK",
            },
        )
        service = GithubService(token="gh-token")

        result = service.read_repository_code(
            repository_url="https://github.com/acme/api",
            path="src/app.py",
            max_bytes=1000,
        )
        self.assertEqual(result["kind"], "file")
        self.assertEqual(result["path"], "src/app.py")
        self.assertEqual(result["content"], 'print("hello")\n')
        self.assertFalse(result["truncated"])


if __name__ == "__main__":
    unittest.main()
