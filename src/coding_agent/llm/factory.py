"""Factory for constructing the configured `LLMProvider` backend.

This is the single place that knows how to turn `Config.llm_provider`
("ollama" | "openai" | "anthropic") into a concrete provider instance, so
`CodingAgent` and the CLI commands never need to branch on provider name
themselves.
"""

from typing import Tuple

from coding_agent.llm.base import LLMProvider
from coding_agent.utils.config import Config

SUPPORTED_PROVIDERS = ("ollama", "openai", "anthropic")


def create_llm_client(config: Config) -> LLMProvider:
    """
    Construct the `LLMProvider` selected by `config.llm_provider`.

    Args:
        config: A `coding_agent.utils.config.Config` instance

    Returns:
        A concrete `LLMProvider` instance for the configured backend

    Raises:
        ValueError: If `config.llm_provider` isn't a supported provider name
        ImportError: If the provider's optional SDK package isn't installed
    """
    provider = config.llm_provider

    if provider == "ollama":
        from coding_agent.llm.ollama_client import OllamaClient

        return OllamaClient(host=config.ollama_host, model=config.ollama_model)

    if provider == "openai":
        from coding_agent.llm.openai_client import OpenAIProvider

        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set to use the openai provider")
        return OpenAIProvider(api_key=config.openai_api_key, model=config.openai_model)

    if provider == "anthropic":
        from coding_agent.llm.anthropic_client import AnthropicProvider

        if not config.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set to use the anthropic provider")
        return AnthropicProvider(api_key=config.anthropic_api_key, model=config.anthropic_model)

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider}'. Supported providers: {', '.join(SUPPORTED_PROVIDERS)}"
    )


def get_active_model(config: Config) -> str:
    """
    Get the model name for whichever provider is currently configured.

    Args:
        config: A `coding_agent.utils.config.Config` instance

    Returns:
        The model name string for the active provider
    """
    if config.llm_provider == "openai":
        return config.openai_model
    if config.llm_provider == "anthropic":
        return config.anthropic_model
    return config.ollama_model


def test_llm_connection(config: Config) -> Tuple[bool, str]:
    """
    Test connectivity for whichever provider is currently configured.

    Args:
        config: A `coding_agent.utils.config.Config` instance

    Returns:
        Tuple of (success, message)
    """
    provider = config.llm_provider

    if provider == "ollama":
        from coding_agent.llm.ollama_client import test_ollama_connection

        return test_ollama_connection(config.ollama_host, config.ollama_model)

    if provider == "openai":
        from coding_agent.llm.openai_client import test_openai_connection

        return test_openai_connection(config.openai_api_key, config.openai_model)

    if provider == "anthropic":
        from coding_agent.llm.anthropic_client import test_anthropic_connection

        return test_anthropic_connection(config.anthropic_api_key, config.anthropic_model)

    return (
        False,
        f"Unknown LLM_PROVIDER '{provider}'. Supported providers: {', '.join(SUPPORTED_PROVIDERS)}",
    )
