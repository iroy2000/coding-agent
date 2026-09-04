"""Core agent logic for orchestrating LLM and file operations."""

import difflib
import re
from typing import Callable, Dict, List, Optional, Tuple

from rich.console import Console
from rich.prompt import Confirm
from rich.syntax import Syntax

from coding_agent.llm.ollama_client import OllamaClient
from coding_agent.llm.prompts import get_system_prompt
from coding_agent.storage.history import HistoryManager
from coding_agent.tools.file_manager import FileManager
from coding_agent.tools.git_manager import GitManager
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
        auto_approve_commands: bool = False,
        confirm_command: Optional[Callable[[str], bool]] = None,
        auto_approve_writes: bool = False,
        confirm_write: Optional[Callable[[str, str], bool]] = None,
        enable_git_auto_commit: bool = False,
    ) -> None:
        """
        Initialize the coding agent.

        Args:
            workspace_path: Path to the workspace
            ollama_host: Ollama server host
            model: Model name to use
            max_history: Maximum number of messages to keep in history
            enable_history: Whether to enable history persistence
            auto_approve_commands: If True, skip the confirmation prompt before
                running shell commands (e.g. for `--yes`/non-interactive/CI use)
            confirm_command: Optional callable that takes the command string and
                returns True/False to approve/deny it. Defaults to an interactive
                Rich confirmation prompt. Primarily used to inject a fake
                confirmation in tests.
            auto_approve_writes: If True, skip the diff-preview confirmation
                prompt before writing or editing files (e.g. for `--yes`/CI use)
            confirm_write: Optional callable that takes (path, unified_diff_text)
                and returns True/False to approve/deny applying the change.
                Defaults to an interactive Rich confirmation prompt showing the
                diff. Primarily used to inject a fake confirmation in tests.
            enable_git_auto_commit: If True (and the workspace is a git repo),
                automatically commit each successful WRITE_FILE/EDIT_FILE with
                a message tagged `[coding-agent] ...`, so changes can always be
                reviewed/undone via git. Opt-in, off by default.
        """
        self.workspace_path = workspace_path
        self.model = model
        self.file_manager = FileManager(workspace_path)
        self.git_manager = GitManager(workspace_path)
        self.llm_client = OllamaClient(host=ollama_host, model=model)
        self.max_history = max_history
        self.conversation_history: List[Dict[str, str]] = []
        self.system_prompt = get_system_prompt(workspace_path)
        self.auto_approve_commands = auto_approve_commands
        self.confirm_command = confirm_command or self._default_confirm_command
        self.auto_approve_writes = auto_approve_writes
        self.confirm_write = confirm_write or self._default_confirm_write
        self.enable_git_auto_commit = enable_git_auto_commit
        
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

    def _default_confirm_command(self, command: str) -> bool:
        """
        Default interactive confirmation prompt shown before running a shell command.

        Args:
            command: The shell command the agent wants to run

        Returns:
            True if the user approves running the command
        """
        console.print(f"\n[bold yellow]Agent wants to run a shell command:[/bold yellow] [cyan]{command}[/cyan]")
        return Confirm.ask("Allow this command to run?", default=False)

    def _build_diff(self, path: str, old_content: str, new_content: str) -> str:
        """
        Build a unified diff between old and new file content.

        Args:
            path: File path (used for the diff headers)
            old_content: Original file content (empty string for new files)
            new_content: Proposed new file content

        Returns:
            Unified diff text, or an empty string if there is no difference
        """
        if old_content == new_content:
            return ""

        diff_lines = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
        return "".join(diff_lines)

    def _default_confirm_write(self, path: str, diff_text: str) -> bool:
        """
        Default interactive confirmation prompt shown before writing/editing a file.

        Displays a unified diff of the proposed change and asks the user to
        approve it before it's applied to disk.

        Args:
            path: File path that would be written/edited
            diff_text: Unified diff text of the proposed change

        Returns:
            True if the user approves applying the change
        """
        console.print(f"\n[bold yellow]Agent wants to write changes to:[/bold yellow] [cyan]{path}[/cyan]")
        console.print(Syntax(diff_text, "diff", theme="monokai", line_numbers=False, word_wrap=True))
        return Confirm.ask(f"Apply these changes to {path}?", default=True)

    def _maybe_auto_commit(self, change_description: str) -> None:
        """
        Auto-commit the current workspace state if git auto-commit is enabled.

        Silently no-ops if auto-commit is disabled, the workspace isn't a git
        repository, or there's nothing to commit. Failures are surfaced as a
        system message so the user notices, but never raise/abort the turn.

        Args:
            change_description: Short description used as the commit message
                (e.g. "WRITE_FILE path/to/file.py")
        """
        if not self.enable_git_auto_commit:
            return

        success, message = self.git_manager.auto_commit(change_description)
        if success:
            if "no changes" not in message.lower():
                print_success_message(message)
        else:
            print_error_message(f"Git auto-commit failed: {message}")


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
        - RUN_COMMAND: shell command to execute

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

        # Pattern for RUN_COMMAND
        run_command_pattern = r"RUN_COMMAND:\s*([^\n]+)"
        for match in re.finditer(run_command_pattern, response, re.IGNORECASE):
            operations.append(("RUN_COMMAND", {"command": match.group(1).strip()}))

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
            operation: Operation type (READ_FILE, WRITE_FILE, EDIT_FILE, LIST_FILES, RUN_COMMAND)
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

                file_exists = self.file_manager.file_exists(path)
                _, existing_content = self.file_manager.read_file(path) if file_exists else (False, "")
                diff_text = self._build_diff(path, existing_content if file_exists else "", content)

                if diff_text and not self.auto_approve_writes:
                    if not self.confirm_write(path, diff_text):
                        message = f"Write to '{path}' was not approved by the user"
                        print_file_operation("Writing", path, "error")
                        return False, message

                print_file_operation("Writing", path, "in_progress")
                success, message = self.file_manager.write_file(path, content, overwrite=True)
                
                if success:
                    print_file_operation("Writing", path, "success")
                    self._maybe_auto_commit(f"WRITE_FILE {path}")
                else:
                    print_file_operation("Writing", path, "error")
                
                return success, message

            elif operation == "EDIT_FILE":
                path = params["path"]
                old_text = params["old_text"]
                new_text = params["new_text"]

                read_success, existing_content = self.file_manager.read_file(path)
                if read_success and old_text in existing_content:
                    new_content = existing_content.replace(old_text, new_text)
                    diff_text = self._build_diff(path, existing_content, new_content)

                    if diff_text and not self.auto_approve_writes:
                        if not self.confirm_write(path, diff_text):
                            message = f"Edit to '{path}' was not approved by the user"
                            print_file_operation("Editing", path, "error")
                            return False, message

                print_file_operation("Editing", path, "in_progress")
                success, message = self.file_manager.edit_file(path, old_text, new_text)
                
                if success:
                    print_file_operation("Editing", path, "success")
                    self._maybe_auto_commit(f"EDIT_FILE {path}")
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

            elif operation == "RUN_COMMAND":
                command = params["command"]

                if not self.auto_approve_commands and not self.confirm_command(command):
                    message = f"Command was not approved by the user: {command}"
                    print_file_operation("Running", command, "error")
                    return False, message

                print_file_operation("Running", command, "in_progress")
                success, output = self.file_manager.run_command(command)

                if success:
                    print_file_operation("Running", command, "success")
                    result = f"Output of `{command}`:\n{output}"
                    self._add_to_history("system", result)
                    return True, result
                else:
                    print_file_operation("Running", command, "error")
                    return False, output

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
                    elif operation == "RUN_COMMAND" and success:
                        print_system_message(result)
                        has_read_operation = True
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
            self.git_manager = GitManager(new_path)
            self.system_prompt = get_system_prompt(new_path)
            
            # Update system message in history
            if self.conversation_history and self.conversation_history[0]["role"] == "system":
                self.conversation_history[0]["content"] = self.system_prompt
            
            print_success_message(f"Workspace changed to: {new_path}")
            return True
        except Exception as e:
            print_error_message(f"Failed to change workspace: {str(e)}")
            return False
