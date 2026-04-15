"""
Manual smoke test for Nova agentic coding tools.

Usage:
  cd backend-python
  ./venv/bin/python tests/manual_smoke_test_agentic_tools.py

Required env vars:
  OPENAI_API_KEY (or OPENAI_APIKEY)
  CURSOR_API_KEY
  GITHUB_TOKEN
"""

from __future__ import annotations

import json

from src.service.tool_service import ToolService


def main() -> None:
    tool_service = ToolService()

    print("1) GET /tools equivalent")
    tools = tool_service.list_tools()
    print(json.dumps([tool["name"] for tool in tools], indent=2))

    print("\n2) github_list_repos")
    repos = tool_service.execute(
        "github_list_repos",
        {
            "visibility": "all",
            "limit": 5,
            "page": 1,
        },
    )
    print(json.dumps(repos, indent=2))

    repositories = repos.get("repositories") or []
    if not repositories:
        print("No repositories found; stopping smoke test.")
        return

    first_repo = repositories[0].get("url")
    if not first_repo:
        print("First repository has no URL; stopping smoke test.")
        return

    print("\n3) write_code")
    launch = tool_service.execute(
        "write_code",
        {
            "prompt": "Create a tiny README note proving the agent can open this repo.",
            "repository_url": first_repo,
            "ref": "main",
            "auto_create_pr": True,
        },
    )
    print(json.dumps(launch, indent=2))

    agent_id = launch.get("agent_id")
    if not agent_id:
        print("No agent id returned; stopping smoke test.")
        return

    print("\n4) check_coding_agent")
    status = tool_service.execute(
        "check_coding_agent",
        {
            "agent_id": agent_id,
            "include_conversation": False,
        },
    )
    print(json.dumps(status, indent=2))

    print("\n5) check_prs")
    prs = tool_service.execute(
        "check_prs",
        {
            "repository_url": first_repo,
            "state": "open",
            "limit": 5,
            "page": 1,
        },
    )
    print(json.dumps(prs, indent=2))


if __name__ == "__main__":
    main()
