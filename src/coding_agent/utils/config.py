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
        # calling module's location or config.py's own file location, which
        # for editable/dev installs stays inside the coding-agent-cli repo
        # tree and would otherwise pick up the repo's own .env instead of
        # the target project's .env).
        load_dotenv(find_dotenv(usecwd=True))

        # User data directory
        self.user_data_dir = Path.home() / ".coding-agent"
        self.history_dir = self.user_data_dir / "history"

        # Ollama settings
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "codellama:latest")

        # Workspace settings
        self.workspace_path = Path(os.getenv("WORKSPACE_PATH", ".")).resolve()

        # History settings
        self.max_history_length = int(os.getenv("MAX_HISTORY_LENGTH", "50"))
        self.history_enabled = os.getenv("HISTORY_ENABLED", "true").lower() == "true"

        # Display settings
        self.show_spinner = os.getenv("SHOW_SPINNER", "true").lower() == "true"
        self.syntax_theme = os.getenv("SYNTAX_THEME", "monokai")

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

        table.add_row("Ollama Host", self.ollama_host)
        table.add_row("Ollama Model", self.ollama_model)
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
