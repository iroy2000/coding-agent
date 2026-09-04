"""Tests for MCPClient / MCPClientManager (src/coding_agent/mcp/client.py)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coding_agent.mcp.client import MCPClient, MCPClientManager


def _make_tool(name="read_file", description="Reads a file"):
    tool = MagicMock()
    tool.name = name
    tool.description = description
    tool.inputSchema = {"type": "object"}
    return tool


class _FakeSession:
    def __init__(self, tools):
        self._tools = tools
        self.initialize = AsyncMock()
        self.call_tool = AsyncMock(return_value={"content": "ok"})

    async def list_tools(self):
        response = MagicMock()
        response.tools = self._tools
        return response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeStdioClient:
    def __init__(self, read="read", write="write"):
        self._pair = (read, write)

    async def __aenter__(self):
        return self._pair

    async def __aexit__(self, *exc):
        return False


class TestMCPClientConnect:
    @pytest.mark.asyncio
    async def test_connect_success_registers_tools(self):
        client = MCPClient("filesystem", {"command": "npx", "args": ["-y", "server"]})
        fake_session = _FakeSession([_make_tool("read_file"), _make_tool("list_files")])

        with (
            patch("coding_agent.mcp.client.stdio_client", return_value=_FakeStdioClient()),
            patch("coding_agent.mcp.client.ClientSession", return_value=fake_session),
        ):
            result = await client.connect()

        assert result is True
        assert client.session is fake_session
        names = [t["name"] for t in client.available_tools]
        assert names == ["read_file", "list_files"]

    @pytest.mark.asyncio
    async def test_connect_failure_returns_false(self):
        client = MCPClient("broken", {"command": "does-not-exist"})

        with patch("coding_agent.mcp.client.stdio_client", side_effect=RuntimeError("boom")):
            result = await client.connect()

        assert result is False
        assert client.session is None


class TestMCPClientToolCalls:
    @pytest.mark.asyncio
    async def test_list_tools_returns_cached_tools(self):
        client = MCPClient("srv", {"command": "cmd"})
        client.available_tools = [{"name": "explain_code", "description": "d", "input_schema": {}}]
        assert await client.list_tools() == client.available_tools

    @pytest.mark.asyncio
    async def test_call_tool_requires_connection(self):
        client = MCPClient("srv", {"command": "cmd"})
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.call_tool("read_file", {"path": "a.py"})

    @pytest.mark.asyncio
    async def test_call_tool_delegates_to_session(self):
        client = MCPClient("srv", {"command": "cmd"})
        client.session = _FakeSession([])
        result = await client.call_tool("read_file", {"path": "a.py"})
        assert result == {"content": "ok"}
        client.session.call_tool.assert_awaited_once_with("read_file", {"path": "a.py"})

    @pytest.mark.asyncio
    async def test_disconnect_clears_session(self):
        client = MCPClient("srv", {"command": "cmd"})
        client.session = _FakeSession([])
        await client.disconnect()
        assert client.session is None


class TestMCPClientManager:
    @pytest.mark.asyncio
    async def test_add_server_success_registers_tools(self):
        manager = MCPClientManager()
        fake_client = MagicMock()
        fake_client.connect = AsyncMock(return_value=True)
        fake_client.list_tools = AsyncMock(
            return_value=[{"name": "read_file", "description": "d", "input_schema": {}}]
        )

        with patch("coding_agent.mcp.client.MCPClient", return_value=fake_client):
            result = await manager.add_server("filesystem", {"command": "npx"})

        assert result is True
        assert manager.clients["filesystem"] is fake_client
        assert manager.tool_registry["filesystem.read_file"] == "filesystem"

    @pytest.mark.asyncio
    async def test_add_server_failure_is_not_registered(self):
        manager = MCPClientManager()
        fake_client = MagicMock()
        fake_client.connect = AsyncMock(return_value=False)

        with patch("coding_agent.mcp.client.MCPClient", return_value=fake_client):
            result = await manager.add_server("bad", {"command": "nope"})

        assert result is False
        assert "bad" not in manager.clients

    @pytest.mark.asyncio
    async def test_list_all_tools_aggregates_across_servers(self):
        manager = MCPClientManager()
        client_a = MagicMock()
        client_a.list_tools = AsyncMock(return_value=[{"name": "t1"}])
        manager.clients = {"a": client_a}

        all_tools = await manager.list_all_tools()
        assert all_tools == {"a": [{"name": "t1"}]}

    @pytest.mark.asyncio
    async def test_call_tool_routes_to_correct_server(self):
        manager = MCPClientManager()
        client_a = MagicMock()
        client_a.call_tool = AsyncMock(return_value="result")
        manager.clients = {"a": client_a}

        result = await manager.call_tool("a", "read_file", {"path": "x"})
        assert result == "result"
        client_a.call_tool.assert_awaited_once_with("read_file", {"path": "x"})

    @pytest.mark.asyncio
    async def test_call_tool_unknown_server_raises(self):
        manager = MCPClientManager()
        with pytest.raises(ValueError, match="not connected"):
            await manager.call_tool("missing", "tool", {})

    @pytest.mark.asyncio
    async def test_disconnect_all_clears_state(self):
        manager = MCPClientManager()
        client_a = MagicMock()
        client_a.disconnect = AsyncMock()
        manager.clients = {"a": client_a}
        manager.tool_registry = {"a.tool": "a"}

        await manager.disconnect_all()

        client_a.disconnect.assert_awaited_once()
        assert manager.clients == {}
        assert manager.tool_registry == {}

    @pytest.mark.asyncio
    async def test_load_config_adds_each_server(self, tmp_path):
        config_file = tmp_path / "mcp.json"
        config_file.write_text('{"servers": {"fs": {"command": "npx"}}}')

        manager = MCPClientManager()
        manager.add_server = AsyncMock(return_value=True)

        await manager.load_config(str(config_file))

        manager.add_server.assert_awaited_once_with("fs", {"command": "npx"})
