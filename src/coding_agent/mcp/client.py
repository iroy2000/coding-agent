"""MCP Client implementation - connects to external MCP servers."""

import asyncio
import json
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """
    MCP Client for connecting to external MCP servers.
    
    This allows the coding-agent to use tools from external MCP servers like:
    - Filesystem servers
    - Database servers (PostgreSQL, MySQL, etc.)
    - API servers (GitHub, Slack, etc.)
    - Custom company servers
    """

    def __init__(self, server_name: str, config: Dict[str, Any]):
        """
        Initialize MCP client.

        Args:
            server_name: Name of the server
            config: Server configuration (command, args, env)
        """
        self.server_name = server_name
        self.config = config
        self.session: Optional[ClientSession] = None
        self.available_tools: List[Dict[str, Any]] = []

    async def connect(self) -> bool:
        """
        Connect to the MCP server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            server_params = StdioServerParameters(
                command=self.config["command"],
                args=self.config.get("args", []),
                env=self.config.get("env", {}),
            )

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    self.session = session
                    await session.initialize()
                    
                    # List available tools
                    tools_response = await session.list_tools()
                    self.available_tools = [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "input_schema": tool.inputSchema,
                        }
                        for tool in tools_response.tools
                    ]
                    
                    return True
        except Exception as e:
            print(f"Failed to connect to {self.server_name}: {str(e)}")
            return False

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from the server.

        Returns:
            List of tool definitions
        """
        return self.available_tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the remote server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result
        """
        if not self.session:
            raise RuntimeError("Not connected to server")

        result = await self.session.call_tool(tool_name, arguments)
        return result

    async def disconnect(self) -> None:
        """Disconnect from the server."""
        if self.session:
            # Cleanup would go here
            self.session = None


class MCPClientManager:
    """
    Manager for multiple MCP client connections.
    
    Handles:
    - Connecting to multiple MCP servers
    - Tool discovery across servers
    - Routing tool calls to appropriate servers
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize MCP client manager.

        Args:
            config_path: Path to MCP servers configuration file
        """
        self.config_path = config_path
        self.clients: Dict[str, MCPClient] = {}
        self.tool_registry: Dict[str, str] = {}  # tool_name -> server_name

    async def load_config(self, config_path: str) -> None:
        """Load server configurations from file."""
        with open(config_path, "r") as f:
            config = json.load(f)
        
        servers = config.get("servers", {})
        for server_name, server_config in servers.items():
            await self.add_server(server_name, server_config)

    async def add_server(self, name: str, config: Dict[str, Any]) -> bool:
        """
        Add and connect to a new MCP server.

        Args:
            name: Server name
            config: Server configuration

        Returns:
            True if connection successful
        """
        client = MCPClient(name, config)
        success = await client.connect()
        
        if success:
            self.clients[name] = client
            
            # Register tools from this server
            tools = await client.list_tools()
            for tool in tools:
                tool_name = f"{name}.{tool['name']}"
                self.tool_registry[tool_name] = name
            
            return True
        
        return False

    async def list_all_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        List all tools from all connected servers.

        Returns:
            Dictionary of server_name -> tools
        """
        all_tools = {}
        for server_name, client in self.clients.items():
            tools = await client.list_tools()
            all_tools[server_name] = tools
        
        return all_tools

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Any:
        """
        Call a tool on a specific server.

        Args:
            server_name: Name of the server
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Tool result
        """
        if server_name not in self.clients:
            raise ValueError(f"Server '{server_name}' not connected")

        client = self.clients[server_name]
        return await client.call_tool(tool_name, arguments)

    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        for client in self.clients.values():
            await client.disconnect()
        
        self.clients.clear()
        self.tool_registry.clear()


# Example usage
async def example_usage():
    """Example of using MCP client."""
    # Create manager
    manager = MCPClientManager()
    
    # Connect to filesystem server
    filesystem_config = {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    }
    await manager.add_server("filesystem", filesystem_config)
    
    # List all available tools
    all_tools = await manager.list_all_tools()
    print("Available tools:", json.dumps(all_tools, indent=2))
    
    # Call a tool
    result = await manager.call_tool(
        "filesystem",
        "read_file",
        {"path": "example.txt"}
    )
    print("Result:", result)
    
    # Cleanup
    await manager.disconnect_all()


if __name__ == "__main__":
    asyncio.run(example_usage())
