"""
MCP stdio server implementation using official MCP SDK.

This module provides the stdio transport layer for the MCP server,
enabling communication with Claude Desktop and other MCP clients.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from coding_agent.tools.file_manager import FileManager
from coding_agent.llm.ollama_client import OllamaClient
from coding_agent.storage.history import HistoryManager

logger = logging.getLogger(__name__)


class MCPStdioServer:
    """
    MCP Server with stdio transport for Claude Desktop integration.
    
    This server exposes coding-agent tools via the Model Context Protocol
    using stdin/stdout for communication with MCP clients.
    """
    
    def __init__(
        self,
        workspace_path: str,
        enable_file_tools: bool = True,
        enable_ai_tools: bool = True,
        enable_history_tools: bool = False,
        ollama_host: str = "http://localhost:11434",
        ollama_model: str = "codellama:latest",
    ):
        """Initialize MCP stdio server."""
        self.workspace_path = workspace_path
        self.enable_file_tools = enable_file_tools
        self.enable_ai_tools = enable_ai_tools
        self.enable_history_tools = enable_history_tools
        
        # Initialize service components
        self.file_manager = FileManager(workspace_path) if enable_file_tools else None
        self.ollama_client = OllamaClient(host=ollama_host, model=ollama_model) if enable_ai_tools else None
        self.history_manager = HistoryManager() if enable_history_tools else None
        
        # Create MCP server instance
        self.server = Server(
            name="coding-agent",
            version="1.0.0",
            instructions="AI-powered coding assistant with file operations and code understanding"
        )
        
        # Register tool handlers
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """Register MCP tool handlers."""
        
        # List tools handler
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools."""
            tools = []
            
            if self.enable_file_tools:
                # read_file tool
                tools.append(Tool(
                    name="read_file",
                    description="Read contents of a file from the workspace. Supports reading full file or specific line ranges.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Relative or absolute path to the file within workspace"
                            },
                            "start_line": {
                                "type": "integer",
                                "description": "Optional: Starting line number (1-indexed)",
                                "minimum": 1
                            },
                            "end_line": {
                                "type": "integer",
                                "description": "Optional: Ending line number (inclusive)",
                                "minimum": 1
                            }
                        },
                        "required": ["file_path"]
                    }
                ))
                
                # list_files tool
                tools.append(Tool(
                    name="list_files",
                    description="List files in the workspace directory. Supports pattern filtering.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Optional: Filter pattern (e.g., '*.py', 'test_*.js')"
                            },
                            "include_hidden": {
                                "type": "boolean",
                                "description": "Optional: Include hidden files (default: false)",
                                "default": False
                            }
                        },
                        "required": []
                    }
                ))
            
            if self.enable_ai_tools:
                # explain_code tool
                tools.append(Tool(
                    name="explain_code",
                    description="Explain what a code snippet does. Uses local Ollama LLM for analysis.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Code snippet to explain"
                            },
                            "language": {
                                "type": "string",
                                "description": "Optional: Programming language (e.g., 'python', 'javascript')"
                            }
                        },
                        "required": ["code"]
                    }
                ))
            
            if self.enable_history_tools:
                # search_history tool
                tools.append(Tool(
                    name="search_history",
                    description="Search conversation history for past interactions.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query string"
                            },
                            "session_id": {
                                "type": "string",
                                "description": "Optional: Specific session ID to search within"
                            }
                        },
                        "required": ["query"]
                    }
                ))
            
            return tools
        
        # Call tool handler
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Execute a tool by name."""
            logger.info(f"Tool called: {name} with arguments: {arguments}")
            
            try:
                if name == "read_file":
                    return await self._handle_read_file(**arguments)
                elif name == "list_files":
                    return await self._handle_list_files(**arguments)
                elif name == "explain_code":
                    return await self._handle_explain_code(**arguments)
                elif name == "search_history":
                    return await self._handle_search_history(**arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"Tool execution error: {e}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=f"Error executing tool: {str(e)}"
                )]
    
    async def _handle_read_file(
        self,
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None
    ) -> List[TextContent]:
        """Handle read_file tool execution."""
        if not self.file_manager:
            return [TextContent(type="text", text="Error: File tools not enabled")]
        
        # Read file
        success, content = self.file_manager.read_file(file_path)
        
        if not success:
            return [TextContent(type="text", text=f"Error: {content}")]
        
        # Handle line range if specified
        if start_line is not None or end_line is not None:
            lines = content.splitlines()
            total_lines = len(lines)
            
            start_idx = (start_line - 1) if start_line else 0
            end_idx = end_line if end_line else total_lines
            
            # Validate ranges
            if start_idx < 0 or start_idx >= total_lines:
                return [TextContent(
                    type="text",
                    text=f"Error: start_line {start_line} out of range (file has {total_lines} lines)"
                )]
            
            if end_idx < start_idx or end_idx > total_lines:
                return [TextContent(
                    type="text",
                    text=f"Error: end_line {end_line} out of range (file has {total_lines} lines)"
                )]
            
            selected_lines = lines[start_idx:end_idx]
            content = "\n".join(selected_lines)
            
            result_text = f"File: {file_path}\nLines {start_line}-{end_line} of {total_lines}:\n\n{content}"
        else:
            result_text = f"File: {file_path}\n\n{content}"
        
        return [TextContent(type="text", text=result_text)]
    
    async def _handle_list_files(
        self,
        pattern: Optional[str] = None,
        include_hidden: bool = False
    ) -> List[TextContent]:
        """Handle list_files tool execution."""
        if not self.file_manager:
            return [TextContent(type="text", text="Error: File tools not enabled")]
        
        # List files (FileManager.list_files uses 'directory' parameter, not 'path')
        success, files = self.file_manager.list_files(
            directory=".",
            max_depth=5,
            include_hidden=include_hidden
        )
        
        if not success:
            return [TextContent(type="text", text=f"Error: {files}")]
        
        # Apply pattern filtering if provided
        if pattern:
            from fnmatch import fnmatch
            files = [f for f in files if fnmatch(f, pattern) or fnmatch(f.split('/')[-1], pattern)]
        
        # Filter hidden files if requested
        if not include_hidden:
            files = [f for f in files if not any(part.startswith('.') for part in f.split('/'))]
        
        # Format result
        if not files:
            result_text = f"No files found matching pattern: {pattern}" if pattern else "No files found"
        else:
            file_list = "\n".join(f"  - {f}" for f in sorted(files))
            pattern_info = f" matching '{pattern}'" if pattern else ""
            result_text = f"Found {len(files)} files{pattern_info}:\n\n{file_list}"
        
        return [TextContent(type="text", text=result_text)]
    
    async def _handle_explain_code(
        self,
        code: str,
        language: Optional[str] = None
    ) -> List[TextContent]:
        """Handle explain_code tool execution."""
        if not self.ollama_client:
            return [TextContent(type="text", text="Error: AI tools not enabled")]
        
        # Build prompt - keep it concise for faster response
        lang_info = f" ({language})" if language else ""
        prompt = f"Explain what this code{lang_info} does in 2-3 sentences:\n\n```\n{code}\n```"
        
        try:
            # Run synchronous Ollama call in thread pool with timeout
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Set timeout to 25 seconds (MCP Inspector default is 30s)
            explanation = await asyncio.wait_for(
                loop.run_in_executor(
                    None,  # Use default executor
                    self.ollama_client.generate,
                    prompt
                ),
                timeout=25.0
            )
            
            if not explanation:
                return [TextContent(
                    type="text",
                    text="Error: Ollama returned empty response. Check if Ollama is running and a model is available."
                )]
            
            result_text = f"Code Explanation:\n\n{explanation}"
            
            return [TextContent(type="text", text=result_text)]
        except asyncio.TimeoutError:
            return [TextContent(
                type="text",
                text="Error: Explanation timed out after 25 seconds. The code might be too complex or Ollama might be slow. Try a simpler code snippet."
            )]
        except Exception as e:
            return [TextContent(type="text", text=f"Error generating explanation: {str(e)}")]
    
    async def _handle_search_history(
        self,
        query: str,
        session_id: Optional[str] = None
    ) -> List[TextContent]:
        """Handle search_history tool execution."""
        if not self.history_manager:
            return [TextContent(type="text", text="Error: History tools not enabled")]
        
        try:
            # Search history
            results = self.history_manager.search_messages(query, session_id=session_id)
            
            if not results:
                result_text = f"No results found for query: {query}"
            else:
                # Format results
                formatted_results = []
                for i, result in enumerate(results[:10], 1):  # Limit to 10 results
                    session = result.get("session_id", "unknown")
                    role = result.get("role", "unknown")
                    content = result.get("content", "")[:200]  # Truncate
                    formatted_results.append(f"{i}. [{session}] {role}: {content}...")
                
                result_text = f"Found {len(results)} results (showing top 10):\n\n" + "\n\n".join(formatted_results)
            
            return [TextContent(type="text", text=result_text)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error searching history: {str(e)}")]
    
    async def run(self) -> None:
        """Run the MCP server with stdio transport."""
        logger.info(f"Starting MCP stdio server for workspace: {self.workspace_path}")
        
        async with stdio_server() as (read_stream, write_stream):
            logger.info("stdio server started, running MCP server...")
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )
    
    @classmethod
    def with_safe_mode(cls, workspace_path: str, **kwargs) -> "MCPStdioServer":
        """Create MCP server with Safe Mode defaults."""
        return cls(
            workspace_path=workspace_path,
            enable_file_tools=True,
            enable_ai_tools=True,
            enable_history_tools=False,
            **kwargs
        )


async def run_stdio_server(
    workspace_path: str,
    safe_mode: bool = True,
    **kwargs
) -> None:
    """
    Run MCP stdio server.
    
    Args:
        workspace_path: Path to workspace directory
        safe_mode: Use Safe Mode defaults (read-only operations)
        **kwargs: Additional configuration options
    """
    if safe_mode:
        server = MCPStdioServer.with_safe_mode(workspace_path, **kwargs)
    else:
        server = MCPStdioServer(workspace_path, **kwargs)
    
    await server.run()
