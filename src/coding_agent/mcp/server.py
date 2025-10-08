"""
MCP Server implementation - exposes coding-agent tools to MCP clients.

Following TDD approach with Safe Mode defaults.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List
import logging

from coding_agent.tools.file_manager import FileManager
from coding_agent.llm.ollama_client import OllamaClient
from coding_agent.storage.history import HistoryManager

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server that exposes coding-agent capabilities as MCP tools."""

    def __init__(
        self,
        workspace_path: str,
        enable_file_tools: bool = True,
        enable_ai_tools: bool = True,
        enable_history_tools: bool = False,
        ollama_host: str = "http://localhost:11434",
        ollama_model: str = "codellama:latest",
    ):
        """Initialize MCP server."""
        workspace = Path(workspace_path)
        if not workspace.exists():
            raise ValueError(f"Workspace path does not exist: {workspace_path}")
        
        self.workspace_path = str(workspace.resolve())
        self.enable_file_tools = enable_file_tools
        self.enable_ai_tools = enable_ai_tools
        self.enable_history_tools = enable_history_tools

        self.file_manager = FileManager(self.workspace_path) if enable_file_tools else None
        self.ollama_client = OllamaClient(host=ollama_host, model=ollama_model) if enable_ai_tools else None
        self.history_manager = HistoryManager() if enable_history_tools else None

        self._tools: Dict[str, Dict[str, Any]] = {}
        self._register_tools()

    @classmethod
    def with_safe_mode(cls, workspace_path: str, **kwargs) -> "MCPServer":
        """Create MCP server with Safe Mode defaults."""
        return cls(
            workspace_path=workspace_path,
            enable_file_tools=True,
            enable_ai_tools=True,
            enable_history_tools=False,
            **kwargs
        )

    def _register_tools(self) -> None:
        """Register all tools based on configuration."""
        if self.enable_file_tools:
            self._register_read_file_tool()
            self._register_list_files_tool()
        
        if self.enable_ai_tools:
            self._register_explain_code_tool()
        
        if self.enable_history_tools:
            self._register_search_history_tool()

    def _register_read_file_tool(self) -> None:
        """Register read_file tool."""
        self._tools["read_file"] = {
            "name": "read_file",
            "description": "Read contents of a file from the workspace",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to file in workspace"},
                    "start_line": {"type": "integer", "description": "Optional start line (1-indexed)"},
                    "end_line": {"type": "integer", "description": "Optional end line (inclusive)"},
                },
                "required": ["path"],
            },
        }

    def _register_list_files_tool(self) -> None:
        """Register list_files tool."""
        self._tools["list_files"] = {
            "name": "list_files",
            "description": "List files in the workspace",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Optional glob pattern (e.g., '*.py')"},
                    "include_hidden": {"type": "boolean", "description": "Include hidden files", "default": False},
                },
                "required": [],
            },
        }

    def _register_explain_code_tool(self) -> None:
        """Register explain_code tool."""
        self._tools["explain_code"] = {
            "name": "explain_code",
            "description": "Explain what a code snippet does",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to explain"},
                    "language": {"type": "string", "description": "Programming language"},
                },
                "required": ["code"],
            },
        }

    def _register_search_history_tool(self) -> None:
        """Register search_history tool."""
        self._tools["search_history"] = {
            "name": "search_history",
            "description": "Search conversation history",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Maximum results", "default": 10},
                },
                "required": ["query"],
            },
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools."""
        return list(self._tools.values())

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool by name with given arguments."""
        if name not in self._tools:
            return {"success": False, "error": f"Tool '{name}' not found"}
        
        try:
            if name == "read_file":
                return await self._handle_read_file(arguments)
            elif name == "list_files":
                return await self._handle_list_files(arguments)
            elif name == "explain_code":
                return await self._handle_explain_code(arguments)
            elif name == "search_history":
                return await self._handle_search_history(arguments)
            else:
                return {"success": False, "error": f"Handler not implemented for '{name}'"}
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}")
            return {"success": False, "error": str(e)}

    async def _handle_read_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle read_file tool call."""
        try:
            path = args.get("path")
            if not path:
                return {"success": False, "error": "Missing required parameter: path"}
            
            # Use FileManager which already has security checks
            success, content = self.file_manager.read_file(path)
            
            if not success:
                return {"success": False, "error": content}
            
            # Handle line range if specified
            start_line = args.get("start_line")
            end_line = args.get("end_line")
            
            if start_line is not None or end_line is not None:
                lines = content.splitlines()
                start_idx = (start_line - 1) if start_line else 0
                end_idx = end_line if end_line else len(lines)
                content = "\n".join(lines[start_idx:end_idx])
            
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_list_files(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list_files tool call."""
        try:
            directory = args.get("directory", ".")
            include_hidden = args.get("include_hidden", False)
            
            # Use FileManager which already has security checks
            success, result = self.file_manager.list_files(
                directory=directory,
                include_hidden=include_hidden
            )
            
            if not success:
                return {"success": False, "error": result}
            
            # Apply pattern filtering if specified
            pattern = args.get("pattern")
            if pattern and pattern != "*":
                import fnmatch
                result = [f for f in result if fnmatch.fnmatch(f, pattern)]
            
            return {"success": True, "files": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_explain_code(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle explain_code tool call."""
        try:
            code = args.get("code")
            if not code:
                return {"success": False, "error": "Missing required parameter: code"}
            
            language = args.get("language", "")
            prompt = f"Please explain what this {language} code does:\\n\\n```{language}\\n{code}\\n```"
            
            explanation = await asyncio.to_thread(self.ollama_client.generate, prompt)
            return {"success": True, "explanation": explanation}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_search_history(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search_history tool call."""
        try:
            query = args.get("query")
            if not query:
                return {"success": False, "error": "Missing required parameter: query"}
            
            limit = args.get("limit", 10)
            results = self.history_manager.search_sessions(query, limit=limit)
            return {"success": True, "results": results}
        except Exception as e:
            return {"success": False, "error": str(e)}
