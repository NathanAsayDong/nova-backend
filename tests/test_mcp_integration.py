import unittest
from dataclasses import dataclass, field
from types import SimpleNamespace
from uuid import uuid4

from src.harness.agent_loop import AgentLoop
from src.model.conversation import Conversation
from src.model.mcp_server import McpServer
from src.model.message import MessageRole
from src.service.claude_service import (
    MCP_CONNECTOR_BETA,
    TOOL_SEARCH_TOOL_NAME,
    TOOL_SEARCH_TOOL_TYPE,
    ClaudeService,
    TurnStream,
)
from src.service.mcp_server_service import McpServerService
from src.service.tool_service import ToolService


class FakeMcpServerDao:
    def __init__(self, servers=()):
        self.servers = {s.id: s for s in servers}

    def get(self, id):
        return self.servers.get(int(id))

    def get_by_name(self, name):
        return next((s for s in self.servers.values() if s.name == name), None)

    def get_all(self):
        return sorted(self.servers.values(), key=lambda s: s.name)

    def get_enabled(self):
        return [s for s in self.get_all() if s.enabled]

    def create(self, entity):
        entity.id = max(self.servers, default=0) + 1
        self.servers[entity.id] = entity
        return entity

    def update(self, id, columns):
        server = self.servers.get(int(id))
        if server is None:
            return None
        for key, value in columns.items():
            setattr(server, key, value)
        return server

    def delete(self, id):
        self.servers.pop(int(id), None)


def build_service(servers=()) -> McpServerService:
    service = McpServerService.__new__(McpServerService)
    service.mcp_server_dao = FakeMcpServerDao(servers)
    return service


class McpServerServiceTests(unittest.TestCase):
    def test_create_masks_token(self):
        service = build_service()
        result = service.create_server("linear", "https://mcp.linear.app/mcp", "secret")
        self.assertTrue(result["has_token"])
        self.assertNotIn("secret", str(result))

    def test_rejects_bad_name_and_url(self):
        service = build_service()
        with self.assertRaises(ValueError):
            service.create_server("bad name!", "https://ok.example")
        with self.assertRaises(ValueError):
            service.create_server("ok", "ftp://nope.example")

    def test_rejects_duplicate_name(self):
        service = build_service()
        service.create_server("linear", "https://mcp.linear.app/mcp")
        with self.assertRaises(ValueError):
            service.create_server("linear", "https://other.example")

    def test_connector_servers_enabled_only_sorted(self):
        service = build_service(
            servers=(
                McpServer(id=1, name="zeta", url="https://z.example", enabled=True),
                McpServer(id=2, name="alpha", url="https://a.example", enabled=True,
                          auth_token="tok"),
                McpServer(id=3, name="off", url="https://off.example", enabled=False),
            )
        )
        servers = service.connector_servers()
        self.assertEqual([s["name"] for s in servers], ["alpha", "zeta"])
        self.assertEqual(servers[0]["authorization_token"], "tok")
        self.assertNotIn("authorization_token", servers[1])

    def test_update_can_toggle_and_clear_token(self):
        service = build_service(
            servers=(McpServer(id=1, name="a", url="https://a.example",
                               auth_token="tok", enabled=True),)
        )
        result = service.update_server(1, enabled=False)
        self.assertFalse(result["enabled"])
        result = service.update_server(1, auth_token="")
        self.assertFalse(result["has_token"])


class ClaudeServiceMcpKwargsTests(unittest.TestCase):
    def setUp(self):
        self.service = ClaudeService()

    def test_mcp_servers_and_toolsets_are_paired(self):
        kwargs = self.service._build_kwargs(
            tools=[{"name": "run_sql", "description": "", "input_schema": {}}],
            system=None,
            mcp_servers=[
                {"name": "zeta", "url": "https://z.example"},
                {"name": "alpha", "url": "https://a.example",
                 "authorization_token": "tok"},
            ],
        )
        servers = kwargs["mcp_servers"]
        self.assertEqual([s["name"] for s in servers], ["alpha", "zeta"])
        self.assertEqual(servers[0]["type"], "url")
        self.assertEqual(servers[0]["authorization_token"], "tok")
        self.assertNotIn("authorization_token", servers[1])

        toolsets = [t for t in kwargs["tools"] if t.get("type") == "mcp_toolset"]
        self.assertEqual(
            [t["mcp_server_name"] for t in toolsets], ["alpha", "zeta"]
        )
        # Deferred loading: schemas for these come on demand through the
        # tool search tool, not on every request.
        self.assertTrue(all(t["defer_loading"] is True for t in toolsets))

    def test_no_mcp_servers_means_no_connector_fields(self):
        kwargs = self.service._build_kwargs(tools=None, system=None, mcp_servers=None)
        self.assertNotIn("mcp_servers", kwargs)
        self.assertEqual(MCP_CONNECTOR_BETA, "mcp-client-2025-11-20")

    def test_tool_search_tool_added_alongside_mcp_and_never_deferred(self):
        kwargs = self.service._build_kwargs(
            tools=[{"name": "run_sql", "description": "", "input_schema": {}}],
            system=None,
            mcp_servers=[{"name": "linear", "url": "https://mcp.linear.app/mcp"}],
        )
        search_tools = [
            t for t in kwargs["tools"]
            if t.get("type") == TOOL_SEARCH_TOOL_TYPE
        ]
        self.assertEqual(len(search_tools), 1)
        self.assertEqual(search_tools[0]["name"], TOOL_SEARCH_TOOL_NAME)
        self.assertNotIn("defer_loading", search_tools[0])

        # At least one non-deferred tool exists (the client tool and the
        # search tool itself) — the API 400s if every tool is deferred.
        non_deferred = [t for t in kwargs["tools"] if not t.get("defer_loading")]
        self.assertTrue(non_deferred)

    def test_no_mcp_servers_means_no_tool_search_tool(self):
        kwargs = self.service._build_kwargs(
            tools=[{"name": "run_sql", "description": "", "input_schema": {}}],
            system=None,
            mcp_servers=None,
        )
        types = [t.get("type") for t in kwargs.get("tools", [])]
        self.assertNotIn(TOOL_SEARCH_TOOL_TYPE, types)


@dataclass
class FakeBlock:
    type: str
    name: str = ""
    server_name: str = ""
    input: dict = field(default_factory=dict)
    text: str = ""
    id: str = "blk"


@dataclass
class FakeMessage:
    content: list
    stop_reason: str = "end_turn"


class FakeToolDao:
    def get_all(self):
        return []


@dataclass
class FakeConversationService:
    conversations: dict = field(default_factory=dict)
    recorded: list = field(default_factory=list)

    def ensure_open_conversation(self, conversation_uuid):
        return self.conversations.setdefault(
            conversation_uuid, Conversation(id=1, uuid=conversation_uuid)
        )

    def load_history(self, conversation):
        return []

    def record_message(self, conversation, role, content):
        self.recorded.append((role, content))


class FakeMcpService:
    def __init__(self, servers):
        self.servers = servers

    def connector_servers(self):
        return self.servers


class AgentLoopMcpTests(unittest.TestCase):
    def setUp(self):
        self.agent_loop = AgentLoop()
        # Memory injection is covered in its own suite; these tests
        # assert on prompts, so keep retrieval out of them.
        self.agent_loop.memory_retrieval_enabled = False
        tool_service = ToolService.__new__(ToolService)
        tool_service.tool_dao = FakeToolDao()
        self.agent_loop.tool_service = tool_service
        self.conversation_service = FakeConversationService()
        self.agent_loop.conversation_service = self.conversation_service
        self.agent_loop.mcp_server_service = FakeMcpService(
            [{"name": "linear", "url": "https://mcp.linear.app/mcp"}]
        )
        self.captured = {}

    def test_mcp_servers_passed_and_blocks_surfaced(self):
        def fake_stream(prompt, role=None, context=None, tools=None,
                        system=None, mcp_servers=None):
            self.captured["mcp_servers"] = mcp_servers
            return TurnStream.completed(
                FakeMessage(
                    content=[
                        FakeBlock(type="mcp_tool_use", name="search_issues",
                                  server_name="linear", input={"query": "bug"}),
                        FakeBlock(type="mcp_tool_result"),
                        FakeBlock(type="text", text="Found 3 issues."),
                    ]
                )
            )

        self.agent_loop.claude_service.stream_response = fake_stream

        events = list(
            self.agent_loop.conversation_loop_events("check linear", uuid4())
        )

        self.assertEqual(
            self.captured["mcp_servers"],
            [{"name": "linear", "url": "https://mcp.linear.app/mcp"}],
        )
        tool_calls = [e for e in events if e["type"] == "tool_call"]
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0]["tool"], "linear.search_issues")
        self.assertEqual(tool_calls[0]["input"], {"query": "bug"})

        audit_rows = [
            content for role, content in self.conversation_service.recorded
            if role == MessageRole.TOOL and "linear.search_issues" in content
        ]
        self.assertEqual(len(audit_rows), 1)

    def test_registry_failure_degrades_to_no_mcp(self):
        class BrokenService:
            def connector_servers(self):
                raise RuntimeError("db down")

        self.agent_loop.mcp_server_service = BrokenService()

        def fake_stream(prompt, role=None, context=None, tools=None,
                        system=None, mcp_servers=None):
            self.captured["mcp_servers"] = mcp_servers
            return TurnStream.completed(
                FakeMessage(content=[FakeBlock(type="text", text="ok")])
            )

        self.agent_loop.claude_service.stream_response = fake_stream

        list(self.agent_loop.conversation_loop_events("hi", uuid4()))
        self.assertIsNone(self.captured["mcp_servers"])


class SanitizeMcpHistoryTests(unittest.TestCase):
    """
    `AgentLoop.sanitize_mcp_history` — the fix for conversation history
    containing mcp_tool_use/mcp_tool_result (or deferred tool-search) blocks
    getting a 400 when replayed after MCP servers are no longer attached.
    """

    def test_noop_when_mcp_is_available(self):
        history = [
            {
                "role": "assistant",
                "content": [
                    {"type": "mcp_tool_use", "id": "t1", "name": "search_issues",
                     "server_name": "linear", "input": {}},
                    {"type": "mcp_tool_result", "tool_use_id": "t1", "content": "ok"},
                ],
            }
        ]
        before = [dict(m) for m in history]
        result = AgentLoop.sanitize_mcp_history(history, mcp_available=True)
        self.assertEqual(result, before)
        self.assertIs(result, history)

    def test_strips_mcp_blocks_when_mcp_unavailable(self):
        history = [
            {"role": "user", "content": "check linear"},
            {
                "role": "assistant",
                "content": [
                    {"type": "mcp_tool_use", "id": "t1", "name": "search_issues",
                     "server_name": "linear", "input": {"query": "bug"}},
                    {"type": "mcp_tool_result", "tool_use_id": "t1", "content": "3 issues"},
                    {"type": "text", "text": "Found 3 issues."},
                ],
            },
        ]
        AgentLoop.sanitize_mcp_history(history, mcp_available=False)

        sanitized = history[1]["content"]
        types = [block["type"] for block in sanitized]
        self.assertNotIn("mcp_tool_use", types)
        self.assertNotIn("mcp_tool_result", types)
        # The model's own words are untouched.
        self.assertIn({"type": "text", "text": "Found 3 issues."}, sanitized)
        # Something readable stands in for what was dropped.
        self.assertTrue(
            any("linear.search_issues" in block.get("text", "") for block in sanitized)
        )

    def test_strips_tool_search_blocks_too(self):
        history = [
            {
                "role": "assistant",
                "content": [
                    {"type": "server_tool_use", "id": "t1",
                     "name": "tool_search_tool_bm25", "input": {"query": "sensor"}},
                    {"type": "tool_search_tool_result", "tool_use_id": "t1",
                     "content": []},
                ],
            }
        ]
        AgentLoop.sanitize_mcp_history(history, mcp_available=False)
        types = [block["type"] for block in history[0]["content"]]
        self.assertEqual(types, ["text", "text"])

    def test_leaves_non_mcp_messages_and_plain_tool_blocks_alone(self):
        history = [
            {"role": "user", "content": "hi"},
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me check."},
                    {"type": "tool_use", "id": "x1", "name": "get_weather", "input": {}},
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "x1", "content": "sunny"},
                ],
            },
        ]
        before = [dict(m) for m in history]
        AgentLoop.sanitize_mcp_history(history, mcp_available=False)
        self.assertEqual(history, before)

    def test_message_left_with_nothing_gets_a_placeholder(self):
        history = [
            {
                "role": "assistant",
                "content": [
                    {"type": "mcp_tool_use", "id": "t1", "name": "ping",
                     "server_name": "mcp", "input": {}},
                    {"type": "mcp_tool_result", "tool_use_id": "t1", "content": "ok"},
                ],
            }
        ]
        AgentLoop.sanitize_mcp_history(history, mcp_available=False)
        self.assertEqual(len(history[0]["content"]), 2)
        self.assertTrue(all(b["type"] == "text" for b in history[0]["content"]))


class ConversationTurnMcpDisabledReplayTests(unittest.TestCase):
    """
    End-to-end: a conversation that called an MCP tool while MCP was enabled,
    then continues after MCP is disabled, must not resend mcp_tool_use blocks
    to the model.
    """

    def setUp(self):
        self.agent_loop = AgentLoop()
        self.agent_loop.memory_retrieval_enabled = False
        tool_service = ToolService.__new__(ToolService)
        tool_service.tool_dao = FakeToolDao()
        self.agent_loop.tool_service = tool_service
        self.conversation_service = FakeConversationService()
        self.agent_loop.conversation_service = self.conversation_service
        self.conversation_uuid = uuid4()
        # Seed in-process history as if an earlier, MCP-enabled turn left an
        # mcp_tool_use/mcp_tool_result pair behind.
        self.agent_loop.conversations[self.conversation_uuid] = [
            {"role": "user", "content": "check linear"},
            {
                "role": "assistant",
                "content": [
                    {"type": "mcp_tool_use", "id": "t1", "name": "search_issues",
                     "server_name": "linear", "input": {"query": "bug"}},
                    {"type": "mcp_tool_result", "tool_use_id": "t1", "content": "3 issues"},
                    {"type": "text", "text": "Found 3 issues."},
                ],
            },
        ]
        # MCP now disabled: no servers registered.
        self.agent_loop.mcp_server_service = FakeMcpService([])

    def test_next_turn_sends_sanitized_history(self):
        captured = {}

        def fake_stream(prompt, role=None, context=None, tools=None,
                        system=None, mcp_servers=None):
            captured["context"] = [dict(m) for m in context]
            return TurnStream.completed(
                FakeMessage(content=[FakeBlock(type="text", text="Still here.")])
            )

        self.agent_loop.claude_service.stream_response = fake_stream

        list(
            self.agent_loop.conversation_loop_events(
                "anything new?", self.conversation_uuid
            )
        )

        sent_assistant_msg = next(
            m for m in captured["context"] if m["role"] == "assistant"
        )
        sent_types = [block["type"] for block in sent_assistant_msg["content"]]
        self.assertNotIn("mcp_tool_use", sent_types)
        self.assertNotIn("mcp_tool_result", sent_types)


if __name__ == "__main__":
    unittest.main()
