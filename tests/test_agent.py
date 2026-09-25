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

    def test_parses_search_files(self, agent: CodingAgent):
        response = "Let me look:\nSEARCH_FILES: def calculate_total\n"
        operations = agent._parse_file_operations(response)
        assert ("SEARCH_FILES", {"pattern": "def calculate_total"}) in operations


class TestParseFileOperationsPreservesOrder:
    """Regression tests: operations of different types were previously
    collected via independent regex passes and appended type-by-type, so a
    response with e.g. WRITE_FILE followed by RUN_COMMAND would execute
    RUN_COMMAND first - breaking sequences like "write a script, then run
    it". Operations must now execute in the order they appear in the
    response text, regardless of type."""

    def test_write_then_run_preserves_order(self, agent: CodingAgent):
        response = (
            "WRITE_FILE: script.sh\n"
            "CONTENT:\n```\necho hello\n```\n\n"
            "RUN_COMMAND: cat script.sh\n"
        )
        operations = agent._parse_file_operations(response)
        assert [op for op, _ in operations] == ["WRITE_FILE", "RUN_COMMAND"]

    def test_run_then_write_preserves_order(self, agent: CodingAgent):
        response = (
            "RUN_COMMAND: mkdir -p out\n\n"
            "WRITE_FILE: out/script.sh\n"
            "CONTENT:\n```\necho hello\n```\n"
        )
        operations = agent._parse_file_operations(response)
        assert [op for op, _ in operations] == ["RUN_COMMAND", "WRITE_FILE"]

    def test_mixed_types_and_repeats_preserve_order(self, agent: CodingAgent):
        response = (
            "READ_FILE: a.txt\n"
            "RUN_COMMAND: echo one\n"
            "LIST_FILES: .\n"
            "SEARCH_FILES: foo\n"
            "EDIT_FILE: b.txt\n"
            "OLD:\n```\nx\n```\n"
            "NEW:\n```\ny\n```\n"
            "READ_FILE: c.txt\n"
        )
        operations = agent._parse_file_operations(response)
        assert [op for op, _ in operations] == [
            "READ_FILE",
            "RUN_COMMAND",
            "LIST_FILES",
            "SEARCH_FILES",
            "EDIT_FILE",
            "READ_FILE",
        ]
        # Confirm the two READ_FILE calls kept their distinct paths in order
        read_paths = [params["path"] for op, params in operations if op == "READ_FILE"]
        assert read_paths == ["a.txt", "c.txt"]


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


class TestExecuteSearchFiles:
    def test_finds_matches_across_workspace(self, agent: CodingAgent, temp_dir: Path):
        (temp_dir / "main.py").write_text("def calculate_total(items):\n    return sum(items)\n")
        (temp_dir / "other.py").write_text("print('nothing to see here')\n")

        success, result = agent._execute_file_operation(
            "SEARCH_FILES", {"pattern": "calculate_total"}
        )

        assert success is True
        assert "main.py" in result
        assert "calculate_total" in result
        assert "other.py" not in result

    def test_no_matches_found(self, agent: CodingAgent, temp_dir: Path):
        (temp_dir / "main.py").write_text("print('hello')\n")

        success, result = agent._execute_file_operation(
            "SEARCH_FILES", {"pattern": "nonexistent_symbol_xyz"}
        )

        assert success is True
        assert "no matches" in result.lower()

    def test_empty_pattern_fails(self, agent: CodingAgent):
        success, result = agent._execute_file_operation("SEARCH_FILES", {"pattern": ""})
        assert success is False


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


class TestLLMClientInjection:
    """Tests for the injectable llm_client constructor param (issue #9)."""

    def test_defaults_to_ollama_client_when_not_provided(self, temp_dir: Path):
        from coding_agent.llm.ollama_client import OllamaClient

        agent = CodingAgent(workspace_path=str(temp_dir), enable_history=False)

        assert isinstance(agent.llm_client, OllamaClient)

    def test_uses_injected_llm_client(self, temp_dir: Path):
        from coding_agent.llm.base import LLMProvider

        class FakeProvider(LLMProvider):
            provider_name = "fake"

            def check_connection(self) -> bool:
                return True

            def generate(self, prompt, context=None) -> str:
                return f"fake response to: {prompt}"

            def stream_generate(self, prompt, context=None):
                yield f"fake response to: {prompt}"

        fake_client = FakeProvider()
        agent = CodingAgent(
            workspace_path=str(temp_dir), enable_history=False, llm_client=fake_client
        )

        assert agent.llm_client is fake_client
        assert agent.llm_client.generate("hello") == "fake response to: hello"


class TestBuildContextIncludesOperationResults:
    """Regression tests: `_build_context()` previously filtered out *all*
    system-role messages from conversation_history, assuming they were
    duplicates of the persistent system prompt. In reality, system-role
    entries are how file content / command output / follow-up instructions
    get recorded (`_add_to_history("system", ...)`) - filtering them out
    meant the model's follow-up "explain what you found" turn never
    actually saw the file/command content it was asked to explain."""

    def test_read_file_content_reaches_followup_context(self, temp_dir: Path):
        from coding_agent.llm.base import LLMProvider

        (temp_dir / "math_utils.py").write_text("def add(a, b):\n    return a + b\n")

        class FakeProvider(LLMProvider):
            provider_name = "fake"

            def __init__(self):
                self.calls = []

            def check_connection(self) -> bool:
                return True

            def generate(self, prompt, context=None) -> str:
                self.calls.append((prompt, context or []))
                if len(self.calls) == 1:
                    return "READ_FILE: math_utils.py"
                return "It defines an add function."

            def stream_generate(self, prompt, context=None):
                yield self.generate(prompt, context)

        fake = FakeProvider()
        agent = CodingAgent(
            workspace_path=str(temp_dir),
            enable_history=False,
            llm_client=fake,
            auto_approve_commands=True,
        )
        agent.process_message("what does math_utils.py do?", stream=False)

        assert len(fake.calls) == 2
        _, followup_context = fake.calls[1]
        assert any("def add" in msg["content"] for msg in followup_context)

    def test_run_command_output_reaches_followup_context(self, temp_dir: Path):
        from coding_agent.llm.base import LLMProvider

        class FakeProvider(LLMProvider):
            provider_name = "fake"

            def __init__(self):
                self.calls = []

            def check_connection(self) -> bool:
                return True

            def generate(self, prompt, context=None) -> str:
                self.calls.append((prompt, context or []))
                if len(self.calls) == 1:
                    return "RUN_COMMAND: echo distinctive_marker_xyz"
                return "The command printed a marker."

            def stream_generate(self, prompt, context=None):
                yield self.generate(prompt, context)

        fake = FakeProvider()
        agent = CodingAgent(
            workspace_path=str(temp_dir),
            enable_history=False,
            llm_client=fake,
            auto_approve_commands=True,
        )
        agent.process_message("run echo and tell me what it printed", stream=False)

        assert len(fake.calls) == 2
        _, followup_context = fake.calls[1]
        assert any("distinctive_marker_xyz" in msg["content"] for msg in followup_context)

    def test_build_context_keeps_single_system_prompt_at_start(self, temp_dir: Path):
        agent = CodingAgent(workspace_path=str(temp_dir), enable_history=False)
        agent._add_to_history("user", "hello")
        agent._add_to_history("system", "some operation result")
        agent._add_to_history("assistant", "ok")

        context = agent._build_context()

        assert context[0]["role"] == "system"
        assert context[0]["content"] == agent.system_prompt
        assert {"role": "system", "content": "some operation result"} in context[1:]

    def test_history_trim_keeps_recent_system_messages(self, temp_dir: Path):
        """A recent operation-result (system) message must survive trimming.

        Regression test: trimming previously kept only the single oldest
        system message in the whole history and stripped *all* system
        messages out of the recent window, so a READ_FILE/RUN_COMMAND result
        produced just before hitting `max_history` was discarded even though
        the very next turn (e.g. "explain that file") depended on it.
        """
        agent = CodingAgent(workspace_path=str(temp_dir), enable_history=False, max_history=5)
        agent._add_to_history("user", "msg0")
        agent._add_to_history("system", "old stale system msg")
        for i in range(1, 8):
            agent._add_to_history("user", f"user msg {i}")
            agent._add_to_history("assistant", f"assistant msg {i}")
        agent._add_to_history("system", "recent file content the user just asked about")
        agent._add_to_history("user", "explain that file")

        assert len(agent.conversation_history) == agent.max_history
        assert any(
            msg["role"] == "system" and "recent file content" in msg["content"]
            for msg in agent.conversation_history
        )
        assert not any("old stale system msg" in msg["content"] for msg in agent.conversation_history)


class TestStructuredToolCalling:
    """Tests for the structured tool-calling path (issue #8), used when the
    configured llm_client declares `supports_tools = True`."""

    @staticmethod
    def _make_tool_calling_agent(temp_dir: Path, tool_calls=None, text=""):
        from coding_agent.llm.base import LLMProvider, ToolCall, ToolCallResult

        class FakeToolCallingProvider(LLMProvider):
            provider_name = "fake-tools"
            supports_tools = True

            def __init__(self):
                self.calls_seen = []

            def check_connection(self) -> bool:
                return True

            def generate(self, prompt, context=None) -> str:
                return text

            def stream_generate(self, prompt, context=None):
                yield text

            def generate_with_tools(self, prompt, context=None, tools=None):
                self.calls_seen.append((prompt, tools))
                if self.calls_seen and len(self.calls_seen) > 1:
                    # Follow-up call (after tool execution): just answer in text.
                    return ToolCallResult(text="Here is the answer based on the file.")
                return ToolCallResult(
                    text=text, tool_calls=[ToolCall(**tc) for tc in (tool_calls or [])]
                )

        fake_client = FakeToolCallingProvider()
        agent = CodingAgent(
            workspace_path=str(temp_dir), enable_history=False, llm_client=fake_client
        )
        return agent, fake_client

    def test_tool_call_executes_read_file_operation(self, temp_dir: Path):
        (temp_dir / "notes.txt").write_text("hello from file")
        agent, fake_client = self._make_tool_calling_agent(
            temp_dir, tool_calls=[{"name": "read_file", "arguments": {"path": "notes.txt"}}]
        )

        response = agent.process_message("What's in notes.txt?", stream=False)

        assert "Here is the answer based on the file." in response
        # First call passed the shared tool schema; agent used the tool-call
        # result rather than regex-parsing free text.
        first_call_prompt, first_call_tools = fake_client.calls_seen[0]
        assert first_call_prompt == "What's in notes.txt?"
        assert first_call_tools and any(t["name"] == "read_file" for t in first_call_tools)

    def test_plain_text_reply_with_no_tool_calls(self, temp_dir: Path):
        agent, fake_client = self._make_tool_calling_agent(
            temp_dir, tool_calls=[], text="Just a normal reply, no tools needed."
        )

        response = agent.process_message("Hello", stream=False)

        assert response == "Just a normal reply, no tools needed."
        # Only one call was made (no follow-up, since no operations ran).
        assert len(fake_client.calls_seen) == 1

    def test_tool_call_write_file_auto_approved(self, temp_dir: Path):
        agent, fake_client = self._make_tool_calling_agent(
            temp_dir,
            tool_calls=[
                {
                    "name": "write_file",
                    "arguments": {"path": "new.py", "content": "print('hi')\n"},
                }
            ],
        )
        agent.auto_approve_writes = True

        agent.process_message("Create new.py", stream=False)

        assert (temp_dir / "new.py").read_text() == "print('hi')\n"
