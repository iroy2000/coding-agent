"""Tests for the LLM provider factory."""

from unittest.mock import Mock, patch

import pytest

from coding_agent.llm.factory import create_llm_client, get_active_model
from coding_agent.llm.factory import test_llm_connection as check_llm_connection
from coding_agent.llm.ollama_client import OllamaClient
from coding_agent.utils.config import Config

_ENV_KEYS = [
    "OLLAMA_HOST",
    "OLLAMA_MODEL",
    "LLM_PROVIDER",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
]


def _make_config(**overrides) -> Config:
    """Build a Config instance without touching the real environment/.env file."""
    env = {key: "" for key in _ENV_KEYS}
    env.update(overrides)
    with patch("coding_agent.utils.config.load_dotenv", lambda *a, **k: False), patch.dict(
        "os.environ", {k: v for k, v in env.items() if v != ""}, clear=True
    ):
        return Config()


class TestCreateLLMClient:
    """Test suite for create_llm_client()."""

    def test_creates_ollama_by_default(self):
        """Test that ollama is the default provider."""
        config = _make_config()
        client = create_llm_client(config)

        assert isinstance(client, OllamaClient)
        assert client.provider_name == "ollama"

    @patch("openai.OpenAI")
    def test_creates_openai(self, mock_openai_class):
        """Test constructing the OpenAI provider from config."""
        config = _make_config(LLM_PROVIDER="openai", OPENAI_API_KEY="test-key")
        client = create_llm_client(config)

        assert client.provider_name == "openai"

    @patch("anthropic.Anthropic")
    def test_creates_anthropic(self, mock_anthropic_class):
        """Test constructing the Anthropic provider from config."""
        config = _make_config(LLM_PROVIDER="anthropic", ANTHROPIC_API_KEY="test-key")
        client = create_llm_client(config)

        assert client.provider_name == "anthropic"

    def test_unknown_provider_raises(self):
        """Test that an unsupported provider name raises ValueError."""
        config = _make_config(LLM_PROVIDER="not-a-real-provider")

        with pytest.raises(ValueError):
            create_llm_client(config)


class TestGetActiveModel:
    """Test suite for get_active_model()."""

    def test_ollama_model(self):
        config = _make_config(OLLAMA_MODEL="codellama:latest")
        assert get_active_model(config) == "codellama:latest"

    def test_openai_model(self):
        config = _make_config(LLM_PROVIDER="openai", OPENAI_MODEL="gpt-4o")
        assert get_active_model(config) == "gpt-4o"

    def test_anthropic_model(self):
        config = _make_config(LLM_PROVIDER="anthropic", ANTHROPIC_MODEL="claude-3-5-haiku-latest")
        assert get_active_model(config) == "claude-3-5-haiku-latest"


class TestTestLLMConnection:
    """Test suite for check_llm_connection()."""

    @patch("coding_agent.llm.ollama_client.test_ollama_connection")
    def test_dispatches_to_ollama(self, mock_test):
        mock_test.return_value = (True, "ok")
        config = _make_config()

        success, message = check_llm_connection(config)

        assert success is True
        mock_test.assert_called_once_with(config.ollama_host, config.ollama_model)

    @patch("coding_agent.llm.openai_client.test_openai_connection")
    def test_dispatches_to_openai(self, mock_test):
        mock_test.return_value = (True, "ok")
        config = _make_config(LLM_PROVIDER="openai", OPENAI_API_KEY="test-key")

        success, message = check_llm_connection(config)

        assert success is True
        mock_test.assert_called_once_with(config.openai_api_key, config.openai_model)

    @patch("coding_agent.llm.anthropic_client.test_anthropic_connection")
    def test_dispatches_to_anthropic(self, mock_test):
        mock_test.return_value = (True, "ok")
        config = _make_config(LLM_PROVIDER="anthropic", ANTHROPIC_API_KEY="test-key")

        success, message = check_llm_connection(config)

        assert success is True
        mock_test.assert_called_once_with(config.anthropic_api_key, config.anthropic_model)

    def test_unknown_provider(self):
        config = _make_config(LLM_PROVIDER="not-a-real-provider")

        success, message = check_llm_connection(config)

        assert success is False
        assert "not-a-real-provider" in message
