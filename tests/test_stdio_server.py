"""Tests for coding_agent.mcp.stdio_server's line-range read_file handling."""

import tempfile
from pathlib import Path

import pytest

from coding_agent.mcp.stdio_server import MCPStdioServer


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
