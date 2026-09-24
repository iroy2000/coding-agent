"""Tests for coding_agent.mcp.stdio_server's line-range read_file handling
and search_history tool."""

import tempfile
from pathlib import Path

import pytest

from coding_agent.mcp.stdio_server import MCPStdioServer
from coding_agent.storage.history import HistoryManager


@pytest.fixture
def server_with_multiline_file():
    """Create an MCPStdioServer pointed at a workspace with a 5-line file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        (workspace / "multi.txt").write_text("line1\nline2\nline3\nline4\nline5\n")
        yield MCPStdioServer(workspace_path=str(workspace), enable_ai_tools=False)


class TestHandleReadFileLineRange:
    @pytest.mark.asyncio
    async def test_normal_range(self, server_with_multiline_file):
        result = await server_with_multiline_file._handle_read_file(
            "multi.txt", start_line=2, end_line=3
        )
        text = result[0].text
        assert "line2" in text
        assert "line3" in text
        assert "line1" not in text
        assert "line4" not in text

    @pytest.mark.asyncio
    async def test_start_line_zero_is_rejected(self, server_with_multiline_file):
        """start_line=0 violates the tool's own schema (minimum: 1) and must
        be rejected rather than silently treated as "no start line" (a
        regression: `start_line if start_line else 0` treats 0 as falsy)."""
        result = await server_with_multiline_file._handle_read_file(
            "multi.txt", start_line=0, end_line=2
        )
        text = result[0].text
        assert "error" in text.lower()

    @pytest.mark.asyncio
    async def test_end_line_zero_is_rejected(self, server_with_multiline_file):
        result = await server_with_multiline_file._handle_read_file(
            "multi.txt", start_line=1, end_line=0
        )
        text = result[0].text
        assert "error" in text.lower()

    @pytest.mark.asyncio
    async def test_negative_start_line_is_rejected(self, server_with_multiline_file):
        result = await server_with_multiline_file._handle_read_file(
            "multi.txt", start_line=-1, end_line=2
        )
        text = result[0].text
        assert "error" in text.lower()

    @pytest.mark.asyncio
    async def test_start_line_beyond_eof_is_rejected(self, server_with_multiline_file):
        result = await server_with_multiline_file._handle_read_file(
            "multi.txt", start_line=100, end_line=200
        )
        text = result[0].text
        assert "error" in text.lower()

    @pytest.mark.asyncio
    async def test_end_line_before_start_line_is_rejected(self, server_with_multiline_file):
        result = await server_with_multiline_file._handle_read_file(
            "multi.txt", start_line=4, end_line=2
        )
        text = result[0].text
        assert "error" in text.lower()

    @pytest.mark.asyncio
    async def test_no_range_returns_whole_file(self, server_with_multiline_file):
        result = await server_with_multiline_file._handle_read_file("multi.txt")
        text = result[0].text
        for line in ("line1", "line2", "line3", "line4", "line5"):
            assert line in text


class TestHandleSearchHistory:
    """Regression tests for _handle_search_history, which previously called a
    nonexistent `HistoryManager.search_messages()` method - every call
    always failed with an AttributeError caught by the generic except
    clause, so the tool silently always returned an error."""

    @pytest.fixture
    def server_with_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            history_dir = workspace / "history"
            srv = MCPStdioServer(workspace_path=str(workspace), enable_ai_tools=False)
            hm = HistoryManager(history_dir=str(history_dir))
            session_id = hm.create_session(workspace_path=str(workspace), model="test-model")
            hm.add_message(session_id, "user", "how do I sort a list in python")
            hm.add_message(session_id, "assistant", "use sorted() or list.sort()")
            srv.history_manager = hm
            srv._test_session_id = session_id
            yield srv

    @pytest.mark.asyncio
    async def test_finds_matching_message(self, server_with_history):
        result = await server_with_history._handle_search_history("sort a list")
        text = result[0].text
        assert "Found 1 results" in text
        assert "how do I sort a list in python" in text

    @pytest.mark.asyncio
    async def test_no_match_reports_no_results(self, server_with_history):
        result = await server_with_history._handle_search_history("zzzznomatch")
        assert "No results found" in result[0].text

    @pytest.mark.asyncio
    async def test_session_id_filter_matches(self, server_with_history):
        result = await server_with_history._handle_search_history(
            "sort", session_id=server_with_history._test_session_id
        )
        assert "Found 1 results" in result[0].text

    @pytest.mark.asyncio
    async def test_session_id_filter_excludes_other_sessions(self, server_with_history):
        result = await server_with_history._handle_search_history(
            "sort", session_id="some-other-session-id"
        )
        assert "No results found" in result[0].text

    @pytest.mark.asyncio
    async def test_history_tools_disabled_reports_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            srv = MCPStdioServer(workspace_path=tmpdir, enable_ai_tools=False)
            result = await srv._handle_search_history("anything")
            assert "History tools not enabled" in result[0].text
