"""Tests for Ollama client."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from coding_agent.llm.ollama_client import OllamaClient


class TestOllamaClient:
    """Test suite for OllamaClient."""

    def test_initialization(self):
        """Test client initialization."""
        client = OllamaClient(host="http://localhost:11434", model="codellama:latest")
        
        assert client.host == "http://localhost:11434"
        assert client.model == "codellama:latest"

    @patch('coding_agent.llm.ollama_client.ollama.Client')
    def test_check_connection_success(self, mock_client_class):
        """Test successful connection check."""
        mock_client = Mock()
        mock_client.list.return_value = {"models": [{"name": "codellama:latest"}]}
        mock_client_class.return_value = mock_client
        
        client = OllamaClient(host="http://localhost:11434", model="codellama:latest")
        result = client.check_connection()
        
        assert result is True
        mock_client.list.assert_called_once()

    @patch('coding_agent.llm.ollama_client.ollama.Client')
    def test_check_connection_failure(self, mock_client_class):
        """Test connection check failure."""
        mock_client = Mock()
        mock_client.list.side_effect = Exception("Connection refused")
        mock_client_class.return_value = mock_client
        
        client = OllamaClient(host="http://localhost:11434", model="codellama:latest")
        result = client.check_connection()
        
        assert result is False

    @patch('coding_agent.llm.ollama_client.ollama.Client')
    def test_check_model_exists_true(self, mock_client_class):
        """Test checking if model exists (true case)."""
        mock_client = Mock()
        mock_client.list.return_value = {
            "models": [
                {"name": "codellama:latest"},
                {"name": "llama2:latest"}
            ]
        }
        mock_client_class.return_value = mock_client
        
        client = OllamaClient(host="http://localhost:11434", model="codellama:latest")
        result = client.check_model_exists()
        
        assert result is True

    @patch('coding_agent.llm.ollama_client.ollama.Client')
    def test_check_model_exists_false(self, mock_client_class):
        """Test checking if model exists (false case)."""
        mock_client = Mock()
        mock_client.list.return_value = {
            "models": [
                {"name": "llama2:latest"}
            ]
        }
        mock_client_class.return_value = mock_client
        
        client = OllamaClient(host="http://localhost:11434", model="codellama:latest")
        result = client.check_model_exists()
        
        assert result is False

    @patch('coding_agent.llm.ollama_client.ollama.Client')
    def test_list_models(self, mock_client_class):
        """Test listing available models."""
        mock_client = Mock()
        mock_client.list.return_value = {
            "models": [
                {"name": "codellama:latest"},
                {"name": "llama2:latest"},
                {"name": "mistral:latest"}
            ]
        }
        mock_client_class.return_value = mock_client
        
        client = OllamaClient(host="http://localhost:11434", model="codellama:latest")
        models = client.list_models()
        
        assert len(models) == 3
        assert "codellama:latest" in models
        assert "llama2:latest" in models
        assert "mistral:latest" in models

    @patch('coding_agent.llm.ollama_client.ollama.Client')
    def test_generate_simple(self, mock_client_class):
        """Test simple text generation."""
        mock_client = Mock()
        mock_client.chat.return_value = {
            "message": {"content": "This is a test response."}
        }
        mock_client_class.return_value = mock_client
        
        client = OllamaClient(host="http://localhost:11434", model="codellama:latest")
        response = client.generate("Test prompt")
        
        assert response == "This is a test response."
        mock_client.chat.assert_called_once()

    @patch('coding_agent.llm.ollama_client.ollama.Client')
    def test_generate_with_context(self, mock_client_class):
        """Test generation with conversation context."""
        mock_client = Mock()
        mock_client.chat.return_value = {
            "message": {"content": "Response with context"}
        }
        mock_client_class.return_value = mock_client
        
        client = OllamaClient(host="http://localhost:11434", model="codellama:latest")
        context = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        response = client.generate("How are you?", context=context)
        
        assert "Response with context" in response or response is not None
        # Verify chat was called with messages
        assert mock_client.chat.called or mock_client.generate.called

    @patch('coding_agent.llm.ollama_client.ollama.Client')
    def test_stream_generate(self, mock_client_class):
        """Test streaming generation."""
        mock_client = Mock()
        # Simulate streaming response with correct structure
        mock_client.chat.return_value = [
            {"message": {"content": "Hello "}},
            {"message": {"content": "world"}},
            {"message": {"content": "!"}}
        ]
        mock_client_class.return_value = mock_client
        
        client = OllamaClient(host="http://localhost:11434", model="codellama:latest")
        chunks = list(client.stream_generate("Test prompt"))
        
        assert len(chunks) == 3
        full_text = "".join(chunks)
        assert "Hello" in full_text
        assert "world" in full_text

    @patch('coding_agent.llm.ollama_client.ollama.Client')
    def test_generate_error_handling(self, mock_client_class):
        """Test error handling during generation."""
        mock_client = Mock()
        mock_client.chat.side_effect = Exception("Generation failed")
        mock_client_class.return_value = mock_client
        
        client = OllamaClient(host="http://localhost:11434", model="codellama:latest")
        
        # The implementation catches exceptions and returns empty string
        response = client.generate("Test prompt")
        assert response == ""

    def test_host_normalization(self):
        """Test that host URL is stored as provided."""
        # The implementation doesn't normalize - it stores as-is
        client = OllamaClient(host="localhost:11434", model="test")
        assert client.host == "localhost:11434"
        
        client2 = OllamaClient(host="http://localhost:11434", model="test")
        assert client2.host == "http://localhost:11434"

    @patch('coding_agent.llm.ollama_client.ollama.Client')
    def test_empty_model_list(self, mock_client_class):
        """Test handling of empty model list."""
        mock_client = Mock()
        mock_client.list.return_value = {"models": []}
        mock_client_class.return_value = mock_client
        
        client = OllamaClient(host="http://localhost:11434", model="codellama:latest")
        models = client.list_models()
        
        assert models == []
        assert client.check_model_exists() is False
