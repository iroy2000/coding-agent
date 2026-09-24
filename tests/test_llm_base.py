"""Tests for coding_agent.llm.base (LLMProvider interface)."""

from coding_agent.llm.base import LLMProvider, ToolCall, ToolCallResult


class _MinimalProvider(LLMProvider):
    """A provider implementing only the required abstract methods, used to
    verify the base class's default (non-tool-calling) behavior."""

    provider_name = "minimal"

    def check_connection(self) -> bool:
        return True

    def generate(self, prompt, context=None) -> str:
        return f"echo: {prompt}"

    def stream_generate(self, prompt, context=None):
        yield f"echo: {prompt}"


class TestLLMProviderDefaults:
    """Test suite for LLMProvider's default (non-tool-calling) behavior."""

    def test_supports_tools_defaults_to_false(self):
        provider = _MinimalProvider()
        assert provider.supports_tools is False

    def test_generate_with_tools_falls_back_to_generate(self):
        """Providers that don't override generate_with_tools() must get a
        plain-text ToolCallResult with no tool calls, so CodingAgent falls
        back to text-format regex parsing (issue #8)."""
        provider = _MinimalProvider()
        result = provider.generate_with_tools("hello", tools=[{"name": "read_file"}])

        assert isinstance(result, ToolCallResult)
        assert result.text == "echo: hello"
        assert result.tool_calls == []

    def test_list_models_defaults_to_empty(self):
        assert _MinimalProvider().list_models() == []

    def test_check_model_exists_defaults_to_true(self):
        assert _MinimalProvider().check_model_exists() is True


class TestToolCallDataclasses:
    def test_tool_call_defaults(self):
        call = ToolCall(name="read_file", arguments={"path": "a.py"})
        assert call.id is None

    def test_tool_call_result_defaults(self):
        result = ToolCallResult()
        assert result.text == ""
        assert result.tool_calls == []
