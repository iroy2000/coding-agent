"""OpenAI client for LLM integration.

Implements the shared `LLMProvider` interface (see `coding_agent.llm.base`)
using the official `openai` Python SDK, so the agent/CLI can use OpenAI's
hosted models exactly like Ollama.
"""

import json
from typing import Any, Dict, Generator, List, Optional

from rich.console import Console

from coding_agent.llm.base import LLMProvider, ToolCall, ToolCallResult

console = Console()

# A conservative, non-exhaustive list of commonly used chat models, shown to
# the user for reference only (OpenAI has no simple "list installed models"
# concept the way Ollama does - `list_models()` below queries the real API).
_KNOWN_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]


class OpenAIProvider(LLMProvider):
    """Client for interacting with OpenAI's chat completions API."""

    provider_name = "openai"
    supports_tools = True

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        """
        Initialize the OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model name to use (e.g. "gpt-4o-mini")

        Raises:
            ImportError: If the optional `openai` package is not installed.
        """
        try:
            import openai
        except ImportError as e:
            raise ImportError(
                "The 'openai' package is required to use the OpenAI provider. "
                "Install it with: pip install openai"
            ) from e

        self.model = model
        self.client = openai.OpenAI(api_key=api_key)

    def check_connection(self) -> bool:
        """
        Check that the API key is valid by listing models.

        Returns:
            True if the API responded successfully.
        """
        try:
            self.client.models.list()
            return True
        except Exception as e:
            console.print("[red]Failed to connect to OpenAI[/red]")
            console.print(f"[dim]Error: {str(e)}[/dim]")
            return False

    def list_models(self) -> List[str]:
        """
        List models available to this API key.

        Returns:
            List of model names, or a small hardcoded reference list if the
            API call fails (e.g. network issue).
        """
        try:
            response = self.client.models.list()
            return [m.id for m in response.data]
        except Exception:
            return list(_KNOWN_MODELS)

    def generate(self, prompt: str, context: Optional[list] = None) -> str:
        """
        Generate a response from the model.

        Args:
            prompt: User prompt
            context: Optional conversation context

        Returns:
            Generated response text
        """
        try:
            messages = list(context or [])
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model, messages=messages
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            console.print(f"[red]Generation failed: {str(e)}[/red]")
            return ""

    def stream_generate(
        self, prompt: str, context: Optional[list] = None
    ) -> Generator[str, None, None]:
        """
        Generate a streaming response from the model.

        Args:
            prompt: User prompt
            context: Optional conversation context

        Yields:
            Response chunks
        """
        try:
            messages = list(context or [])
            messages.append({"role": "user", "content": prompt})

            stream = self.client.chat.completions.create(
                model=self.model, messages=messages, stream=True
            )

            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            console.print(f"[red]Streaming failed: {str(e)}[/red]")
            yield ""

    def generate_with_tools(
        self,
        prompt: str,
        context: Optional[list] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ToolCallResult:
        """
        Generate a response using OpenAI's native function-calling API.

        Args:
            prompt: User prompt
            context: Optional conversation context
            tools: JSON-schema tool definitions (see
                `coding_agent.llm.tool_schemas.TOOL_DEFINITIONS`)

        Returns:
            A `ToolCallResult` with either plain text or structured tool calls
        """
        try:
            messages = list(context or [])
            messages.append({"role": "user", "content": prompt})

            openai_tools = [
                {"type": "function", "function": tool} for tool in (tools or [])
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=openai_tools or None,
            )
            message = response.choices[0].message

            tool_calls = []
            for call in message.tool_calls or []:
                try:
                    arguments = json.loads(call.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    arguments = {}
                tool_calls.append(
                    ToolCall(name=call.function.name, arguments=arguments, id=call.id)
                )

            return ToolCallResult(text=message.content or "", tool_calls=tool_calls)
        except Exception as e:
            console.print(f"[red]Generation failed: {str(e)}[/red]")
            return ToolCallResult(text="")


def test_openai_connection(api_key: Optional[str], model: str) -> tuple[bool, str]:
    """
    Test OpenAI API key validity and basic connectivity.

    Args:
        api_key: OpenAI API key (may be None/empty if not configured)
        model: Model name to use

    Returns:
        Tuple of (success, message)
    """
    if not api_key:
        return False, "OPENAI_API_KEY is not set. Get one at https://platform.openai.com/api-keys"

    try:
        client = OpenAIProvider(api_key=api_key, model=model)
    except ImportError as e:
        return False, str(e)

    if not client.check_connection():
        return False, "Cannot connect to OpenAI. Check your OPENAI_API_KEY and network connection."

    return True, f"Successfully connected to OpenAI with model '{model}'"
