"""Tests for GitManager (auto-commit + safe undo of agent changes)."""

import subprocess
from pathlib import Path

import pytest

from coding_agent.tools.git_manager import AGENT_COMMIT_PREFIX, GitManager


def _run(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


@pytest.fixture
def git_repo(temp_dir: Path) -> Path:
    """Create a real git repository in a temp directory with an initial commit."""
    _run(["init", "-q"], cwd=temp_dir)
    _run(["config", "user.email", "test@example.com"], cwd=temp_dir)
    _run(["config", "user.name", "Test User"], cwd=temp_dir)
    (temp_dir / "README.md").write_text("# Test repo\n")
    _run(["add", "-A"], cwd=temp_dir)
    _run(["commit", "-m", "initial commit"], cwd=temp_dir)
    return temp_dir


class TestIsRepo:
    def test_true_for_git_repo(self, git_repo: Path):
        gm = GitManager(str(git_repo))
        assert gm.is_repo() is True

    def test_false_for_non_git_dir(self, temp_dir: Path):
        gm = GitManager(str(temp_dir))
        assert gm.is_repo() is False


class TestHasUncommittedChanges:
    def test_false_when_clean(self, git_repo: Path):
        gm = GitManager(str(git_repo))
        assert gm.has_uncommitted_changes() is False

    def test_true_after_editing_a_file(self, git_repo: Path):
        (git_repo / "README.md").write_text("# Changed\n")
        gm = GitManager(str(git_repo))
        assert gm.has_uncommitted_changes() is True

    def test_true_for_new_untracked_file(self, git_repo: Path):
        (git_repo / "new.txt").write_text("new\n")
        gm = GitManager(str(git_repo))
        assert gm.has_uncommitted_changes() is True


class TestAutoCommit:
    def test_fails_when_not_a_repo(self, temp_dir: Path):
        gm = GitManager(str(temp_dir))
        success, message = gm.auto_commit("some change")
        assert success is False
        assert "not a git repository" in message.lower()

    def test_noop_when_no_changes(self, git_repo: Path):
        gm = GitManager(str(git_repo))
        success, message = gm.auto_commit("nothing changed")
        assert success is True
        assert "no changes" in message.lower()

    def test_commits_new_file_with_tagged_message(self, git_repo: Path):
        (git_repo / "hello.py").write_text("print('hi')\n")
        gm = GitManager(str(git_repo))

        success, message = gm.auto_commit("WRITE_FILE hello.py")

        assert success is True
        assert AGENT_COMMIT_PREFIX in message
        assert gm.has_uncommitted_changes() is False

        log_success, log_message = gm.get_last_commit_message()
        assert log_success is True
        assert log_message == f"{AGENT_COMMIT_PREFIX}WRITE_FILE hello.py"

    def test_commits_modification_to_existing_file(self, git_repo: Path):
        (git_repo / "README.md").write_text("# Modified\n")
        gm = GitManager(str(git_repo))

        success, message = gm.auto_commit("EDIT_FILE README.md")

        assert success is True
        _, log_message = gm.get_last_commit_message()
        assert log_message == f"{AGENT_COMMIT_PREFIX}EDIT_FILE README.md"


class TestUndoLastAgentCommit:
    def test_fails_when_not_a_repo(self, temp_dir: Path):
        gm = GitManager(str(temp_dir))
        success, message = gm.undo_last_agent_commit()
        assert success is False
        assert "not a git repository" in message.lower()

    def test_friendly_message_when_repo_has_no_commits(self, temp_dir: Path):
        _run(["init", "-q"], cwd=temp_dir)
        gm = GitManager(str(temp_dir))
        success, message = gm.undo_last_agent_commit()
        assert success is False
        assert message == "Nothing to undo yet — this repository has no commits."
        assert "fatal:" not in message

    def test_fails_when_last_commit_is_not_from_agent(self, git_repo: Path):
        gm = GitManager(str(git_repo))
        success, message = gm.undo_last_agent_commit()
        assert success is False
        assert "not made by coding-agent" in message.lower()

    def test_reverts_last_agent_commit(self, git_repo: Path):
        (git_repo / "hello.py").write_text("print('hi')\n")
        gm = GitManager(str(git_repo))
        gm.auto_commit("WRITE_FILE hello.py")
        assert (git_repo / "hello.py").exists()

        success, message = gm.undo_last_agent_commit()

        assert success is True
        assert not (git_repo / "hello.py").exists()

    def test_refuses_to_undo_twice_in_a_row(self, git_repo: Path):
        (git_repo / "hello.py").write_text("print('hi')\n")
        gm = GitManager(str(git_repo))
        gm.auto_commit("WRITE_FILE hello.py")
        gm.undo_last_agent_commit()

        # The revert commit itself isn't tagged as an agent commit, so a
        # second undo in a row must be refused rather than reverting the
        # revert (or reaching further back into history).
        success, message = gm.undo_last_agent_commit()
        assert success is False
        assert "not made by coding-agent" in message.lower()
