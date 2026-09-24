"""Tests for Anthropic client."""

from unittest.mock import MagicMock, Mock, patch

from coding_agent.llm.anthropic_client import (
    AnthropicProvider,
    _split_system_and_messages,
    test_anthropic_connection as check_anthropic_connection,
)


class TestSplitSystemAndMessages:
    """Test suite for the shared-context -> Anthropic-shape helper."""

    def test_no_context(self):
        """Test with no prior context, only the current prompt."""
        system, messages = _split_system_and_messages(None, "Hello")

        assert system is None
        assert messages == [{"role": "user", "content": "Hello"}]

    def test_extracts_system_message(self):
        """Test that a leading system message is pulled out separately."""
        context = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        system, messages = _split_system_and_messages(context, "How are you?")

        assert system == "You are helpful."
        assert messages == [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "How are you?"},
        ]

    def test_no_system_message_in_context(self):
        """Test context with no system message present."""
        context = [{"role": "user", "content": "Hi"}]
        system, messages = _split_system_and_messages(context, "Continue")

        assert system is None
        assert len(messages) == 2


class TestAnthropicProvider:
    """Test suite for AnthropicProvider."""

    @patch("anthropic.Anthropic")
    def test_initialization(self, mock_anthropic_class):
        """Test client initialization."""
        client = AnthropicProvider(api_key="test-key", model="claude-3-5-sonnet-latest")

        assert client.model == "claude-3-5-sonnet-latest"
        assert client.provider_name == "anthropic"
        mock_anthropic_class.assert_called_once_with(api_key="test-key")

    @patch("anthropic.Anthropic")
    def test_check_connection_success(self, mock_anthropic_class):
        """Test successful connection check."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        client = AnthropicProvider(api_key="test-key")
        result = client.check_connection()

        assert result is True
        mock_client.messages.create.assert_called_once()

    @patch("anthropic.Anthropic")
    def test_check_connection_failure(self, mock_anthropic_class):
        """Test connection check failure."""
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("Invalid API key")
        mock_anthropic_class.return_value = mock_client

        client = AnthropicProvider(api_key="bad-key")
        result = client.check_connection()

        assert result is False

    def test_list_models_returns_reference_list(self):
        """Test that list_models returns a non-empty hardcoded list."""
        with patch("anthropic.Anthropic"):
            client = AnthropicProvider(api_key="test-key")
            models = client.list_models()

        assert len(models) > 0
        assert "claude-3-5-sonnet-latest" in models

    @patch("anthropic.Anthropic")
    def test_generate_simple(self, mock_anthropic_class):
        """Test simple text generation."""
        mock_client = Mock()
        text_block = Mock(type="text", text="Test response")
        mock_response = Mock(content=[text_block])
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        client = AnthropicProvider(api_key="test-key")
        response = client.generate("Test prompt")

        assert response == "Test response"

    @patch("anthropic.Anthropic")
    def test_generate_with_system_context(self, mock_anthropic_class):
        """Test that a system message in context is passed via the system= kwarg."""
        mock_client = Mock()
        text_block = Mock(type="text", text="Response")
        mock_response = Mock(content=[text_block])
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        client = AnthropicProvider(api_key="test-key")
        context = [{"role": "system", "content": "Be concise."}]
        client.generate("Hello", context=context)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == "Be concise."
        assert call_kwargs["messages"] == [{"role": "user", "content": "Hello"}]

    @patch("anthropic.Anthropic")
    def test_generate_error_handling(self, mock_anthropic_class):
        """Test error handling during generation."""
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("API error")
        mock_anthropic_class.return_value = mock_client

        client = AnthropicProvider(api_key="test-key")
        response = client.generate("Test prompt")

        assert response == ""

    @patch("anthropic.Anthropic")
    def test_stream_generate(self, mock_anthropic_class):
        """Test streaming generation."""
        mock_client = Mock()
        mock_stream_cm = MagicMock()
        mock_stream_cm.__enter__.return_value.text_stream = iter(["Hello ", "world", "!"])
        mock_client.messages.stream.return_value = mock_stream_cm
        mock_anthropic_class.return_value = mock_client

        client = AnthropicProvider(api_key="test-key")
        chunks = list(client.stream_generate("Test prompt"))

        assert "".join(chunks) == "Hello world!"


class TestAnthropicConnectionHelper:
    """Test suite for check_anthropic_connection()."""

    def test_missing_api_key(self):
        """Test that a missing API key is reported without constructing a client."""
        success, message = check_anthropic_connection(None, "claude-3-5-sonnet-latest")

        assert success is False
        assert "ANTHROPIC_API_KEY" in message

    @patch("anthropic.Anthropic")
    def test_successful_connection(self, mock_anthropic_class):
        """Test a successful connection check end-to-end."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        success, message = check_anthropic_connection("test-key", "claude-3-5-sonnet-latest")

        assert success is True
        assert "claude-3-5-sonnet-latest" in message

    @patch("anthropic.Anthropic")
    def test_failed_connection(self, mock_anthropic_class):
        """Test a failed connection check end-to-end."""
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("bad key")
        mock_anthropic_class.return_value = mock_client

        success, message = check_anthropic_connection("bad-key", "claude-3-5-sonnet-latest")

        assert success is False
