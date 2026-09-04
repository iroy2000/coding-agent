"""Tests for CodingAgent's file-operation parsing and execution, focused on
the RUN_COMMAND capability (shell command execution tool)."""

import subprocess
from pathlib import Path

import pytest

from coding_agent.agent import CodingAgent


@pytest.fixture
def agent(temp_dir: Path) -> CodingAgent:
    """Create a CodingAgent rooted at a temp workspace, with history disabled
    so tests don't touch the real ~/.coding-agent directory, and command
    auto-approval disabled by default so each test controls confirmation."""
    return CodingAgent(
        workspace_path=str(temp_dir),
        enable_history=False,
    )


class TestParseRunCommand:
    def test_parses_single_run_command(self, agent: CodingAgent):
        response = "Sure, let's check:\nRUN_COMMAND: pytest -q\n"
        operations = agent._parse_file_operations(response)
        assert ("RUN_COMMAND", {"command": "pytest -q"}) in operations

    def test_parses_multiple_operations(self, agent: CodingAgent):
        response = "LIST_FILES: .\nRUN_COMMAND: npm test\n"
        operations = agent._parse_file_operations(response)
        assert ("LIST_FILES", {"path": "."}) in operations
        assert ("RUN_COMMAND", {"command": "npm test"}) in operations

    def test_case_insensitive(self, agent: CodingAgent):
        response = "run_command: echo hi\n"
        operations = agent._parse_file_operations(response)
        assert ("RUN_COMMAND", {"command": "echo hi"}) in operations

    def test_no_run_command_when_absent(self, agent: CodingAgent):
        response = "Just a normal explanation with no commands."
        operations = agent._parse_file_operations(response)
        assert operations == []


class TestExecuteRunCommand:
    def test_runs_when_auto_approved(self, agent: CodingAgent):
        agent.auto_approve_commands = True
        success, result = agent._execute_file_operation(
            "RUN_COMMAND", {"command": "echo hello-from-agent"}
        )
        assert success is True
        assert "hello-from-agent" in result

    def test_runs_when_confirmation_callback_approves(self, agent: CodingAgent):
        agent.confirm_command = lambda command: True
        success, result = agent._execute_file_operation(
            "RUN_COMMAND", {"command": "echo approved"}
        )
        assert success is True
        assert "approved" in result

    def test_blocked_when_confirmation_callback_denies(self, agent: CodingAgent):
        calls = []
        agent.confirm_command = lambda command: calls.append(command) or False

        success, result = agent._execute_file_operation(
            "RUN_COMMAND", {"command": "echo should-not-run"}
        )

        assert success is False
        assert "not approved" in result.lower()
        # The command must never have reached the shell.
        assert calls == ["echo should-not-run"]

    def test_confirmation_prompt_receives_the_command(self, agent: CodingAgent):
        seen = {}

        def fake_confirm(command: str) -> bool:
            seen["command"] = command
            return True

        agent.confirm_command = fake_confirm
        agent._execute_file_operation("RUN_COMMAND", {"command": "echo track-me"})
        assert seen["command"] == "echo track-me"

    def test_dangerous_command_blocked_even_when_auto_approved(self, agent: CodingAgent):
        agent.auto_approve_commands = True
        success, result = agent._execute_file_operation(
            "RUN_COMMAND", {"command": "rm -rf /"}
        )
        assert success is False
        assert "blocked" in result.lower()

    def test_failed_command_returns_error_output(self, agent: CodingAgent):
        agent.auto_approve_commands = True
        success, result = agent._execute_file_operation(
            "RUN_COMMAND", {"command": "exit 1"}
        )
        assert success is False
        assert "exited with code 1" in result


class TestWriteFileDiffPreview:
    def test_new_file_write_runs_when_auto_approved(self, agent: CodingAgent, temp_dir: Path):
        agent.auto_approve_writes = True
        success, message = agent._execute_file_operation(
            "WRITE_FILE", {"path": "new.py", "content": "print('hi')\n"}
        )
        assert success is True
        assert (temp_dir / "new.py").read_text() == "print('hi')\n"

    def test_write_blocked_when_confirmation_denies(self, agent: CodingAgent, temp_dir: Path):
        agent.confirm_write = lambda path, diff: False
        success, message = agent._execute_file_operation(
            "WRITE_FILE", {"path": "new.py", "content": "print('hi')\n"}
        )
        assert success is False
        assert "not approved" in message.lower()
        assert not (temp_dir / "new.py").exists()

    def test_write_applied_when_confirmation_approves(self, agent: CodingAgent, temp_dir: Path):
        agent.confirm_write = lambda path, diff: True
        success, message = agent._execute_file_operation(
            "WRITE_FILE", {"path": "new.py", "content": "print('hi')\n"}
        )
        assert success is True
        assert (temp_dir / "new.py").read_text() == "print('hi')\n"

    def test_confirmation_receives_diff_containing_new_lines(self, agent: CodingAgent):
        seen = {}

        def fake_confirm(path, diff_text):
            seen["path"] = path
            seen["diff"] = diff_text
            return True

        agent.confirm_write = fake_confirm
        agent._execute_file_operation(
            "WRITE_FILE", {"path": "new.py", "content": "print('hi')\n"}
        )
        assert seen["path"] == "new.py"
        assert "+print('hi')" in seen["diff"]

    def test_overwrite_existing_file_shows_diff_of_change(self, agent: CodingAgent, temp_dir: Path):
        (temp_dir / "existing.txt").write_text("old line\n")
        seen = {}

        def fake_confirm(path, diff_text):
            seen["diff"] = diff_text
            return True

        agent.confirm_write = fake_confirm
        success, _ = agent._execute_file_operation(
            "WRITE_FILE", {"path": "existing.txt", "content": "new line\n"}
        )
        assert success is True
        assert "-old line" in seen["diff"]
        assert "+new line" in seen["diff"]
        assert (temp_dir / "existing.txt").read_text() == "new line\n"

    def test_no_confirmation_when_content_unchanged(self, agent: CodingAgent, temp_dir: Path):
        (temp_dir / "same.txt").write_text("same content\n")
        agent.confirm_write = lambda path, diff: pytest.fail("should not be called")

        success, _ = agent._execute_file_operation(
            "WRITE_FILE", {"path": "same.txt", "content": "same content\n"}
        )
        assert success is True


class TestEditFileDiffPreview:
    def test_edit_blocked_when_confirmation_denies(self, agent: CodingAgent, temp_dir: Path):
        (temp_dir / "target.py").write_text("value = 1\n")
        agent.confirm_write = lambda path, diff: False

        success, message = agent._execute_file_operation(
            "EDIT_FILE", {"path": "target.py", "old_text": "value = 1", "new_text": "value = 2"}
        )

        assert success is False
        assert "not approved" in message.lower()
        assert (temp_dir / "target.py").read_text() == "value = 1\n"

    def test_edit_applied_when_confirmation_approves(self, agent: CodingAgent, temp_dir: Path):
        (temp_dir / "target.py").write_text("value = 1\n")
        agent.confirm_write = lambda path, diff: True

        success, message = agent._execute_file_operation(
            "EDIT_FILE", {"path": "target.py", "old_text": "value = 1", "new_text": "value = 2"}
        )

        assert success is True
        assert (temp_dir / "target.py").read_text() == "value = 2\n"

    def test_edit_auto_approved(self, agent: CodingAgent, temp_dir: Path):
        (temp_dir / "target.py").write_text("value = 1\n")
        agent.auto_approve_writes = True

        success, message = agent._execute_file_operation(
            "EDIT_FILE", {"path": "target.py", "old_text": "value = 1", "new_text": "value = 2"}
        )

        assert success is True
        assert (temp_dir / "target.py").read_text() == "value = 2\n"

    def test_edit_diff_shown_reflects_replacement(self, agent: CodingAgent, temp_dir: Path):
        (temp_dir / "target.py").write_text("value = 1\n")
        seen = {}

        def fake_confirm(path, diff_text):
            seen["diff"] = diff_text
            return True

        agent.confirm_write = fake_confirm
        agent._execute_file_operation(
            "EDIT_FILE", {"path": "target.py", "old_text": "value = 1", "new_text": "value = 2"}
        )
        assert "-value = 1" in seen["diff"]
        assert "+value = 2" in seen["diff"]

    def test_edit_with_missing_old_text_does_not_prompt(self, agent: CodingAgent, temp_dir: Path):
        (temp_dir / "target.py").write_text("value = 1\n")
        agent.confirm_write = lambda path, diff: pytest.fail("should not be called")

        success, message = agent._execute_file_operation(
            "EDIT_FILE", {"path": "target.py", "old_text": "not-there", "new_text": "value = 2"}
        )

        assert success is False
        assert "not found" in message.lower()


def _init_git_repo(path: Path) -> None:
    """Initialize a real git repo with an initial commit at the given path."""
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    (path / "README.md").write_text("# Test repo\n")
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial commit"], cwd=path, check=True)


class TestGitAutoCommitIntegration:
    def test_write_file_auto_commits_when_enabled(self, temp_dir: Path):
        _init_git_repo(temp_dir)
        agent = CodingAgent(workspace_path=str(temp_dir), enable_history=False)
        agent.auto_approve_writes = True
        agent.enable_git_auto_commit = True

        success, _ = agent._execute_file_operation(
            "WRITE_FILE", {"path": "new.py", "content": "print('hi')\n"}
        )

        assert success is True
        success, log_message = agent.git_manager.get_last_commit_message()
        assert success is True
        assert log_message == "[coding-agent] WRITE_FILE new.py"
        assert agent.git_manager.has_uncommitted_changes() is False

    def test_write_file_does_not_auto_commit_when_disabled(self, temp_dir: Path):
        _init_git_repo(temp_dir)
        agent = CodingAgent(workspace_path=str(temp_dir), enable_history=False)
        agent.auto_approve_writes = True
        assert agent.enable_git_auto_commit is False

        agent._execute_file_operation(
            "WRITE_FILE", {"path": "new.py", "content": "print('hi')\n"}
        )

        assert agent.git_manager.has_uncommitted_changes() is True

    def test_write_file_auto_commit_noop_outside_git_repo(self, agent: CodingAgent):
        agent.auto_approve_writes = True
        agent.enable_git_auto_commit = True

        success, _ = agent._execute_file_operation(
            "WRITE_FILE", {"path": "new.py", "content": "print('hi')\n"}
        )

        # Should still succeed writing the file; auto-commit silently no-ops.
        assert success is True

    def test_edit_file_auto_commits_when_enabled(self, temp_dir: Path):
        _init_git_repo(temp_dir)
        (temp_dir / "target.py").write_text("value = 1\n")
        subprocess.run(["git", "add", "-A"], cwd=temp_dir, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "add target"], cwd=temp_dir, check=True)

        agent = CodingAgent(workspace_path=str(temp_dir), enable_history=False)
        agent.auto_approve_writes = True
        agent.enable_git_auto_commit = True

        success, _ = agent._execute_file_operation(
            "EDIT_FILE", {"path": "target.py", "old_text": "value = 1", "new_text": "value = 2"}
        )

        assert success is True
        _, log_message = agent.git_manager.get_last_commit_message()
        assert log_message == "[coding-agent] EDIT_FILE target.py"
