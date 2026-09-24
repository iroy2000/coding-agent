"""Anthropic client for LLM integration.

Implements the shared `LLMProvider` interface (see `coding_agent.llm.base`)
using the official `anthropic` Python SDK.

Anthropic's Messages API takes the system prompt as a separate top-level
`system=` parameter rather than as a `{"role": "system", ...}` entry inside
`messages` (unlike Ollama/OpenAI's chat-completions-style APIs), so this
provider splits it out of the shared context format before calling the API.
"""

from typing import Any, Dict, Generator, List, Optional, Tuple

from rich.console import Console

from coding_agent.llm.base import LLMProvider, ToolCall, ToolCallResult

console = Console()

# A conservative, non-exhaustive list of commonly used models, shown to the
# user for reference only. Anthropic doesn't expose a public "list models"
# API endpoint the way OpenAI does.
_KNOWN_MODELS = [
    "claude-3-5-sonnet-latest",
    "claude-3-5-haiku-latest",
    "claude-3-opus-latest",
]


def _split_system_and_messages(
    context: Optional[list], prompt: str
) -> Tuple[Optional[str], List[dict]]:
    """
    Split the shared `[{"role": ..., "content": ...}, ...]` context format
    into Anthropic's (system_prompt, messages) shape.

    Args:
        context: Optional prior conversation messages, which may start with
            a `{"role": "system", ...}` entry
        prompt: The current user prompt to append as the final message

    Returns:
        Tuple of (system_prompt or None, messages list with only
        user/assistant roles)
    """
    system_parts = []
    messages = []

    for msg in context or []:
        if msg.get("role") == "system":
            system_parts.append(msg.get("content", ""))
        else:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": prompt})

    system_prompt = "\n\n".join(p for p in system_parts if p) or None
    return system_prompt, messages


class AnthropicProvider(LLMProvider):
    """Client for interacting with Anthropic's Messages API."""

    provider_name = "anthropic"
    supports_tools = True

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-latest",
        max_tokens: int = 4096,
    ) -> None:
        """
        Initialize the Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model name to use (e.g. "claude-3-5-sonnet-latest")
            max_tokens: Maximum tokens to generate per response (required by
                Anthropic's API, unlike Ollama/OpenAI where it's optional)

        Raises:
            ImportError: If the optional `anthropic` package is not installed.
        """
        try:
            import anthropic
        except ImportError as e:
            raise ImportError(
                "The 'anthropic' package is required to use the Anthropic provider. "
                "Install it with: pip install anthropic"
            ) from e

        self.model = model
        self.max_tokens = max_tokens
        self.client = anthropic.Anthropic(api_key=api_key)
        self._not_given = anthropic.NOT_GIVEN

    def check_connection(self) -> bool:
        """
        Check that the API key is valid with a minimal request.

        Anthropic has no dedicated "ping"/"list models" endpoint, so this
        sends the smallest possible message request instead.

        Returns:
            True if the API responded successfully.
        """
        try:
            self.client.messages.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            return True
        except Exception as e:
            console.print("[red]Failed to connect to Anthropic[/red]")
            console.print(f"[dim]Error: {str(e)}[/dim]")
            return False

    def list_models(self) -> List[str]:
        """
        Return a small reference list of commonly used model names.

        Anthropic does not expose a public models-listing API, so unlike
        Ollama/OpenAI this cannot be a live lookup.

        Returns:
            A short, hardcoded reference list of model names.
        """
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
            system_prompt, messages = _split_system_and_messages(context, prompt)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=messages,
                system=system_prompt or self._not_given,
            )
            return "".join(
                getattr(block, "text", "")
                for block in response.content
                if getattr(block, "type", None) == "text"
            )
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
            system_prompt, messages = _split_system_and_messages(context, prompt)

            with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=messages,
                system=system_prompt or self._not_given,
            ) as stream:
                for text in stream.text_stream:
                    yield text
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
        Generate a response using Anthropic's native tool-use API.

        Args:
            prompt: User prompt
            context: Optional conversation context
            tools: JSON-schema tool definitions (see
                `coding_agent.llm.tool_schemas.TOOL_DEFINITIONS`). Anthropic
                expects each tool's schema under an `input_schema` key
                rather than `parameters`, so it's translated here.

        Returns:
            A `ToolCallResult` with either plain text or structured tool calls
        """
        try:
            system_prompt, messages = _split_system_and_messages(context, prompt)

            anthropic_tools = [
                {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "input_schema": tool["parameters"],
                }
                for tool in (tools or [])
            ]

            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=messages,
                system=system_prompt or self._not_given,
                tools=anthropic_tools or self._not_given,
            )

            text_parts = []
            tool_calls = []
            for block in response.content:
                block_type = getattr(block, "type", None)
                if block_type == "text":
                    text_parts.append(getattr(block, "text", ""))
                elif block_type == "tool_use":
                    tool_calls.append(
                        ToolCall(
                            name=getattr(block, "name", ""),
                            arguments=getattr(block, "input", {}) or {},
                            id=getattr(block, "id", None),
                        )
                    )

            return ToolCallResult(text="".join(text_parts), tool_calls=tool_calls)
        except Exception as e:
            console.print(f"[red]Generation failed: {str(e)}[/red]")
            return ToolCallResult(text="")


def test_anthropic_connection(api_key: Optional[str], model: str) -> tuple[bool, str]:
    """
    Test Anthropic API key validity and basic connectivity.

    Args:
        api_key: Anthropic API key (may be None/empty if not configured)
        model: Model name to use

    Returns:
        Tuple of (success, message)
    """
    if not api_key:
        return False, "ANTHROPIC_API_KEY is not set. Get one at https://console.anthropic.com/"

    try:
        client = AnthropicProvider(api_key=api_key, model=model)
    except ImportError as e:
        return False, str(e)

    if not client.check_connection():
        return False, "Cannot connect to Anthropic. Check your ANTHROPIC_API_KEY and network connection."

    return True, f"Successfully connected to Anthropic with model '{model}'"
