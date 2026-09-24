"""Shared interface implemented by every LLM backend (Ollama, OpenAI, Anthropic, ...).

`CodingAgent` and the CLI only depend on this interface, never on a specific
provider's SDK, so adding a new backend means implementing this class and
wiring it into `coding_agent.llm.factory` - nothing else in the agent loop
needs to change.
"""

from abc import ABC, abstractmethod
from typing import Generator, List, Optional


class LLMProvider(ABC):
    """Abstract base class for a chat-capable LLM backend."""

    #: Human-readable provider name (e.g. "ollama", "openai", "anthropic"),
    #: used in error/status messages.
    provider_name: str = "unknown"

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
