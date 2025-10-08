"""Core agent logic for orchestrating LLM and file operations."""

import re
from typing import Dict, List, Optional, Tuple

from rich.console import Console

from coding_agent.llm.ollama_client import OllamaClient
from coding_agent.llm.prompts import get_system_prompt
from coding_agent.storage.history import HistoryManager
from coding_agent.tools.file_manager import FileManager
from coding_agent.utils.display import (
    print_agent_message,
    print_code_block,
    print_error_message,
    print_file_operation,
    print_file_operation_result,
    print_success_message,
    print_system_message,
    stream_agent_response,
)

console = Console()


class CodingAgent:
    """Main agent for handling user interactions and executing tasks."""

    def __init__(
        self,
        workspace_path: str,
        ollama_host: str = "http://localhost:11434",
        model: str = "codellama:latest",
        max_history: int = 50,
        enable_history: bool = True,
    ) -> None:
        """
        Initialize the coding agent.

        Args:
            workspace_path: Path to the workspace
            ollama_host: Ollama server host
            model: Model name to use
            max_history: Maximum number of messages to keep in history
            enable_history: Whether to enable history persistence
        """
        self.workspace_path = workspace_path
        self.model = model
        self.file_manager = FileManager(workspace_path)
        self.llm_client = OllamaClient(host=ollama_host, model=model)
        self.max_history = max_history
        self.conversation_history: List[Dict[str, str]] = []
        self.system_prompt = get_system_prompt(workspace_path)
        
        # History management
        self.enable_history = enable_history
        self.history_manager = HistoryManager() if enable_history else None
        self.session_id: Optional[str] = None
        
        # Start a new session if history is enabled
        if self.enable_history and self.history_manager:
            self.session_id = self.history_manager.create_session(
                workspace_path=workspace_path,
                model=model
            )

    def _add_to_history(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """
        Add a message to conversation history.

        Args:
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional metadata (e.g., file operations)
        """
        self.conversation_history.append({"role": role, "content": content})

        # Save to persistent storage if enabled
        if self.enable_history and self.history_manager and self.session_id:
            # Don't save system messages to persistent storage
            if role != "system":
                self.history_manager.add_message(
                    self.session_id,
                    role=role,
                    content=content,
                    metadata=metadata
                )

        # Trim history if too long (keep system prompt + recent messages)
        if len(self.conversation_history) > self.max_history:
            # Keep system message and recent messages
            system_messages = [msg for msg in self.conversation_history if msg["role"] == "system"]
            recent_messages = self.conversation_history[-self.max_history:]
            
            # Combine, removing duplicate system messages
            self.conversation_history = system_messages[:1] + [
                msg for msg in recent_messages if msg["role"] != "system"
            ]

    def _build_context(self) -> List[Dict[str, str]]:
        """
        Build context for LLM including system prompt and history.

        Returns:
            List of messages for LLM
        """
        context = [{"role": "system", "content": self.system_prompt}]
        
        # Add conversation history (excluding system messages as we already added one)
        context.extend([msg for msg in self.conversation_history if msg["role"] != "system"])
        
        return context

    def _parse_file_operations(self, response: str) -> List[Tuple[str, Dict[str, str]]]:
        """
        Parse agent response for file operation commands.

        Supported formats:
        - READ_FILE: path/to/file
        - WRITE_FILE: path/to/file
          CONTENT:
          ```
          file content here
          ```
        - EDIT_FILE: path/to/file
          OLD:
          ```
          old text
          ```
          NEW:
          ```
          new text
          ```
        - LIST_FILES: path/to/directory

        Args:
            response: Agent's response text

        Returns:
            List of (operation, params) tuples
        """
        operations = []

        # Pattern for READ_FILE
        read_pattern = r"READ_FILE:\s*([^\n]+)"
        for match in re.finditer(read_pattern, response, re.IGNORECASE):
            operations.append(("READ_FILE", {"path": match.group(1).strip()}))

        # Pattern for LIST_FILES
        list_pattern = r"LIST_FILES:\s*([^\n]+)"
        for match in re.finditer(list_pattern, response, re.IGNORECASE):
            operations.append(("LIST_FILES", {"path": match.group(1).strip()}))

        # Pattern for WRITE_FILE with content
        write_pattern = r"WRITE_FILE:\s*([^\n]+)[\s\n]+CONTENT:\s*```(?:\w+)?\s*(.*?)```"
        for match in re.finditer(write_pattern, response, re.IGNORECASE | re.DOTALL):
            operations.append(("WRITE_FILE", {
                "path": match.group(1).strip(),
                "content": match.group(2).strip()
            }))

        # Pattern for EDIT_FILE with old and new content
        edit_pattern = r"EDIT_FILE:\s*([^\n]+)[\s\n]+OLD:\s*```(?:\w+)?\s*(.*?)```[\s\n]+NEW:\s*```(?:\w+)?\s*(.*?)```"
        for match in re.finditer(edit_pattern, response, re.IGNORECASE | re.DOTALL):
            operations.append(("EDIT_FILE", {
                "path": match.group(1).strip(),
                "old_text": match.group(2).strip(),
                "new_text": match.group(3).strip()
            }))

        return operations

    def _execute_file_operation(self, operation: str, params: Dict[str, str]) -> Tuple[bool, str]:
        """
        Execute a file operation.

        Args:
            operation: Operation type (READ_FILE, WRITE_FILE, EDIT_FILE, LIST_FILES)
            params: Operation parameters

        Returns:
            Tuple of (success, result/error message)
        """
        try:
            if operation == "READ_FILE":
                path = params["path"]
                print_file_operation("Reading", path, "in_progress")
                success, content = self.file_manager.read_file(path)
                
                if success:
                    print_file_operation("Reading", path, "success")
                    # Add to context so agent knows the content
                    self._add_to_history(
                        "system",
                        f"File content of {path}:\n```\n{content}\n```"
                    )
                    return True, content
                else:
                    print_file_operation("Reading", path, "error")
                    return False, content

            elif operation == "WRITE_FILE":
                path = params["path"]
                content = params["content"]
                print_file_operation("Writing", path, "in_progress")
                
                # Check if file exists to determine overwrite
                overwrite = self.file_manager.file_exists(path)
                success, message = self.file_manager.write_file(path, content, overwrite=True)
                
                if success:
                    print_file_operation("Writing", path, "success")
                else:
                    print_file_operation("Writing", path, "error")
                
                return success, message

            elif operation == "EDIT_FILE":
                path = params["path"]
                old_text = params["old_text"]
                new_text = params["new_text"]
                print_file_operation("Editing", path, "in_progress")
                
                success, message = self.file_manager.edit_file(path, old_text, new_text)
                
                if success:
                    print_file_operation("Editing", path, "success")
                else:
                    print_file_operation("Editing", path, "error")
                
                return success, message

            elif operation == "LIST_FILES":
                path = params.get("path", ".")
                print_file_operation("Listing", path, "in_progress")
                
                success, files = self.file_manager.list_files(path, max_depth=2)
                
                if success:
                    print_file_operation("Listing", path, "success")
                    files_list = "\n".join(f"  - {f}" for f in files[:50])
                    if len(files) > 50:
                        files_list += f"\n  ... and {len(files) - 50} more files"
                    
                    result = f"Files in {path}:\n{files_list}"
                    # Add to context
                    self._add_to_history("system", result)
                    return True, result
                else:
                    print_file_operation("Listing", path, "error")
                    return False, files

            else:
                return False, f"Unknown operation: {operation}"

        except Exception as e:
            return False, f"Error executing {operation}: {str(e)}"

    def process_message(self, user_message: str, stream: bool = True) -> str:
        """
        Process a user message and return the agent's response.

        Args:
            user_message: User's input message
            stream: Whether to stream the response

        Returns:
            Agent's response
        """
        # Add user message to history
        self._add_to_history("user", user_message)

        # Build context
        context = self._build_context()

        try:
            # Get LLM response
            if stream:
                # Stream the response
                response_generator = self.llm_client.stream_generate(user_message, context[:-1])
                response = stream_agent_response(response_generator)
            else:
                # Non-streaming response
                response = self.llm_client.generate(user_message, context[:-1])
                print_agent_message(response)

            # Add agent response to history
            self._add_to_history("assistant", response)

            # Check for file operations in the response
            operations = self._parse_file_operations(response)

            if operations:
                console.print(f"\n[yellow]Detected {len(operations)} file operation(s)[/yellow]")
            else:
                # Debug: show response for debugging
                console.print(f"\n[dim]No file operations detected in response[/dim]")
                # Uncomment for debugging:
                # console.print(f"[dim]Response text:[/dim]\n{response[:200]}...")
            
            if operations:
                # Track if we need a follow-up response
                has_read_operation = False
                operation_results = []
                
                for operation, params in operations:
                    success, result = self._execute_file_operation(operation, params)
                    
                    # Show result
                    if operation == "READ_FILE" and success:
                        # Show file content with syntax highlighting
                        from coding_agent.utils.display import print_file_content
                        print_file_content(result, params["path"], max_lines=50)
                        has_read_operation = True
                        operation_results.append(f"File: {params['path']}\nContent:\n{result}")
                    elif operation == "LIST_FILES" and success:
                        print_system_message(result)
                        operation_results.append(result)
                    else:
                        print_file_operation_result(success, result, operation)
                    
                    # If operation failed, inform the agent
                    if not success:
                        error_context = f"The {operation} operation failed: {result}"
                        self._add_to_history("system", error_context)
                
                # If we read a file, ask LLM to provide explanation/answer
                if has_read_operation and operation_results:
                    console.print("\n[yellow]Generating explanation...[/yellow]\n")
                    
                    # Add operation results to history
                    for result in operation_results:
                        self._add_to_history("system", result)
                    
                    # Get follow-up response from LLM
                    follow_up_prompt = "Now that you have the file content, please answer the user's original question."
                    self._add_to_history("system", follow_up_prompt)
                    
                    context = self._build_context()
                    
                    if stream:
                        follow_up_generator = self.llm_client.stream_generate(follow_up_prompt, context[:-1])
                        follow_up_response = stream_agent_response(follow_up_generator)
                    else:
                        follow_up_response = self.llm_client.generate(follow_up_prompt, context[:-1])
                        print_agent_message(follow_up_response)
                    
                    self._add_to_history("assistant", follow_up_response)
                    return response + "\n\n" + follow_up_response

            return response

        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            print_error_message(error_msg)
            return error_msg

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()
        print_success_message("Conversation history cleared")

    def get_workspace_info(self) -> Dict[str, any]:
        """
        Get information about the current workspace.

        Returns:
            Dictionary with workspace information
        """
        success, files = self.file_manager.list_files(".", max_depth=2)
        
        return {
            "path": self.workspace_path,
            "file_count": len(files) if success else 0,
            "files": files if success else [],
        }

    def set_workspace(self, new_path: str) -> bool:
        """
        Change the workspace path.

        Args:
            new_path: New workspace path

        Returns:
            True if successful
        """
        try:
            self.workspace_path = new_path
            self.file_manager = FileManager(new_path)
            self.system_prompt = get_system_prompt(new_path)
            
            # Update system message in history
            if self.conversation_history and self.conversation_history[0]["role"] == "system":
                self.conversation_history[0]["content"] = self.system_prompt
            
            print_success_message(f"Workspace changed to: {new_path}")
            return True
        except Exception as e:
            print_error_message(f"Failed to change workspace: {str(e)}")
            return False
