"""Tests for coding_agent.utils.config."""

from pathlib import Path

import pytest

from coding_agent.utils import config as config_module
from coding_agent.utils.config import Config, get_config, reset_config


@pytest.fixture(autouse=True)
def _reset_global_config():
    """Ensure the global config singleton doesn't leak between tests."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all coding-agent related env vars before each test."""
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
    # Prevent load_dotenv() from picking up a real .env file in the repo root.
    monkeypatch.chdir(Path.cwd())
    monkeypatch.setattr(config_module, "load_dotenv", lambda *a, **k: False)
    return monkeypatch


class TestConfigDefaults:
    def test_defaults_when_no_env_vars_set(self, clean_env):
        cfg = Config()
        assert cfg.ollama_host == "http://localhost:11434"
        assert cfg.ollama_model == "codellama:latest"
        assert cfg.workspace_path == Path(".").resolve()
        assert cfg.max_history_length == 50
        assert cfg.history_enabled is True
        assert cfg.show_spinner is True
        assert cfg.syntax_theme == "monokai"
        assert cfg.user_data_dir == Path.home() / ".coding-agent"
        assert cfg.history_dir == cfg.user_data_dir / "history"

    def test_env_vars_override_defaults(self, clean_env, temp_dir):
        clean_env.setenv("OLLAMA_HOST", "http://example.com:1234")
        clean_env.setenv("OLLAMA_MODEL", "deepseek-coder")
        clean_env.setenv("WORKSPACE_PATH", str(temp_dir))
        clean_env.setenv("MAX_HISTORY_LENGTH", "100")
        clean_env.setenv("HISTORY_ENABLED", "false")
        clean_env.setenv("SHOW_SPINNER", "false")
        clean_env.setenv("SYNTAX_THEME", "dracula")

        cfg = Config()

        assert cfg.ollama_host == "http://example.com:1234"
        assert cfg.ollama_model == "deepseek-coder"
        assert cfg.workspace_path == temp_dir.resolve()
        assert cfg.max_history_length == 100
        assert cfg.history_enabled is False
        assert cfg.show_spinner is False
        assert cfg.syntax_theme == "dracula"

    @pytest.mark.parametrize(
        "raw_value,expected",
        [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("false", False),
            ("False", False),
            ("anything-else", False),
        ],
    )
    def test_history_enabled_boolean_parsing(self, clean_env, raw_value, expected):
        clean_env.setenv("HISTORY_ENABLED", raw_value)
        cfg = Config()
        assert cfg.history_enabled is expected


class TestConfigEnsureDirectories:
    def test_ensure_directories_creates_paths(self, clean_env, monkeypatch, tmp_path):
        cfg = Config()
        fake_home = tmp_path / "fakehome"
        cfg.user_data_dir = fake_home / ".coding-agent"
        cfg.history_dir = cfg.user_data_dir / "history"

        assert not cfg.user_data_dir.exists()

        cfg.ensure_directories()

        assert cfg.user_data_dir.is_dir()
        assert cfg.history_dir.is_dir()


class TestConfigValidate:
    def test_validate_success(self, clean_env, temp_dir):
        clean_env.setenv("WORKSPACE_PATH", str(temp_dir))
        cfg = Config()
        is_valid, errors = cfg.validate()
        assert is_valid is True
        assert errors == []

    def test_validate_missing_workspace(self, clean_env, tmp_path):
        missing_path = tmp_path / "does-not-exist"
        clean_env.setenv("WORKSPACE_PATH", str(missing_path))
        cfg = Config()
        is_valid, errors = cfg.validate()
        assert is_valid is False
        assert any("does not exist" in e for e in errors)

    def test_validate_invalid_max_history_length(self, clean_env):
        clean_env.setenv("MAX_HISTORY_LENGTH", "0")
        cfg = Config()
        is_valid, errors = cfg.validate()
        assert is_valid is False
        assert any("MAX_HISTORY_LENGTH" in e for e in errors)

    def test_validate_accumulates_multiple_errors(self, clean_env, tmp_path):
        missing_path = tmp_path / "nope"
        clean_env.setenv("WORKSPACE_PATH", str(missing_path))
        clean_env.setenv("MAX_HISTORY_LENGTH", "-5")
        cfg = Config()
        is_valid, errors = cfg.validate()
        assert is_valid is False
        assert len(errors) == 2


class TestConfigUpdate:
    def test_update_rejects_invalid_key(self, clean_env, capsys):
        cfg = Config()
        result = cfg.update("NOT_A_REAL_KEY", "value")
        assert result is False

    def test_update_sets_env_var(self, clean_env):
        cfg = Config()
        result = cfg.update("OLLAMA_MODEL", "qwen2.5-coder")
        assert result is True
        assert config_module.os.environ["OLLAMA_MODEL"] == "qwen2.5-coder"

    def test_update_creates_env_file_if_missing(self, clean_env, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cfg = Config()
        assert not (tmp_path / ".env").exists()

        cfg.update("OLLAMA_MODEL", "codellama:13b")

        env_file = tmp_path / ".env"
        assert env_file.exists()
        assert "OLLAMA_MODEL=codellama:13b" in env_file.read_text()

    def test_update_modifies_existing_key_in_env_file(self, clean_env, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("OLLAMA_MODEL=old-model\nOTHER_KEY=stay\n")

        cfg = Config()
        cfg.update("OLLAMA_MODEL", "new-model")

        content = env_file.read_text()
        assert "OLLAMA_MODEL=new-model" in content
        assert "OTHER_KEY=stay" in content
        assert "old-model" not in content

    def test_update_appends_new_key_to_existing_env_file(self, clean_env, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("OLLAMA_MODEL=codellama:latest\n")

        cfg = Config()
        cfg.update("SYNTAX_THEME", "nord")

        content = env_file.read_text()
        assert "SYNTAX_THEME=nord" in content
        assert "OLLAMA_MODEL=codellama:latest" in content


class TestConfigDisplay:
    def test_display_prints_table_without_raising(self, clean_env, capsys):
        cfg = Config()
        cfg.display()
        captured = capsys.readouterr()
        assert "Current Configuration" in captured.out
        assert "Ollama Model" in captured.out


class TestConfigDotenvDiscovery:
    """Regression tests for issue #3: editable/dev installs picking up the
    coding-agent-cli repo's own .env instead of the target project's .env.
    """

    def test_loads_dotenv_from_cwd_not_from_editable_install_repo_root(
        self, monkeypatch, tmp_path
    ):
        """Config() must find the CWD-local .env even when config.py's real
        file location (as with an editable/dev install, e.g.
        `pip install -e ".[dev]"`) lives inside a different repo tree that
        also happens to contain its own .env file.
        """
        for key in ["OLLAMA_HOST", "OLLAMA_MODEL"]:
            monkeypatch.delenv(key, raising=False)

        # Simulate the coding-agent-cli repo's own checkout with its own .env.
        repo_root = tmp_path / "coding-agent-cli"
        fake_module_dir = repo_root / "src" / "coding_agent" / "utils"
        fake_module_dir.mkdir(parents=True)
        (repo_root / ".env").write_text("OLLAMA_MODEL=qwen2.5-coder\n")
        monkeypatch.setattr(
            config_module, "__file__", str(fake_module_dir / "config.py")
        )

        # Simulate the target project the developer is actually running from.
        project_dir = tmp_path / "some_other_project"
        project_dir.mkdir()
        (project_dir / ".env").write_text("OLLAMA_MODEL=codellama:latest\n")
        monkeypatch.chdir(project_dir)

        cfg = Config()

        assert cfg.ollama_model == "codellama:latest"


class TestGlobalConfigSingleton:
    def test_get_config_returns_same_instance(self, clean_env):
        cfg1 = get_config()
        cfg2 = get_config()
        assert cfg1 is cfg2

    def test_reset_config_creates_new_instance(self, clean_env):
        cfg1 = get_config()
        reset_config()
        cfg2 = get_config()
        assert cfg1 is not cfg2
