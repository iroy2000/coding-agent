"""Shared interface implemented by every LLM backend (Ollama, OpenAI, Anthropic, ...).

`CodingAgent` and the CLI only depend on this interface, never on a specific
provider's SDK, so adding a new backend means implementing this class and
wiring it into `coding_agent.llm.factory` - nothing else in the agent loop
needs to change.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional


@dataclass
class ToolCall:
    """A single structured tool/function call requested by the model."""

    name: str
    arguments: Dict[str, Any]
    id: Optional[str] = None


@dataclass
class ToolCallResult:
    """
    Result of a tool-calling-capable generation.

    Exactly one of `text`/`tool_calls` is typically meaningful: a normal
    conversational reply sets `text` and leaves `tool_calls` empty; a
    request to invoke actions sets `tool_calls` (with `text` usually empty).
    """

    text: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)


class LLMProvider(ABC):
    """Abstract base class for a chat-capable LLM backend."""

    #: Human-readable provider name (e.g. "ollama", "openai", "anthropic"),
    #: used in error/status messages.
    provider_name: str = "unknown"

    #: Whether this provider supports native structured tool/function calling
    #: (see `generate_with_tools`). Providers that don't (or can't guarantee
    #: it for the configured model) leave this False, and `CodingAgent` falls
    #: back to text-format regex parsing of the prompted command syntax.
    supports_tools: bool = False

    @abstractmethod
    def check_connection(self) -> bool:
        """
        Check whether the backend is reachable/usable with current config.

        For local backends (Ollama) this means the server responds; for
        hosted APIs (OpenAI/Anthropic) this means the API key is present
        and accepted.

        Returns:
            True if the backend is ready to serve requests.
        """
        raise NotImplementedError

    def list_models(self) -> List[str]:
        """
        List models available through this backend, if the backend supports
        discovery. Hosted providers that don't expose (or need) this may
        return an empty list; callers must not assume it's exhaustive or
        authoritative.

        Returns:
            List of model names.
        """
        return []

    def check_model_exists(self, model_name: Optional[str] = None) -> bool:
        """
        Check whether the configured (or given) model is usable.

        Local backends that manage their own model downloads (Ollama)
        should do a real check; hosted providers typically can't verify
        this without an actual API call, so the default implementation
        optimistically returns True and lets the first `generate()` call
        surface any real error.

        Args:
            model_name: Model name to check (uses the provider's configured
                default if None)

        Returns:
            True if the model is presumed usable.
        """
        return True

    @abstractmethod
    def generate(self, prompt: str, context: Optional[list] = None) -> str:
        """
        Generate a single, non-streaming response.

        Args:
            prompt: User prompt
            context: Optional prior conversation messages
                (`[{"role": ..., "content": ...}, ...]`)

        Returns:
            Generated response text
        """
        raise NotImplementedError

    @abstractmethod
    def stream_generate(
        self, prompt: str, context: Optional[list] = None
    ) -> Generator[str, None, None]:
        """
        Generate a streaming response.

        Args:
            prompt: User prompt
            context: Optional prior conversation messages

        Yields:
            Response text chunks
        """
        raise NotImplementedError

    def generate_with_tools(
        self,
        prompt: str,
        context: Optional[list] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ToolCallResult:
        """
        Generate a response, allowing the model to request structured tool
        calls instead of (or alongside) plain text, when supported.

        Providers with `supports_tools = True` must override this to use
        their native function/tool-calling API (see
        `coding_agent.llm.tool_schemas.TOOL_DEFINITIONS` for the shared
        schema). The default implementation here is a plain-text fallback
        used by providers that don't support tool-calling: it just calls
        `generate()` and returns the text with no tool calls, so
        `CodingAgent` can fall back to text-format regex parsing.

        Args:
            prompt: User prompt
            context: Optional prior conversation messages
            tools: JSON-schema tool definitions the model may call

        Returns:
            A `ToolCallResult` with either plain text or structured tool calls
        """
        return ToolCallResult(text=self.generate(prompt, context))

