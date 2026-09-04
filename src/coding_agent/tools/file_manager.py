"""File manager for workspace file operations."""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pathspec
from rich.console import Console

console = Console()

# Patterns that are always blocked, regardless of confirmation, because they
# are almost never intentional in a coding-assistant workflow and can cause
# irreversible damage to the machine (not just the workspace).
_DANGEROUS_COMMAND_PATTERNS = [
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+/(\s|$)",  # rm -rf /
    r"rm\s+-[a-z]*f[a-z]*r[a-z]*\s+/(\s|$)",  # rm -fr /
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+~",  # rm -rf ~
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",  # classic fork bomb
    r"\bmkfs(\.\w+)?\b",
    r"\bdd\b.*\bof=/dev/",
    r">\s*/dev/sd[a-z]",
    r"\bsudo\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r":>\s*/",  # truncating arbitrary root-level files
]


class FileManager:
    """Handles file operations within a workspace."""

    def __init__(self, workspace_path: str) -> None:
        """
        Initialize FileManager.

        Args:
            workspace_path: Root path of the workspace
        """
        self.workspace = Path(workspace_path).resolve()
        self.gitignore_spec = self._load_gitignore()

    def _load_gitignore(self) -> Optional[pathspec.PathSpec]:
        """
        Load .gitignore patterns if present.

        Returns:
            PathSpec object or None if no .gitignore
        """
        gitignore_path = self.workspace / ".gitignore"
        if gitignore_path.exists():
            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    patterns = f.read().splitlines()
                return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load .gitignore: {e}[/yellow]")
        return None

    def _is_ignored(self, path: Path) -> bool:
        """
        Check if path should be ignored based on .gitignore.

        Args:
            path: Path to check

        Returns:
            True if path should be ignored
        """
        if self.gitignore_spec is None:
            return False

        try:
            # Get relative path from workspace root
            rel_path = path.relative_to(self.workspace)
            return self.gitignore_spec.match_file(str(rel_path))
        except ValueError:
            # Path is outside workspace
            return True

    def _is_safe_path(self, path: Path) -> bool:
        """
        Check if path is within workspace.

        Args:
            path: Path to check

        Returns:
            True if path is safe to access
        """
        try:
            resolved = path.resolve()
            resolved.relative_to(self.workspace)
            return True
        except (ValueError, RuntimeError):
            return False

    def read_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Read contents of a file.

        Args:
            file_path: Relative or absolute path to file

        Returns:
            Tuple of (success, content or error message)
        """
        try:
            # Convert to Path and resolve
            path = Path(file_path)
            if not path.is_absolute():
                path = self.workspace / path
            path = path.resolve()

            # Security check
            if not self._is_safe_path(path):
                return False, f"Error: Path '{file_path}' is outside workspace"

            # Check if ignored
            if self._is_ignored(path):
                return False, f"Error: Path '{file_path}' is ignored by .gitignore"

            # Check if exists
            if not path.exists():
                return False, f"Error: File '{file_path}' does not exist"

            if not path.is_file():
                return False, f"Error: '{file_path}' is not a file"

            # Read file
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            return True, content

        except UnicodeDecodeError:
            return False, f"Error: File '{file_path}' is not a text file (binary content)"
        except PermissionError:
            return False, f"Error: Permission denied reading '{file_path}'"
        except Exception as e:
            return False, f"Error reading file: {str(e)}"

    def write_file(self, file_path: str, content: str, overwrite: bool = False) -> Tuple[bool, str]:
        """
        Write content to a file.

        Args:
            file_path: Relative or absolute path to file
            content: Content to write
            overwrite: Whether to overwrite existing file

        Returns:
            Tuple of (success, message)
        """
        try:
            # Convert to Path and resolve
            path = Path(file_path)
            if not path.is_absolute():
                path = self.workspace / path

            # Security check (before resolving, as file might not exist yet)
            if not self._is_safe_path(path):
                return False, f"Error: Path '{file_path}' is outside workspace"

            # Check if file exists and overwrite is False
            if path.exists() and not overwrite:
                return False, f"Error: File '{file_path}' already exists (use overwrite=True to replace)"

            # Check if ignored
            if self._is_ignored(path):
                return False, f"Error: Path '{file_path}' is ignored by .gitignore"

            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            action = "overwritten" if path.exists() and overwrite else "created"
            return True, f"Successfully {action} '{file_path}'"

        except PermissionError:
            return False, f"Error: Permission denied writing to '{file_path}'"
        except Exception as e:
            return False, f"Error writing file: {str(e)}"

    def edit_file(self, file_path: str, old_text: str, new_text: str) -> Tuple[bool, str]:
        """
        Edit a file by replacing text.

        Args:
            file_path: Relative or absolute path to file
            old_text: Text to find and replace
            new_text: Replacement text

        Returns:
            Tuple of (success, message)
        """
        # First, read the file
        success, content = self.read_file(file_path)
        if not success:
            return False, content

        # Check if old_text exists
        if old_text not in content:
            return False, f"Error: Text to replace not found in '{file_path}'"

        # Replace the text
        new_content = content.replace(old_text, new_text)

        # Count replacements
        count = content.count(old_text)

        # Write back
        success, message = self.write_file(file_path, new_content, overwrite=True)
        if success:
            return True, f"Successfully replaced {count} occurrence(s) in '{file_path}'"

        return False, message

    def list_files(
        self,
        directory: str = ".",
        max_depth: int = 3,
        include_hidden: bool = False
    ) -> Tuple[bool, Union[List[str], str]]:
        """
        List files in a directory recursively.

        Args:
            directory: Directory to list (relative to workspace)
            max_depth: Maximum depth to traverse
            include_hidden: Whether to include hidden files

        Returns:
            Tuple of (success, list of file paths or error message)
        """
        try:
            # Convert to Path and resolve
            path = Path(directory)
            if not path.is_absolute():
                path = self.workspace / path
            path = path.resolve()

            # Security check
            if not self._is_safe_path(path):
                return False, f"Error: Path '{directory}' is outside workspace"

            # Check if exists
            if not path.exists():
                return False, f"Error: Directory '{directory}' does not exist"

            if not path.is_dir():
                return False, f"Error: '{directory}' is not a directory"

            # Collect files
            files = []

            def walk_directory(current_path: Path, current_depth: int):
                if current_depth > max_depth:
                    return

                try:
                    for item in sorted(current_path.iterdir()):
                        # Skip hidden files if not included
                        if not include_hidden and item.name.startswith("."):
                            continue

                        # Skip if ignored
                        if self._is_ignored(item):
                            continue

                        # Get relative path
                        try:
                            rel_path = item.relative_to(self.workspace)
                        except ValueError:
                            continue

                        if item.is_file():
                            files.append(str(rel_path))
                        elif item.is_dir():
                            walk_directory(item, current_depth + 1)

                except PermissionError:
                    console.print(f"[yellow]Warning: Permission denied for {current_path}[/yellow]")

            walk_directory(path, 0)
            return True, files

        except Exception as e:
            return False, f"Error listing directory: {str(e)}"

    def get_file_info(self, file_path: str) -> Tuple[bool, Union[Dict, str]]:
        """
        Get information about a file.

        Args:
            file_path: Path to file

        Returns:
            Tuple of (success, info dict or error message)
        """
        try:
            # Convert to Path and resolve
            path = Path(file_path)
            if not path.is_absolute():
                path = self.workspace / path
            path = path.resolve()

            # Security check
            if not self._is_safe_path(path):
                return False, f"Error: Path '{file_path}' is outside workspace"

            # Check if exists
            if not path.exists():
                return False, f"Error: File '{file_path}' does not exist"

            # Get stats
            stat = path.stat()

            info = {
                "name": path.name,
                "path": str(path.relative_to(self.workspace)),
                "absolute_path": str(path),
                "size": stat.st_size,
                "size_human": self._format_size(stat.st_size),
                "modified": stat.st_mtime,
                "is_file": path.is_file(),
                "is_directory": path.is_dir(),
                "extension": path.suffix,
            }

            return True, info

        except Exception as e:
            return False, f"Error getting file info: {str(e)}"

    @staticmethod
    def _format_size(size: int) -> str:
        """
        Format file size in human-readable format.

        Args:
            size: Size in bytes

        Returns:
            Formatted size string
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists.

        Args:
            file_path: Path to check

        Returns:
            True if file exists
        """
        try:
            path = Path(file_path)
            if not path.is_absolute():
                path = self.workspace / path
            path = path.resolve()

            return self._is_safe_path(path) and path.exists() and path.is_file()
        except Exception:
            return False

    def directory_exists(self, dir_path: str) -> bool:
        """
        Check if a directory exists.

        Args:
            dir_path: Path to check

        Returns:
            True if directory exists
        """
        try:
            path = Path(dir_path)
            if not path.is_absolute():
                path = self.workspace / path
            path = path.resolve()

            return self._is_safe_path(path) and path.exists() and path.is_dir()
        except Exception:
            return False

    @staticmethod
    def is_command_dangerous(command: str) -> bool:
        """
        Check whether a shell command matches a known-destructive pattern.

        This is a best-effort safety net (not a sandbox) that blocks the most
        common ways an agent could damage the host machine, e.g. `rm -rf /`,
        fork bombs, `sudo`, or writing directly to block devices.

        Args:
            command: Shell command to check

        Returns:
            True if the command matches a dangerous pattern and should be blocked
        """
        return any(
            re.search(pattern, command, re.IGNORECASE)
            for pattern in _DANGEROUS_COMMAND_PATTERNS
        )

    def run_command(self, command: str, timeout: int = 60) -> Tuple[bool, str]:
        """
        Run a shell command inside the workspace directory.

        This allows the agent to run things like test suites, linters, or
        build tools so it can verify its own changes. Commands run with the
        workspace directory as the current working directory. Known
        destructive commands are always blocked; callers (e.g. the agent's
        confirmation flow) are responsible for any additional user consent.

        Args:
            command: Shell command to execute
            timeout: Maximum number of seconds to allow the command to run

        Returns:
            Tuple of (success, combined stdout/stderr output or error message)
        """
        if not command or not command.strip():
            return False, "Command cannot be empty"

        if self.is_command_dangerous(command):
            return False, f"Command blocked for safety (matches a destructive pattern): {command}"

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            output = result.stdout or ""
            if result.stderr:
                output = f"{output}\n{result.stderr}" if output else result.stderr

            if result.returncode == 0:
                return True, output.strip() or "(command completed with no output)"

            return False, f"Command exited with code {result.returncode}:\n{output.strip()}"

        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds: {command}"
        except Exception as e:
            return False, f"Error running command: {str(e)}"
