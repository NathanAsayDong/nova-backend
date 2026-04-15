# Nova Agentic Coding Workflow Tools

This document describes the Cursor + GitHub tooling added to Nova's backend tool system.

## Environment Setup

Add these variables to `.env`:

- `CURSOR_API_KEY` (required)
- `GITHUB_TOKEN` (required)
- `CURSOR_API_BASE_URL` (optional, default `https://api.cursor.com`)
- `GITHUB_API_BASE_URL` (optional, default `https://api.github.com`)
- `GITHUB_API_VERSION` (optional, default `2026-03-10`)
- `CODE_PLANNER_MODEL` (optional, default `gpt-5.4-mini-2026-03-17`)

### GitHub Token Requirements

Use a fine-grained PAT when possible.

Minimum repository permissions for this v1:

- `Metadata` (read) to list repositories
- `Pull requests` (read) to list/check PRs

If you need private or org repos, set token resource owner and repository selection to include those repositories.

## New Tools

### `github_list_repos`
Lists repositories available to the configured `GITHUB_TOKEN`.

Input schema highlights:

- `visibility`: `all | public | private`
- `affiliation`: comma-separated values (default `owner,collaborator,organization_member`)
- `limit`: `1-100`
- `page`: `>=1`
- `sort`: `created | updated | pushed | full_name`
- `direction`: `asc | desc`

Example call payload:

```json
{
  "visibility": "all",
  "limit": 20,
  "page": 1
}
```

### `write_code`
Launches a Cursor background coding agent for a repo.

Input schema highlights:

- `prompt` (required)
- `repository_url` (required)
- `ref` (optional, default `main`)
- `branch_name` (optional)
- `model` (optional)
- `auto_create_pr` (optional, default `true`)

Example:

```json
{
  "prompt": "Add a health endpoint and tests",
  "repository_url": "https://github.com/acme/api",
  "ref": "main",
  "auto_create_pr": true
}
```

### `check_coding_agent`
Checks Cursor agent status and optionally conversation history.

Input schema highlights:

- `agent_id` (required)
- `include_conversation` (optional, default `false`)

Example:

```json
{
  "agent_id": "bc_abc123",
  "include_conversation": true
}
```

### `check_prs`
Lists pull requests for a specific repository.

Input schema highlights:

- `repository_url` (required)
- `state`: `open | closed | all`
- `limit`: `1-100`
- `page`: `>=1`

Example:

```json
{
  "repository_url": "https://github.com/acme/api",
  "state": "open",
  "limit": 25
}
```

### `code_planner`
Uses OpenAI to generate an implementation plan and a Cursor-ready prompt.

Input schema highlights:

- `objective` (required)
- `repository_url` (optional)
- `context` (optional)

Example:

```json
{
  "objective": "Implement OAuth login with refresh tokens",
  "repository_url": "https://github.com/acme/api",
  "context": "Need backward compatibility with legacy sessions"
}
```

## Workflow

1. Call `github_list_repos` to fetch candidate repositories.
2. Choose repository URL and call `code_planner` (optional but recommended).
3. Call `write_code` with a direct coding prompt or the planner output prompt.
4. Poll `check_coding_agent` until terminal status.
5. Call `check_prs` for the repository to verify the generated PR.

## Error Handling Notes

- Missing credentials surface as recoverable tool errors.
- Cursor and GitHub API HTTP errors are mapped with status + message context.
- `write_code` and `check_prs` validate repository URLs before API calls.
- `code_planner` uses `OPENAI_API_KEY`/`OPENAI_APIKEY` and returns recoverable errors on timeout/network failure.

## Rate-Limit Notes

- GitHub API requests are paginated (`limit`/`page`) and subject to account rate limits.
- Cursor background-agent endpoints are also rate-limited by account.
- If you later use Cursor repository listing (`GET /v0/repositories`), note that endpoint has strict limits and should be used sparingly.
