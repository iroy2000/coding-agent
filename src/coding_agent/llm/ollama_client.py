"""Ollama client for LLM integration."""

from typing import Generator, Optional

import ollama
from rich.console import Console

console = Console()


class OllamaClient:
    """Client for interacting with Ollama."""

    def __init__(self, host: str = "http://localhost:11434", model: str = "codellama:latest") -> None:
        """
        Initialize Ollama client.

        Args:
            host: Ollama server host URL
            model: Model name to use
        """
        self.host = host
        self.model = model
        self.client = ollama.Client(host=host)

    def check_connection(self) -> bool:
        """
        Check if Ollama server is accessible.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to list models as a connectivity test
            self.client.list()
            return True
        except Exception as e:
            console.print(f"[red]Failed to connect to Ollama at {self.host}[/red]")
            console.print(f"[dim]Error: {str(e)}[/dim]")
            return False

    def list_models(self) -> list[str]:
        """
        List available models.

        Returns:
            List of model names
        """
        try:
            response = self.client.list()
            # Handle ListResponse object (Pydantic model)
            if hasattr(response, "models"):
                # Response is a ListResponse object with models attribute
                models = [model.model for model in response.models if hasattr(model, "model")]
                return models
            # Fallback for dict format (older versions)
            elif isinstance(response, dict) and "models" in response:
                models = [model.get("name", model.get("model", "")) for model in response["models"]]
                return [m for m in models if m]  # Filter out empty strings
            return []
        except Exception as e:
            console.print(f"[red]Failed to list models: {str(e)}[/red]")
            return []

    def check_model_exists(self, model_name: Optional[str] = None) -> bool:
        """
        Check if a specific model exists.

        Args:
            model_name: Model name to check (uses default if None)

        Returns:
            True if model exists, False otherwise
        """
        check_model = model_name or self.model
        models = self.list_models()

        # Check for exact match or base model match
        for model in models:
            if model == check_model or model.startswith(check_model.split(":")[0]):
                return True

        return False

    def pull_model(self, model_name: Optional[str] = None) -> bool:
        """
        Pull a model from Ollama.

        Args:
            model_name: Model name to pull (uses default if None)

        Returns:
            True if successful, False otherwise
        """
        pull_model = model_name or self.model

        try:
            console.print(f"[yellow]Pulling model: {pull_model}...[/yellow]")
            console.print("[dim]This may take a while for large models...[/dim]")

            # Pull the model with progress
            for progress in self.client.pull(pull_model, stream=True):
                status = progress.get("status", "")
                if status:
                    console.print(f"[dim]{status}[/dim]", end="\r")

            console.print(f"\n[green]Successfully pulled model: {pull_model}[/green]")
            return True
        except Exception as e:
            console.print(f"\n[red]Failed to pull model: {str(e)}[/red]")
            return False

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
            messages = context or []
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat(model=self.model, messages=messages)
            return response["message"]["content"]
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
            messages = context or []
            messages.append({"role": "user", "content": prompt})

            stream = self.client.chat(model=self.model, messages=messages, stream=True)

            for chunk in stream:
                if "message" in chunk and "content" in chunk["message"]:
                    yield chunk["message"]["content"]
        except Exception as e:
            console.print(f"[red]Streaming failed: {str(e)}[/red]")
            yield ""


def test_ollama_connection(host: str, model: str) -> tuple[bool, str]:
    """
    Test Ollama connection and model availability.

    Args:
        host: Ollama server host URL
        model: Model name to check

    Returns:
        Tuple of (success, message)
    """
    client = OllamaClient(host=host, model=model)

    # Check connection
    if not client.check_connection():
        return False, f"Cannot connect to Ollama at {host}. Is Ollama running?"

    # Check if model exists
    if not client.check_model_exists():
        available_models = client.list_models()
        if available_models:
            return (
                False,
                f"Model '{model}' not found. Available models: {', '.join(available_models[:5])}",
            )
        else:
            return False, f"Model '{model}' not found. Try pulling it with: ollama pull {model}"

    return True, f"Successfully connected to Ollama with model '{model}'"
