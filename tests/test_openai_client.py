"""Tests for OpenAI client."""

from unittest.mock import Mock, patch

from coding_agent.llm.openai_client import OpenAIProvider
from coding_agent.llm.openai_client import test_openai_connection as check_openai_connection


class TestOpenAIProvider:
    """Test suite for OpenAIProvider."""

    @patch("openai.OpenAI")
    def test_initialization(self, mock_openai_class):
        """Test client initialization."""
        client = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")

        assert client.model == "gpt-4o-mini"
        assert client.provider_name == "openai"
        mock_openai_class.assert_called_once_with(api_key="test-key")

    @patch("openai.OpenAI")
    def test_check_connection_success(self, mock_openai_class):
        """Test successful connection check."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        client = OpenAIProvider(api_key="test-key")
        result = client.check_connection()

        assert result is True
        mock_client.models.list.assert_called_once()

    @patch("openai.OpenAI")
    def test_check_connection_failure(self, mock_openai_class):
        """Test connection check failure."""
        mock_client = Mock()
        mock_client.models.list.side_effect = Exception("Invalid API key")
        mock_openai_class.return_value = mock_client

        client = OpenAIProvider(api_key="bad-key")
        result = client.check_connection()

        assert result is False

    @patch("openai.OpenAI")
    def test_list_models(self, mock_openai_class):
        """Test listing available models."""
        mock_client = Mock()
        mock_model_a = Mock()
        mock_model_a.id = "gpt-4o"
        mock_model_b = Mock()
        mock_model_b.id = "gpt-4o-mini"
        mock_client.models.list.return_value = Mock(data=[mock_model_a, mock_model_b])
        mock_openai_class.return_value = mock_client

        client = OpenAIProvider(api_key="test-key")
        models = client.list_models()

        assert "gpt-4o" in models
        assert "gpt-4o-mini" in models

    @patch("openai.OpenAI")
    def test_list_models_falls_back_on_error(self, mock_openai_class):
        """Test that list_models returns a reference list if the API call fails."""
        mock_client = Mock()
        mock_client.models.list.side_effect = Exception("network error")
        mock_openai_class.return_value = mock_client

        client = OpenAIProvider(api_key="test-key")
        models = client.list_models()

        assert len(models) > 0

    @patch("openai.OpenAI")
    def test_generate_simple(self, mock_openai_class):
        """Test simple text generation."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        client = OpenAIProvider(api_key="test-key")
        response = client.generate("Test prompt")

        assert response == "Test response"
        mock_client.chat.completions.create.assert_called_once()

    @patch("openai.OpenAI")
    def test_generate_with_context(self, mock_openai_class):
        """Test generation with conversation context."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Response with context"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        client = OpenAIProvider(api_key="test-key")
        context = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]
        response = client.generate("How are you?", context=context)

        assert response == "Response with context"
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["messages"][-1] == {"role": "user", "content": "How are you?"}
        assert len(call_kwargs["messages"]) == 3

    @patch("openai.OpenAI")
    def test_generate_error_handling(self, mock_openai_class):
        """Test error handling during generation."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_openai_class.return_value = mock_client

        client = OpenAIProvider(api_key="test-key")
        response = client.generate("Test prompt")

        assert response == ""

    @patch("openai.OpenAI")
    def test_stream_generate(self, mock_openai_class):
        """Test streaming generation."""
        mock_client = Mock()

        def make_chunk(text):
            chunk = Mock()
            chunk.choices = [Mock(delta=Mock(content=text))]
            return chunk

        mock_client.chat.completions.create.return_value = iter(
            [make_chunk("Hello "), make_chunk("world"), make_chunk("!")]
        )
        mock_openai_class.return_value = mock_client

        client = OpenAIProvider(api_key="test-key")
        chunks = list(client.stream_generate("Test prompt"))

        assert "".join(chunks) == "Hello world!"


class TestOpenAIConnectionHelper:
    """Test suite for check_openai_connection()."""

    def test_missing_api_key(self):
        """Test that a missing API key is reported without constructing a client."""
        success, message = check_openai_connection(None, "gpt-4o-mini")

        assert success is False
        assert "OPENAI_API_KEY" in message

    @patch("openai.OpenAI")
    def test_successful_connection(self, mock_openai_class):
        """Test a successful connection check end-to-end."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        success, message = check_openai_connection("test-key", "gpt-4o-mini")

        assert success is True
        assert "gpt-4o-mini" in message

    @patch("openai.OpenAI")
    def test_failed_connection(self, mock_openai_class):
        """Test a failed connection check end-to-end."""
        mock_client = Mock()
        mock_client.models.list.side_effect = Exception("bad key")
        mock_openai_class.return_value = mock_client

        success, message = check_openai_connection("bad-key", "gpt-4o-mini")

        assert success is False
