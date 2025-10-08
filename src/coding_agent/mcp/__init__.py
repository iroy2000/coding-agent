"""Model Context Protocol (MCP) integration for coding-agent."""

from coding_agent.mcp.server import MCPServer
from coding_agent.mcp.client import MCPClient

__all__ = ["MCPServer", "MCPClient"]
