"""Tests for the `coding-agent undo` CLI command via Typer's CliRunner.

Other `cli.py` commands (chat/serve) require a live Ollama server or MCP
client and are out of scope here; `undo` is fully self-contained (git only)
and safe to exercise end-to-end.
"""

import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from coding_agent.cli import app

runner = CliRunner()


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    (path / "README.md").write_text("# Test repo\n")
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial commit"], cwd=path, check=True)


class TestUndoCommand:
    def test_fails_when_not_a_git_repo(self, temp_dir: Path):
        result = runner.invoke(app, ["undo", "--workspace", str(temp_dir)])
        assert result.exit_code != 0
        normalized = " ".join(result.stdout.lower().split())
        assert "is not a git repository" in normalized

    def test_fails_when_last_commit_is_not_from_agent(self, temp_dir: Path):
        _init_git_repo(temp_dir)
        result = runner.invoke(app, ["undo", "--workspace", str(temp_dir)])
        assert result.exit_code != 0
        assert "not made by coding-agent" in result.stdout.lower()

    def test_reverts_last_agent_commit(self, temp_dir: Path):
        _init_git_repo(temp_dir)
        (temp_dir / "agent_change.py").write_text("print('hi')\n")
        subprocess.run(["git", "add", "-A"], cwd=temp_dir, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "[coding-agent] WRITE_FILE agent_change.py"],
            cwd=temp_dir,
            check=True,
        )
        assert (temp_dir / "agent_change.py").exists()

        result = runner.invoke(app, ["undo", "--workspace", str(temp_dir)])

        assert result.exit_code == 0
        assert "reverted" in result.stdout.lower()
        assert not (temp_dir / "agent_change.py").exists()

    def test_help_lists_workspace_option(self):
        result = runner.invoke(app, ["undo", "--help"])
        assert result.exit_code == 0
        assert "--workspace" in result.stdout


class TestChatCommandHelp:
    def test_yes_and_git_commit_flags_present(self):
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0
        assert "--yes" in result.stdout
        assert "--git-commit" in result.stdout


class TestChatCommand:
    """Drives `chat` end-to-end with a mocked Ollama client + agent so no
    live Ollama server or LLM call is required.
    """

    def _mock_client(self, models=None):
        client = MagicMock()
        client.check_connection.return_value = True
        client.check_model_exists.return_value = True
        client.list_models.return_value = models or ["codellama:latest"]
        return client

    def test_exits_when_ollama_unreachable(self, temp_dir: Path):
        with patch("coding_agent.llm.ollama_client.OllamaClient") as MockClient:
            MockClient.return_value.check_connection.return_value = False
            result = runner.invoke(app, ["chat"], input="\n")
        assert result.exit_code == 1
        assert "cannot connect to ollama" in result.stdout.lower()

    def test_exits_when_model_missing(self, temp_dir: Path):
        with patch("coding_agent.llm.ollama_client.OllamaClient") as MockClient:
            mock_client = self._mock_client()
            mock_client.check_model_exists.return_value = False
            MockClient.return_value = mock_client
            result = runner.invoke(app, ["chat"], input="\n")
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_normal_conversation_and_exit(self, temp_dir: Path):
        mock_agent = MagicMock()
        mock_agent.session_id = "session-123"
        mock_agent.get_workspace_info.return_value = {"path": str(temp_dir), "file_count": 3}

        with (
            patch("coding_agent.llm.ollama_client.OllamaClient") as MockClient,
            patch("coding_agent.agent.CodingAgent", return_value=mock_agent),
        ):
            MockClient.return_value = self._mock_client()
            result = runner.invoke(app, ["chat"], input="hello there\nexit\n")

        assert result.exit_code == 0
        mock_agent.process_message.assert_called_once_with("hello there", stream=True)
        assert "session-123" in result.stdout
        assert "goodbye" in result.stdout.lower()

    def test_help_command_shown(self, temp_dir: Path):
        mock_agent = MagicMock()
        mock_agent.session_id = None
        mock_agent.get_workspace_info.return_value = {"path": str(temp_dir), "file_count": 0}

        with (
            patch("coding_agent.llm.ollama_client.OllamaClient") as MockClient,
            patch("coding_agent.agent.CodingAgent", return_value=mock_agent),
        ):
            MockClient.return_value = self._mock_client()
            result = runner.invoke(app, ["chat"], input="help\nquit\n")

        assert result.exit_code == 0
        assert "Available Commands" in result.stdout
        mock_agent.process_message.assert_not_called()

    def test_clear_and_workspace_commands(self, temp_dir: Path):
        mock_agent = MagicMock()
        mock_agent.session_id = None
        mock_agent.get_workspace_info.return_value = {"path": str(temp_dir), "file_count": 1}

        with (
            patch("coding_agent.llm.ollama_client.OllamaClient") as MockClient,
            patch("coding_agent.agent.CodingAgent", return_value=mock_agent),
        ):
            MockClient.return_value = self._mock_client()
            result = runner.invoke(app, ["chat"], input="clear\nworkspace\nexit\n")

        assert result.exit_code == 0
        mock_agent.clear_history.assert_called_once()
        assert mock_agent.get_workspace_info.call_count == 2

    def test_models_command_lists_models(self, temp_dir: Path):
        mock_agent = MagicMock()
        mock_agent.session_id = None
        mock_agent.get_workspace_info.return_value = {"path": str(temp_dir), "file_count": 0}

        with (
            patch("coding_agent.llm.ollama_client.OllamaClient") as MockClient,
            patch("coding_agent.agent.CodingAgent", return_value=mock_agent),
        ):
            MockClient.return_value = self._mock_client(models=["codellama:latest", "deepseek-coder"])
            result = runner.invoke(app, ["chat"], input="models\nexit\n")

        assert result.exit_code == 0
        assert "deepseek-coder" in result.stdout

    def test_yes_and_git_commit_flags_passed_to_agent(self, temp_dir: Path):
        mock_agent = MagicMock()
        mock_agent.session_id = None
        mock_agent.get_workspace_info.return_value = {"path": str(temp_dir), "file_count": 0}

        with (
            patch("coding_agent.llm.ollama_client.OllamaClient") as MockClient,
            patch("coding_agent.agent.CodingAgent", return_value=mock_agent) as MockAgentClass,
        ):
            MockClient.return_value = self._mock_client()
            result = runner.invoke(app, ["chat", "--yes", "--git-commit"], input="exit\n")

        assert result.exit_code == 0
        _, kwargs = MockAgentClass.call_args
        assert kwargs["auto_approve_commands"] is True
        assert kwargs["auto_approve_writes"] is True
        assert kwargs["enable_git_auto_commit"] is True

    def test_process_message_error_is_reported_and_loop_continues(self, temp_dir: Path):
        mock_agent = MagicMock()
        mock_agent.session_id = None
        mock_agent.get_workspace_info.return_value = {"path": str(temp_dir), "file_count": 0}
        mock_agent.process_message.side_effect = RuntimeError("model exploded")

        with (
            patch("coding_agent.llm.ollama_client.OllamaClient") as MockClient,
            patch("coding_agent.agent.CodingAgent", return_value=mock_agent),
        ):
            MockClient.return_value = self._mock_client()
            result = runner.invoke(app, ["chat"], input="hi\nexit\n")

        assert result.exit_code == 0
        assert "failed to generate response" in result.stdout.lower()
        assert "model exploded" in result.stdout


class TestServeCommand:
    """Drives `serve` with a mocked MCPServer + stdio transport so no real
    subprocess/MCP client connection is required.
    """

    def _mock_server(self, tools=None):
        server = MagicMock()
        server.list_tools.return_value = tools or [
            {"name": "read_file", "description": "Reads a file"},
            {"name": "list_files", "description": "Lists files"},
        ]
        return server

    def test_fails_for_missing_workspace(self, tmp_path: Path):
        missing = tmp_path / "does-not-exist"
        result = runner.invoke(app, ["serve", "--workspace", str(missing)])
        assert result.exit_code == 1
        assert "does not exist" in result.stdout.lower()

    def test_starts_stdio_server_and_lists_tools(self, tmp_path: Path):
        mock_server = self._mock_server()
        with (
            patch("coding_agent.mcp.server.MCPServer.with_safe_mode", return_value=mock_server),
            patch(
                "coding_agent.mcp.stdio_server.run_stdio_server", new_callable=AsyncMock
            ) as mock_run,
        ):
            result = runner.invoke(app, ["serve", "--workspace", str(tmp_path)])

        assert result.exit_code == 0
        assert "read_file" in result.stdout
        assert "Server initialized with 2 tool(s)" in result.stdout
        mock_run.assert_awaited_once()

    def test_no_safe_mode_uses_direct_constructor(self, tmp_path: Path):
        mock_server = self._mock_server(tools=[{"name": "search_history", "description": "d"}])
        with (
            patch("coding_agent.mcp.server.MCPServer", return_value=mock_server) as MockServerClass,
            patch(
                "coding_agent.mcp.stdio_server.run_stdio_server", new_callable=AsyncMock
            ) as mock_run,
        ):
            result = runner.invoke(
                app,
                ["serve", "--workspace", str(tmp_path), "--no-safe-mode", "--enable-history-tools"],
            )

        assert result.exit_code == 0
        MockServerClass.assert_called_once()
        mock_run.assert_awaited_once()

    def test_no_tools_enabled_fails(self, tmp_path: Path):
        result = runner.invoke(
            app,
            [
                "serve",
                "--workspace",
                str(tmp_path),
                "--no-safe-mode",
                "--no-file-tools",
                "--no-ai-tools",
            ],
        )
        assert result.exit_code == 1
        assert "no tools enabled" in result.stdout.lower()

    def test_http_transport_not_implemented(self, tmp_path: Path):
        mock_server = self._mock_server()
        with patch("coding_agent.mcp.server.MCPServer.with_safe_mode", return_value=mock_server):
            result = runner.invoke(
                app, ["serve", "--workspace", str(tmp_path), "--transport", "http"]
            )
        assert result.exit_code == 1
        assert "http transport not yet implemented" in result.stdout.lower()

    def test_unknown_transport_fails(self, tmp_path: Path):
        mock_server = self._mock_server()
        with patch("coding_agent.mcp.server.MCPServer.with_safe_mode", return_value=mock_server):
            result = runner.invoke(
                app, ["serve", "--workspace", str(tmp_path), "--transport", "carrier-pigeon"]
            )
        assert result.exit_code == 1
        assert "unknown transport" in result.stdout.lower()


class TestConfigCommand:
    """`config` reads/writes real environment state, so every test here runs
    in an isolated temp cwd with the config singleton reset, to avoid ever
    touching the repository's real .env file or leaking state between tests.
    """

    def _isolate(self, monkeypatch, tmp_path):
        from coding_agent.utils import config as config_module

        for key in [
            "OLLAMA_HOST",
            "OLLAMA_MODEL",
            "WORKSPACE_PATH",
            "MAX_HISTORY_LENGTH",
            "HISTORY_ENABLED",
            "SHOW_SPINNER",
            "SYNTAX_THEME",
        ]:
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setattr(config_module, "load_dotenv", lambda *a, **k: False)
        config_module.reset_config()
        monkeypatch.chdir(tmp_path)
        return config_module

    def test_show_displays_defaults(self, monkeypatch, tmp_path):
        config_module = self._isolate(monkeypatch, tmp_path)
        try:
            result = runner.invoke(app, ["config", "--show"])
            assert result.exit_code == 0
            assert "Current Configuration" in result.stdout
            assert "codellama:latest" in result.stdout
        finally:
            config_module.reset_config()

    def test_set_updates_value_and_env_file(self, monkeypatch, tmp_path):
        config_module = self._isolate(monkeypatch, tmp_path)
        try:
            result = runner.invoke(app, ["config", "--set", "OLLAMA_MODEL=deepseek-coder"])
            assert result.exit_code == 0
            assert "deepseek-coder" in result.stdout
            assert (tmp_path / ".env").exists()
            assert "OLLAMA_MODEL=deepseek-coder" in (tmp_path / ".env").read_text()
        finally:
            config_module.reset_config()

    def test_set_rejects_missing_equals_sign(self, monkeypatch, tmp_path):
        config_module = self._isolate(monkeypatch, tmp_path)
        try:
            result = runner.invoke(app, ["config", "--set", "OLLAMA_MODEL"])
            assert result.exit_code != 0
            assert "invalid format" in result.stdout.lower()
        finally:
            config_module.reset_config()

    def test_no_flags_shows_usage_hint(self, monkeypatch, tmp_path):
        config_module = self._isolate(monkeypatch, tmp_path)
        try:
            result = runner.invoke(app, ["config"])
            assert result.exit_code == 0
            assert "--show" in result.stdout
            assert "--set" in result.stdout
        finally:
            config_module.reset_config()


class TestHistoryCommand:
    """`history` always constructs `HistoryManager()` with the default
    `~/.coding-agent/history` directory, so `Path.home` is patched to a temp
    directory in every test here to avoid touching the real user history.
    """

    def _isolate_home(self, monkeypatch, tmp_path):
        from pathlib import Path as PathClass

        monkeypatch.setattr(PathClass, "home", lambda: tmp_path)

    def test_list_with_no_sessions(self, monkeypatch, tmp_path):
        self._isolate_home(monkeypatch, tmp_path)
        result = runner.invoke(app, ["history", "--list"])
        assert result.exit_code == 0
        assert "no conversation sessions found" in result.stdout.lower()

    def test_list_shows_created_session(self, monkeypatch, tmp_path):
        self._isolate_home(monkeypatch, tmp_path)
        from coding_agent.storage.history import HistoryManager

        history_mgr = HistoryManager()
        session_id = history_mgr.create_session(workspace_path=str(tmp_path), model="codellama:latest")
        history_mgr.add_message(session_id, role="user", content="hello")

        # Widen the terminal so Rich doesn't truncate the session ID column.
        result = runner.invoke(app, ["history", "--list"], env={"COLUMNS": "200"})
        assert result.exit_code == 0
        assert session_id in result.stdout

    def test_view_unknown_session(self, monkeypatch, tmp_path):
        self._isolate_home(monkeypatch, tmp_path)
        result = runner.invoke(app, ["history", "--view", "does-not-exist"])
        assert result.exit_code == 0
        assert "not found" in result.stdout.lower()

    def test_view_existing_session_shows_messages(self, monkeypatch, tmp_path):
        self._isolate_home(monkeypatch, tmp_path)
        from coding_agent.storage.history import HistoryManager

        history_mgr = HistoryManager()
        session_id = history_mgr.create_session(workspace_path=str(tmp_path), model="codellama:latest")
        history_mgr.add_message(session_id, role="user", content="hello there")

        result = runner.invoke(app, ["history", "--view", session_id])
        assert result.exit_code == 0
        assert "Session Details" in result.stdout
        assert "hello there" in result.stdout

    def test_delete_unknown_session_reports_failure(self, monkeypatch, tmp_path):
        self._isolate_home(monkeypatch, tmp_path)
        result = runner.invoke(app, ["history", "--delete", "does-not-exist"])
        assert result.exit_code == 0
        assert "failed to delete" in result.stdout.lower()

    def test_delete_existing_session(self, monkeypatch, tmp_path):
        self._isolate_home(monkeypatch, tmp_path)
        from coding_agent.storage.history import HistoryManager

        history_mgr = HistoryManager()
        session_id = history_mgr.create_session(workspace_path=str(tmp_path), model="codellama:latest")

        result = runner.invoke(app, ["history", "--delete", session_id])
        assert result.exit_code == 0
        assert "deleted" in result.stdout.lower()

    def test_export_session(self, monkeypatch, tmp_path):
        self._isolate_home(monkeypatch, tmp_path)
        from coding_agent.storage.history import HistoryManager

        history_mgr = HistoryManager()
        session_id = history_mgr.create_session(workspace_path=str(tmp_path), model="codellama:latest")
        history_mgr.add_message(session_id, role="user", content="hello")

        output_file = tmp_path / "exported.md"
        result = runner.invoke(
            app, ["history", "--export", session_id, "--output", str(output_file), "--format", "md"]
        )
        assert result.exit_code == 0
        assert "exported" in result.stdout.lower()
        assert output_file.exists()

    def test_no_flags_shows_usage_hint(self, monkeypatch, tmp_path):
        self._isolate_home(monkeypatch, tmp_path)
        result = runner.invoke(app, ["history"])
        assert result.exit_code == 0
        assert "--list" in result.stdout
        assert "--view" in result.stdout


class TestTopLevelHelp:
    def test_lists_all_commands(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for command in ["chat", "init", "undo", "config", "history", "serve"]:
            assert command in result.stdout
