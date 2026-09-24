"""Provider-agnostic JSON-schema tool/function definitions for the agent's
file and shell actions (issue #8, step 1: structured tool-calling).

These mirror the text-based commands documented in `coding_agent.llm.prompts`
(`READ_FILE`, `WRITE_FILE`, etc.) so that both code paths - structured
tool-calling (for providers that support it) and text-format regex parsing
(the fallback for providers/models that don't) - resolve to the exact same
set of operations/parameter names understood by
`CodingAgent._execute_file_operation`.

Each tool's `name` is the lowercase form of its corresponding operation
(e.g. "read_file" -> "READ_FILE"), and its parameter names match the keys
`_execute_file_operation` expects (`path`, `content`, `old_text`, `new_text`,
`command`, `pattern`), so converting a tool call back into an
`(operation, params)` pair is a simple `name.upper()` + pass-through.
"""

from typing import Any, Dict, List

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "read_file",
        "description": "Read the contents of a file in the workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file, relative to the workspace root.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "List files and directories in a directory of the workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the directory, relative to the workspace root "
                    "(use '.' for the workspace root).",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "search_files",
        "description": "Search for a text or regex pattern across files in the workspace "
        "(e.g. to find where something is defined or used).",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Text or regex pattern to search for.",
                }
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "run_command",
        "description": "Run a shell command in the workspace (e.g. tests, linters, builds). "
        "The user must approve the command before it runs.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                }
            },
            "required": ["command"],
        },
    },
    {
        "name": "write_file",
        "description": "Create a new file or overwrite an existing file with the given content.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file, relative to the workspace root.",
                },
                "content": {
                    "type": "string",
                    "description": "Full content to write to the file.",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace an exact block of existing text in a file with new text.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file, relative to the workspace root.",
                },
                "old_text": {
                    "type": "string",
                    "description": "The exact existing text to find and replace.",
                },
                "new_text": {
                    "type": "string",
                    "description": "The replacement text.",
                },
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
]


def operation_name_for_tool(tool_name: str) -> str:
    """
    Convert a tool/function name (e.g. "read_file") into the internal
    operation constant `_execute_file_operation` expects (e.g. "READ_FILE").

    Args:
        tool_name: Tool name as returned by the provider (e.g. "read_file")

    Returns:
        The corresponding internal operation name (e.g. "READ_FILE")
    """
    return tool_name.upper()
