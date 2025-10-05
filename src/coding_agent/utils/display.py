"""Display utilities for Rich output formatting."""

from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

console = Console()


def print_user_message(message: str) -> None:
    """
    Print a user message.

    Args:
        message: User's message
    """
    console.print(f"[bold cyan]You:[/bold cyan] {message}")


def print_agent_message(message: str) -> None:
    """
    Print an agent message.

    Args:
        message: Agent's message
    """
    console.print(f"[bold green]Agent:[/bold green] {message}")


def print_system_message(message: str) -> None:
    """
    Print a system message.

    Args:
        message: System message
    """
    console.print(f"[yellow]{message}[/yellow]")


def print_error_message(message: str) -> None:
    """
    Print an error message.

    Args:
        message: Error message
    """
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_success_message(message: str) -> None:
    """
    Print a success message.

    Args:
        message: Success message
    """
    console.print(f"[green]>[/green] {message}")


def print_file_operation(operation: str, path: str, status: str = "in_progress") -> None:
    """
    Print a file operation status.

    Args:
        operation: Operation type (e.g., "Reading", "Writing", "Editing")
        path: File path
        status: Status ("in_progress", "success", "error")
    """
    # File operation indicators
    indicators = {
        "success": ">",
        "error": "x",
        "info": "i",
        "warning": "!",
    }
    colors = {
        "in_progress": "blue",
        "success": "green",
        "error": "red"
    }
    
    icon = indicators.get(status, "•")
    color = colors.get(status, "white")
    
    console.print(f"[{color}]{icon}[/{color}] {operation} [cyan]{path}[/cyan]")


def print_code_block(code: str, language: str = "python", theme: str = "monokai") -> None:
    """
    Print a syntax-highlighted code block.

    Args:
        code: Code to display
        language: Programming language
        theme: Syntax highlighting theme
    """
    syntax = Syntax(code, language, theme=theme, line_numbers=True)
    console.print(syntax)


def print_markdown(text: str) -> None:
    """
    Print markdown formatted text.

    Args:
        text: Markdown text
    """
    md = Markdown(text)
    console.print(md)


def print_panel(content: str, title: Optional[str] = None, border_style: str = "blue") -> None:
    """
    Print content in a panel.

    Args:
        content: Content to display
        title: Optional panel title
        border_style: Border color
    """
    panel = Panel(content, title=title, border_style=border_style)
    console.print(panel)


def print_table(title: str, headers: list[str], rows: list[list[str]]) -> None:
    """
    Print a formatted table.

    Args:
        title: Table title
        headers: Column headers
        rows: Table rows
    """
    table = Table(title=title, show_header=True, header_style="bold cyan")
    
    for header in headers:
        table.add_column(header)
    
    for row in rows:
        table.add_row(*row)
    
    console.print(table)


def create_spinner(text: str = "Processing..."):
    """
    Create a progress spinner.

    Args:
        text: Spinner text

    Returns:
        Progress context manager
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    )


def print_welcome_message() -> None:
    """Print welcome message for chat mode."""
    welcome = """
[bold cyan]Welcome to Coding Agent CLI![/bold cyan]

[bold magenta]Made with Love by Roy[/bold magenta]

[dim cyan]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣴⠶⢦⣤⠶⠶⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣇⠀⠀⠁⠀⢀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢧⣄⠀⣠⠞⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⡀⠀⠉⠛⠃⣠⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡞⠉⠙⢳⣄⢀⡾⠁⠈⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⡄⠀⠀⠙⢿⡇⠀⢰⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⣦⡀⠀⠀⠹⣦⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢳⣄⠀⠀⠈⠻⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡞⠋⠛⢧⡀⠀⠀⠘⢷⡀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⡴⠾⣧⡀⠀⠀⠹⣦⠀⠀⠈⢿⡄⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣿⠀⠀⠈⠻⣄⠀⠀⠀⠀⠀⠀⠈⣷⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⢠⡟⠉⠛⢷⣄⠀⠀⠈⠀⠀⠀⠀⠀⠀⣰⠏⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⢷⡀⠀⠀⠉⠃⠀⠀⠀⠀⠀⠀⠀⣴⠏⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣦⡀⠀⠀⠀⠀⠀⠀⢀⣠⠞⠁⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⠶⣤⣤⣤⡤⠶⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/dim cyan]

[bold cyan]I'm your AI coding assistant.[/bold cyan] I can help you with:
• Generate code and scripts
• Review and refactor existing code
• Debug issues and explain errors
• Answer coding questions
• Read, write, and edit files in your workspace

[dim]Type your message and press Enter to start.
Type 'exit' or 'quit' to end the session.
Type 'help' for more commands.[/dim]
"""
    console.print(welcome)


def print_help_message() -> None:
    """Print help message with available commands."""
    help_text = """
[bold cyan]Available Commands:[/bold cyan]

[bold]Chat Commands:[/bold]
  [cyan]exit, quit[/cyan]     - End the chat session
  [cyan]clear[/cyan]          - Clear conversation history
  [cyan]help[/cyan]           - Show this help message
  [cyan]workspace[/cyan]      - Show workspace information
  [cyan]models[/cyan]         - List available Ollama models

[bold]Tips:[/bold]
• Be specific in your requests for better results
• You can ask me to read files, write code, or explain concepts
• I'll remember the context of our conversation

[bold]Examples:[/bold]
  "Read the config.py file and explain what it does"
  "Create a Python script that processes CSV files"
  "Refactor main.py to use async/await"
  "What's the difference between lists and tuples in Python?"
"""
    console.print(help_text)


def print_separator(char: str = "─", length: int = 50, color: str = "dim cyan") -> None:
    """
    Print a separator line.

    Args:
        char: Character to use for separator
        length: Length of separator
        color: Color of separator
    """
    console.print(f"[{color}]{char * length}[/{color}]")


def print_workspace_info(workspace_path: str, file_count: Optional[int] = None) -> None:
    """
    Print workspace information.

    Args:
        workspace_path: Path to workspace
        file_count: Number of files (optional)
    """
    info = f"[bold]Current Workspace:[/bold] [cyan]{workspace_path}[/cyan]"
    if file_count is not None:
        info += f"\n[bold]Files:[/bold] {file_count}"
    
    print_panel(info, title="Workspace Info", border_style="blue")


def stream_agent_response(text_generator) -> str:
    """
    Stream agent response with real-time display.

    Args:
        text_generator: Generator yielding text chunks

    Returns:
        Complete response text
    """
    console.print("[bold green]Agent:[/bold green] ", end="")
    
    full_response = ""
    for chunk in text_generator:
        if chunk:
            console.print(chunk, end="")
            full_response += chunk
    
    console.print()  # New line at the end
    return full_response


def print_file_list(files: list, title: str = "Files") -> None:
    """
    Print a list of files in a formatted table.

    Args:
        files: List of file paths
        title: Title for the list
    """
    if not files:
        console.print(f"[yellow]No files found[/yellow]")
        return

    # Group files by directory
    from collections import defaultdict
    files_by_dir = defaultdict(list)
    
    for file in files:
        if "/" in file:
            dir_name = "/".join(file.split("/")[:-1])
            file_name = file.split("/")[-1]
        else:
            dir_name = "."
            file_name = file
        files_by_dir[dir_name].append(file_name)

    # Display grouped files
    console.print(f"\n[bold cyan]{title}[/bold cyan] ([dim]{len(files)} files[/dim])")
    console.print()
    
    for dir_name in sorted(files_by_dir.keys()):
        if dir_name != ".":
            console.print(f"[blue]{dir_name}/[/blue]")
        for file_name in sorted(files_by_dir[dir_name]):
            console.print(f"  [dim]→[/dim] {file_name}")
        console.print()


def print_file_content(content: str, file_path: str, language: str = None, max_lines: int = None) -> None:
    """
    Print file content with syntax highlighting.

    Args:
        content: File content
        file_path: Path to the file (for language detection)
        language: Programming language (auto-detected if None)
        max_lines: Maximum number of lines to display (None for all)
    """
    # Auto-detect language from file extension
    if language is None:
        ext_to_lang = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "jsx",
            ".tsx": "tsx",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".cs": "csharp",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".html": "html",
            ".css": "css",
            ".json": "json",
            ".xml": "xml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".md": "markdown",
            ".sh": "bash",
            ".sql": "sql",
        }
        ext = "." + file_path.split(".")[-1] if "." in file_path else ""
        language = ext_to_lang.get(ext.lower(), "text")

    # Truncate if needed
    lines = content.split("\n")
    if max_lines and len(lines) > max_lines:
        content = "\n".join(lines[:max_lines])
        content += f"\n... ({len(lines) - max_lines} more lines)"

    # Print with syntax highlighting
    console.print(f"\n[bold cyan]File:[/bold cyan] [cyan]{file_path}[/cyan]")
    print_code_block(content, language=language)


def print_file_operation_result(success: bool, message: str, operation: str = "Operation") -> None:
    """
    Print the result of a file operation.

    Args:
        success: Whether the operation was successful
        message: Result message
        operation: Type of operation
    """
    if success:
        console.print(f"[green]>[/green] [bold]{operation}:[/bold] {message}")
    else:
        console.print(f"[red]x[/red] [bold]{operation} failed:[/bold] {message}")
