"""Configuration management for Coding Agent CLI."""

import os
from pathlib import Path
from typing import Optional

from dotenv import find_dotenv, load_dotenv
from rich.console import Console

console = Console()


class Config:
    """Configuration manager for the application."""

    def __init__(self) -> None:
        """Initialize configuration."""
        # Load .env file from the current working directory (not the
        # calling module's location), so real (non-editable) installs
        # correctly pick up a project-local .env file.
        load_dotenv(find_dotenv(usecwd=True))

        # User data directory
        self.user_data_dir = Path.home() / ".coding-agent"
        self.history_dir = self.user_data_dir / "history"

        # Ollama settings
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "codellama:latest")

        # LLM provider selection (ollama | openai | anthropic)
        self.llm_provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()

        # OpenAI settings (used when LLM_PROVIDER=openai)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Anthropic settings (used when LLM_PROVIDER=anthropic)
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")

        # Workspace settings
        self.workspace_path = Path(os.getenv("WORKSPACE_PATH", ".")).resolve()

        # History settings
        self.max_history_length = self._parse_int_env("MAX_HISTORY_LENGTH", 50)
        self.history_enabled = os.getenv("HISTORY_ENABLED", "true").lower() == "true"

        # Display settings
        self.show_spinner = os.getenv("SHOW_SPINNER", "true").lower() == "true"
        self.syntax_theme = os.getenv("SYNTAX_THEME", "monokai")

    @staticmethod
    def _parse_int_env(key: str, default: int) -> int:
        """
        Parse an integer environment variable, falling back to a default
        (with a warning) instead of raising if the value is malformed.

        This guards against a corrupted/hand-edited .env file (or a bad
        value written via `config --set`) permanently crashing the CLI on
        every subsequent invocation.
        """
        raw = os.getenv(key)
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError:
            console.print(
                f"[yellow]Warning: {key}={raw!r} is not a valid integer; "
                f"using default {default}[/yellow]"
            )
            return default

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[dim]User data directory: {self.user_data_dir}[/dim]")

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate configuration.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Validate LLM provider selection
        valid_providers = ("ollama", "openai", "anthropic")
        if self.llm_provider not in valid_providers:
            errors.append(
                f"LLM_PROVIDER must be one of {valid_providers}, got '{self.llm_provider}'"
            )
        elif self.llm_provider == "openai" and not self.openai_api_key:
            errors.append("OPENAI_API_KEY must be set when LLM_PROVIDER=openai")
        elif self.llm_provider == "anthropic" and not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY must be set when LLM_PROVIDER=anthropic")

        # Validate workspace path
        if not self.workspace_path.exists():
            errors.append(f"Workspace path does not exist: {self.workspace_path}")

        # Validate max history length
        if self.max_history_length < 1:
            errors.append(f"MAX_HISTORY_LENGTH must be at least 1, got {self.max_history_length}")

        return len(errors) == 0, errors

    def display(self) -> None:
        """Display current configuration."""
        from rich.table import Table

        table = Table(title="Current Configuration", show_header=True, header_style="bold cyan")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("LLM Provider", self.llm_provider)
        table.add_row("Ollama Host", self.ollama_host)
        table.add_row("Ollama Model", self.ollama_model)
        if self.llm_provider == "openai":
            table.add_row("OpenAI Model", self.openai_model)
            table.add_row("OpenAI API Key", "***set***" if self.openai_api_key else "(not set)")
        if self.llm_provider == "anthropic":
            table.add_row("Anthropic Model", self.anthropic_model)
            table.add_row(
                "Anthropic API Key", "***set***" if self.anthropic_api_key else "(not set)"
            )
        table.add_row("Workspace Path", str(self.workspace_path))
        table.add_row("Max History Length", str(self.max_history_length))
        table.add_row("History Enabled", str(self.history_enabled))
        table.add_row("Show Spinner", str(self.show_spinner))
        table.add_row("Syntax Theme", self.syntax_theme)
        table.add_row("User Data Directory", str(self.user_data_dir))

        console.print(table)

    def update(self, key: str, value: str) -> bool:
        """
        Update a configuration value.

        Args:
            key: Configuration key to update
            value: New value

        Returns:
            True if successful, False otherwise
        """
        # Map of valid keys to their attribute names
        valid_keys = {
            "OLLAMA_HOST": "ollama_host",
            "OLLAMA_MODEL": "ollama_model",
            "LLM_PROVIDER": "llm_provider",
            "OPENAI_API_KEY": "openai_api_key",
            "OPENAI_MODEL": "openai_model",
            "ANTHROPIC_API_KEY": "anthropic_api_key",
            "ANTHROPIC_MODEL": "anthropic_model",
            "WORKSPACE_PATH": "workspace_path",
            "MAX_HISTORY_LENGTH": "max_history_length",
            "HISTORY_ENABLED": "history_enabled",
            "SHOW_SPINNER": "show_spinner",
            "SYNTAX_THEME": "syntax_theme",
        }

        if key not in valid_keys:
            console.print(f"[red]Invalid configuration key: {key}[/red]")
            console.print(f"Valid keys: {', '.join(valid_keys.keys())}")
            return False

        # Validate the value before writing anything, so a bad value can
        # never reach the .env file and brick subsequent CLI invocations.
        if key == "MAX_HISTORY_LENGTH":
            try:
                parsed_length = int(value)
            except ValueError:
                console.print(f"[red]MAX_HISTORY_LENGTH must be an integer, got '{value}'[/red]")
                return False
            if parsed_length < 1:
                console.print(
                    f"[red]MAX_HISTORY_LENGTH must be at least 1, got {parsed_length}[/red]"
                )
                return False
        elif key == "LLM_PROVIDER":
            valid_providers = ("ollama", "openai", "anthropic")
            if value.strip().lower() not in valid_providers:
                console.print(
                    f"[red]LLM_PROVIDER must be one of {valid_providers}, got '{value}'[/red]"
                )
                return False

        # Update the environment variable
        os.environ[key] = value

        # Update .env file
        env_file = Path(".env")
        if env_file.exists():
            # Read existing content
            lines = env_file.read_text().splitlines()
            updated = False

            # Update existing key or add new one
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}"
                    updated = True
                    break

            if not updated:
                lines.append(f"{key}={value}")

            # Write back
            env_file.write_text("\n".join(lines) + "\n")
        else:
            # Create new .env file
            env_file.write_text(f"{key}={value}\n")

        # Reflect the change on this in-memory instance immediately, so a
        # subsequent display() in the same process shows the new value
        # instead of the stale one captured at __init__ time.
        attr_name = valid_keys[key]
        if key == "MAX_HISTORY_LENGTH":
            setattr(self, attr_name, int(value))
        elif key in ("HISTORY_ENABLED", "SHOW_SPINNER"):
            setattr(self, attr_name, value.strip().lower() == "true")
        elif key == "LLM_PROVIDER":
            setattr(self, attr_name, value.strip().lower())
        elif key == "WORKSPACE_PATH":
            setattr(self, attr_name, Path(value).resolve())
        else:
            setattr(self, attr_name, value)

        console.print(f"[green]Updated {key}={value}[/green]")
        console.print("[yellow]Restart the application for changes to take effect[/yellow]")
        return True


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance.

    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config() -> None:
    """Reset the global configuration instance."""
    global _config
    _config = None
