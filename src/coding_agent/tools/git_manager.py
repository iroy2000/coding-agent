"""Git integration for auto-committing agent changes and undoing them safely."""

import subprocess
from pathlib import Path
from typing import Tuple

# Prefix used to tag every commit the agent creates on its own, so that
# `undo_last_agent_commit` can verify it's only ever reverting a commit the
# agent itself made (never a commit a human authored).
AGENT_COMMIT_PREFIX = "[coding-agent] "


class GitManager:
    """Handles git operations (auto-commit, undo) scoped to a workspace."""

    def __init__(self, workspace_path: str) -> None:
        """
        Initialize GitManager.

        Args:
            workspace_path: Root path of the workspace
        """
        self.workspace = Path(workspace_path).resolve()

    def _run_git(self, args: list, timeout: int = 30) -> Tuple[bool, str]:
        """
        Run a git command in the workspace directory.

        Args:
            args: Argument list to pass to `git` (without the leading "git")
            timeout: Maximum number of seconds to allow the command to run

        Returns:
            Tuple of (success, combined stdout/stderr output)
        """
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = (result.stdout or "") + (result.stderr or "")
            return result.returncode == 0, output.strip()
        except FileNotFoundError:
            return False, "git is not installed or not available on PATH"
        except subprocess.TimeoutExpired:
            return False, f"git {' '.join(args)} timed out after {timeout} seconds"
        except Exception as e:
            return False, f"Error running git: {str(e)}"

    def is_repo(self) -> bool:
        """
        Check whether the workspace is inside a git repository.

        Returns:
            True if the workspace is inside a git working tree
        """
        success, output = self._run_git(["rev-parse", "--is-inside-work-tree"])
        return success and output.strip() == "true"

    def has_uncommitted_changes(self) -> bool:
        """
        Check whether the workspace has any uncommitted changes.

        Returns:
            True if `git status --porcelain` reports any changes
        """
        success, output = self._run_git(["status", "--porcelain"])
        return success and bool(output.strip())

    def auto_commit(self, message: str) -> Tuple[bool, str]:
        """
        Stage all changes and create a commit tagged as an agent commit.

        No-ops (returns success) if there are no changes to commit, so callers
        don't need to special-case that.

        Args:
            message: Short description of what changed (e.g. "WRITE_FILE foo.py")

        Returns:
            Tuple of (success, result message)
        """
        if not self.is_repo():
            return False, "Not a git repository"

        if not self.has_uncommitted_changes():
            return True, "No changes to commit"

        success, output = self._run_git(["add", "-A"])
        if not success:
            return False, f"Failed to stage changes: {output}"

        commit_message = f"{AGENT_COMMIT_PREFIX}{message}"
        success, output = self._run_git(["commit", "-m", commit_message])
        if not success:
            return False, f"Failed to commit changes: {output}"

        return True, f"Committed: {commit_message}"

    def get_last_commit_message(self) -> Tuple[bool, str]:
        """
        Get the subject line of the most recent commit.

        Returns:
            Tuple of (success, commit message or error message)
        """
        return self._run_git(["log", "-1", "--pretty=%s"])

    def undo_last_agent_commit(self) -> Tuple[bool, str]:
        """
        Revert the most recent commit, but only if the agent made it.

        Uses `git revert` (not `reset --hard`) so the undo itself is a new
        commit and no history is destroyed or force-pushed.

        Returns:
            Tuple of (success, result message)
        """
        if not self.is_repo():
            return False, "Not a git repository"

        success, message = self.get_last_commit_message()
        if not success:
            return False, f"Could not read last commit: {message}"

        if not message.startswith(AGENT_COMMIT_PREFIX):
            return False, (
                "The last commit was not made by coding-agent "
                f"(commit message: '{message}'); refusing to undo it automatically"
            )

        success, output = self._run_git(["revert", "--no-edit", "HEAD"])
        if not success:
            return False, f"Failed to revert last agent commit: {output}"

        return True, f"Reverted last agent commit ('{message}')"
