import unittest
from dataclasses import dataclass, field
from types import SimpleNamespace
from uuid import uuid4

from src.harness.agent_loop import AgentLoop
from src.model.conversation import Conversation
from src.model.mcp_server import McpServer
from src.model.message import MessageRole
from src.service.claude_service import ClaudeService, MCP_CONNECTOR_BETA
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

    def test_no_mcp_servers_means_no_connector_fields(self):
        kwargs = self.service._build_kwargs(tools=None, system=None, mcp_servers=None)
        self.assertNotIn("mcp_servers", kwargs)
        self.assertEqual(MCP_CONNECTOR_BETA, "mcp-client-2025-11-20")


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
            return FakeMessage(
                content=[
                    FakeBlock(type="mcp_tool_use", name="search_issues",
                              server_name="linear", input={"query": "bug"}),
                    FakeBlock(type="mcp_tool_result"),
                    FakeBlock(type="text", text="Found 3 issues."),
                ]
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
            return FakeMessage(content=[FakeBlock(type="text", text="ok")])

        self.agent_loop.claude_service.stream_response = fake_stream

        list(self.agent_loop.conversation_loop_events("hi", uuid4()))
        self.assertIsNone(self.captured["mcp_servers"])


if __name__ == "__main__":
    unittest.main()
