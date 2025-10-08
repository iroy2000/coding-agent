"""CLI interface for the coding agent."""

import typer
from rich.console import Console

app = typer.Typer(
    name="coding-agent",
    help="An interactive coding assistant powered by local LLMs",
    add_completion=False,
)
console = Console()


@app.command()
def chat() -> None:
    """Start an interactive chat session with the coding agent."""
    from rich.prompt import Prompt

    from coding_agent.agent import CodingAgent
    from coding_agent.llm.ollama_client import OllamaClient
    from coding_agent.utils.config import get_config
    from coding_agent.utils.display import (
        print_error_message,
        print_help_message,
        print_user_message,
        print_welcome_message,
        print_workspace_info,
    )

    # Load configuration
    config = get_config()
    
    # Initialize Ollama client for connection check
    client = OllamaClient(host=config.ollama_host, model=config.ollama_model)
    
    # Check connection
    if not client.check_connection():
        print_error_message(f"Cannot connect to Ollama at {config.ollama_host}")
        console.print("\nPlease make sure:")
        console.print("1. Ollama is installed and running")
        console.print("2. Run: [cyan]coding-agent init[/cyan] to verify setup")
        raise typer.Exit(1)
    
    # Check model availability
    if not client.check_model_exists():
        print_error_message(f"Model '{config.ollama_model}' not found")
        available = client.list_models()
        if available:
            console.print(f"\nAvailable models: {', '.join(available[:5])}")
        console.print(f"\nTo pull the model, run: [cyan]ollama pull {config.ollama_model}[/cyan]")
        raise typer.Exit(1)
    
    # Initialize agent with history enabled
    agent = CodingAgent(
        workspace_path=str(config.workspace_path),
        ollama_host=config.ollama_host,
        model=config.ollama_model,
        max_history=config.max_history_length,
        enable_history=config.history_enabled,
    )
    
    # Print welcome message
    print_welcome_message()
    workspace_info = agent.get_workspace_info()
    print_workspace_info(workspace_info["path"], workspace_info["file_count"])
    
    # Show session ID if history is enabled
    if agent.session_id:
        console.print(f"[dim]Session ID: {agent.session_id}[/dim]")
    
    console.print()
    
    # Chat loop
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            
            if not user_input.strip():
                continue
            
            # Handle commands
            if user_input.lower() in ["exit", "quit"]:
                if agent.session_id:
                    console.print(f"[dim]Session saved: {agent.session_id}[/dim]")
                console.print("\n[yellow]Goodbye![/yellow]")
                break
            
            if user_input.lower() == "help":
                print_help_message()
                continue
            
            if user_input.lower() == "clear":
                agent.clear_history()
                continue
            
            if user_input.lower() == "workspace":
                workspace_info = agent.get_workspace_info()
                print_workspace_info(workspace_info["path"], workspace_info["file_count"])
                continue
            
            if user_input.lower() == "models":
                models = client.list_models()
                if models:
                    console.print("\n[bold]Available Models:[/bold]")
                    for model in models:
                        marker = " [green](current)[/green]" if model == config.ollama_model else ""
                        console.print(f"  • {model}{marker}")
                else:
                    console.print("[yellow]No models found[/yellow]")
                continue
            
            # Process message through agent
            try:
                agent.process_message(user_input, stream=True)
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Response interrupted[/yellow]")
                continue
            except Exception as e:
                print_error_message(f"Failed to generate response: {str(e)}")
                continue
                
        except KeyboardInterrupt:
            if agent.session_id:
                console.print(f"\n[dim]Session saved: {agent.session_id}[/dim]")
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except EOFError:
            if agent.session_id:
                console.print(f"\n[dim]Session saved: {agent.session_id}[/dim]")
            console.print("\n[yellow]Goodbye![/yellow]")
            break


@app.command()
def init() -> None:
    """Initialize configuration for the coding agent."""
    from rich.panel import Panel
    from rich.prompt import Confirm

    from coding_agent.llm.ollama_client import test_ollama_connection
    from coding_agent.utils.config import get_config

    console.print(Panel.fit(
        "[bold cyan]Coding Agent CLI - Initialization[/bold cyan]",
        border_style="cyan"
    ))

    # Load configuration
    config = get_config()

    # Create necessary directories
    console.print("\n[bold]Setting up directories...[/bold]")
    config.ensure_directories()
    console.print("[green]>[/green] Directories created")

    # Validate configuration
    console.print("\n[bold]Validating configuration...[/bold]")
    is_valid, errors = config.validate()

    if not is_valid:
        console.print("[yellow]Configuration warnings:[/yellow]")
        for error in errors:
            console.print(f"  [yellow]•[/yellow] {error}")
    else:
        console.print("[green]>[/green] Configuration is valid")

    # Test Ollama connection
    console.print("\n[bold]Testing Ollama connection...[/bold]")
    success, message = test_ollama_connection(config.ollama_host, config.ollama_model)

    if success:
        console.print(f"[green]>[/green] {message}")
    else:
        console.print(f"[red]x[/red] {message}")
        console.print("\n[yellow]Ollama Setup Instructions:[/yellow]")
        console.print("1. Install Ollama: https://ollama.com")
        console.print(f"2. Pull the model: [cyan]ollama pull {config.ollama_model}[/cyan]")
        console.print(f"3. Or choose a different model in .env file")

        if not Confirm.ask("\nContinue anyway?", default=False):
            raise typer.Exit(1)

    # Display configuration
    console.print("\n[bold]Current Configuration:[/bold]")
    config.display()

    console.print("\n[green]>[/green] Initialization complete!")
    console.print("\nYou can now start using: [cyan]coding-agent chat[/cyan]")


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    set_value: str = typer.Option(None, "--set", help="Set configuration value (KEY=VALUE)"),
) -> None:
    """View or update configuration settings."""
    from coding_agent.utils.config import get_config

    cfg = get_config()

    if show:
        cfg.display()
    elif set_value:
        # Parse KEY=VALUE
        if "=" not in set_value:
            console.print("[red]Invalid format. Use: --set KEY=VALUE[/red]")
            console.print("Example: [cyan]coding-agent config --set OLLAMA_MODEL=deepseek-coder[/cyan]")
            raise typer.Exit(1)

        key, value = set_value.split("=", 1)
        key = key.strip()
        value = value.strip()

        if cfg.update(key, value):
            console.print("\n[bold]Updated configuration:[/bold]")
            cfg.display()
        else:
            raise typer.Exit(1)
    else:
        console.print("Use [cyan]--show[/cyan] to view config or [cyan]--set KEY=VALUE[/cyan] to update")
        console.print("\nExamples:")
        console.print("  [dim]coding-agent config --show[/dim]")
        console.print("  [dim]coding-agent config --set OLLAMA_MODEL=deepseek-coder[/dim]")
        console.print("  [dim]coding-agent config --set MAX_HISTORY_LENGTH=100[/dim]")


@app.command()
def history(
    list_sessions: bool = typer.Option(False, "--list", help="List all conversation sessions"),
    view: str = typer.Option(None, "--view", help="View specific session by ID"),
    delete: str = typer.Option(None, "--delete", help="Delete session by ID"),
    export: str = typer.Option(None, "--export", help="Export session by ID"),
    output: str = typer.Option(None, "--output", help="Output file for export"),
    format: str = typer.Option("md", "--format", help="Export format (json/txt/md)"),
    limit: int = typer.Option(20, "--limit", help="Number of sessions to list"),
) -> None:
    """View conversation history."""
    from coding_agent.storage.history import HistoryManager
    from rich.table import Table
    
    history_mgr = HistoryManager()
    
    if list_sessions:
        sessions = history_mgr.list_sessions(limit=limit)
        
        if not sessions:
            console.print("[yellow]No conversation sessions found[/yellow]")
            return
        
        table = Table(title=f"Recent Conversation Sessions (showing {len(sessions)})", 
                     show_header=True, header_style="bold cyan")
        table.add_column("Session ID", style="cyan")
        table.add_column("Created", style="white")
        table.add_column("Workspace", style="dim", no_wrap=True)
        table.add_column("Messages", justify="right", style="green")
        
        for session in sessions:
            # Format workspace path (show last 2 parts)
            workspace = session.get("workspace_path", "")
            workspace_short = "/".join(workspace.split("/")[-2:]) if "/" in workspace else workspace
            
            # Format date
            created = session.get("created_at", "")
            if created:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(created)
                    created_fmt = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    created_fmt = created[:16]
            else:
                created_fmt = "Unknown"
            
            table.add_row(
                session.get("session_id", ""),
                created_fmt,
                workspace_short,
                str(session.get("message_count", 0))
            )
        
        console.print(table)
        console.print(f"\n[dim]Use --view SESSION_ID to view details[/dim]")
        
    elif view:
        session_data = history_mgr.load_session(view)
        
        if not session_data:
            console.print(f"[red]Session '{view}' not found[/red]")
            return
        
        # Display session info
        from rich.panel import Panel
        
        info = f"""[bold]Session ID:[/bold] {session_data.get('session_id')}
[bold]Created:[/bold] {session_data.get('created_at')}
[bold]Workspace:[/bold] {session_data.get('workspace_path')}
[bold]Model:[/bold] {session_data.get('model')}
[bold]Messages:[/bold] {len(session_data.get('messages', []))}"""
        
        console.print(Panel(info, title="Session Details", border_style="cyan"))
        
        # Display messages
        messages = session_data.get("messages", [])
        if messages:
            console.print(f"\n[bold]Conversation:[/bold]\n")
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                
                if role == "user":
                    console.print(f"[bold cyan]You:[/bold cyan] {content}\n")
                elif role == "assistant":
                    console.print(f"[bold green]Agent:[/bold green] {content}\n")
                else:
                    console.print(f"[dim]{role}:[/dim] {content}\n")
    
    elif delete:
        if history_mgr.delete_session(delete):
            console.print(f"[green]>[/green] Session '{delete}' deleted")
        else:
            console.print(f"[red]Failed to delete session '{delete}'[/red]")
    
    elif export:
        if not output:
            output = f"session_{export}.{format}"
        
        if history_mgr.export_session(export, output, format=format):
            console.print(f"[green]>[/green] Session exported to: {output}")
        else:
            console.print(f"[red]Failed to export session '{export}'[/red]")
    
    else:
        console.print("[bold]Conversation History[/bold]\n")
        console.print("Available commands:")
        console.print("  [cyan]--list[/cyan]              List all conversation sessions")
        console.print("  [cyan]--view SESSION_ID[/cyan]   View a specific session")
        console.print("  [cyan]--delete SESSION_ID[/cyan] Delete a session")
        console.print("  [cyan]--export SESSION_ID[/cyan] Export a session")
        console.print("  [cyan]--limit N[/cyan]           Limit number of sessions to show (default: 20)")
        console.print("\nExport options:")
        console.print("  [cyan]--output FILE[/cyan]      Output file path")
        console.print("  [cyan]--format FORMAT[/cyan]    Format: json, txt, or md (default: md)")


@app.command()
def serve(
    workspace: str = typer.Option(
        ".",
        "--workspace",
        "-w",
        help="Workspace directory for file operations"
    ),
    transport: str = typer.Option(
        "stdio",
        "--transport",
        "-t",
        help="Transport mode: stdio (for Claude Desktop) or http"
    ),
    enable_file_tools: bool = typer.Option(
        True,
        "--enable-file-tools/--no-file-tools",
        help="Enable file operation tools (read, list)"
    ),
    enable_ai_tools: bool = typer.Option(
        True,
        "--enable-ai-tools/--no-ai-tools",
        help="Enable AI tools (explain code)"
    ),
    enable_history_tools: bool = typer.Option(
        False,
        "--enable-history-tools/--no-history-tools",
        help="Enable history tools (disabled in Safe Mode by default)"
    ),
    safe_mode: bool = typer.Option(
        True,
        "--safe-mode/--no-safe-mode",
        help="Use Safe Mode defaults (read-only, explain-only, no history)"
    ),
) -> None:
    """
    Start MCP server to expose coding-agent tools to external clients.
    
    This allows other applications (like Claude Desktop) to use your
    coding-agent's file operations, AI capabilities, and history.
    
    Examples:
    
        # Start with Safe Mode defaults (recommended)
        coding-agent serve
        
        # Serve specific workspace
        coding-agent serve --workspace /path/to/project
        
        # Enable all tools including history
        coding-agent serve --enable-history-tools --no-safe-mode
        
        # Disable Safe Mode for full access
        coding-agent serve --no-safe-mode
    
    For Claude Desktop integration, add this to your Claude config:
    
        {
          "mcpServers": {
            "coding-agent": {
              "command": "coding-agent",
              "args": ["serve", "--workspace", "/your/project/path"]
            }
          }
        }
    """
    import asyncio
    from pathlib import Path
    from coding_agent.mcp.server import MCPServer
    from coding_agent.utils.display import print_error_message
    
    try:
        # Resolve workspace path
        workspace_path = Path(workspace).resolve()
        
        if not workspace_path.exists():
            print_error_message(f"Workspace path does not exist: {workspace}")
            raise typer.Exit(1)
        
        # Display startup info
        console.print("\n[bold cyan]═══ MCP Server Starting ═══[/bold cyan]\n")
        console.print(f"[dim]Workspace:[/dim] {workspace_path}")
        console.print(f"[dim]Transport:[/dim] {transport}")
        console.print(f"[dim]Safe Mode:[/dim] {'✅ Enabled' if safe_mode else '❌ Disabled'}")
        console.print()
        
        # Show enabled tools
        console.print("[bold]Enabled Tools:[/bold]")
        if enable_file_tools:
            console.print("  ✅ File tools: [cyan]read_file, list_files[/cyan]")
        if enable_ai_tools:
            console.print("  ✅ AI tools: [cyan]explain_code[/cyan]")
        if enable_history_tools:
            console.print("  ✅ History tools: [cyan]search_history[/cyan]")
        
        if not any([enable_file_tools, enable_ai_tools, enable_history_tools]):
            print_error_message("No tools enabled! Enable at least one tool category.")
            raise typer.Exit(1)
        
        console.print()
        
        # Create server
        if safe_mode:
            server = MCPServer.with_safe_mode(workspace_path=str(workspace_path))
        else:
            server = MCPServer(
                workspace_path=str(workspace_path),
                enable_file_tools=enable_file_tools,
                enable_ai_tools=enable_ai_tools,
                enable_history_tools=enable_history_tools,
            )
        
        # Show registered tools
        tools = server.list_tools()
        console.print(f"[bold green]✓[/bold green] Server initialized with {len(tools)} tool(s)")
        for tool in tools:
            console.print(f"  • {tool['name']}: [dim]{tool['description']}[/dim]")
        
        console.print()
        console.print("[bold yellow]Server running...[/bold yellow] Press Ctrl+C to stop")
        console.print()
        
        # Start server based on transport
        if transport == "stdio":
            # Run MCP stdio server
            try:
                from coding_agent.mcp.stdio_server import run_stdio_server
                
                # Build kwargs for non-safe-mode
                kwargs = {}
                if not safe_mode:
                    kwargs = {
                        "enable_file_tools": enable_file_tools,
                        "enable_ai_tools": enable_ai_tools,
                        "enable_history_tools": enable_history_tools,
                    }
                
                # Run the async server
                asyncio.run(run_stdio_server(
                    workspace_path=str(workspace_path),
                    safe_mode=safe_mode,
                    **kwargs
                ))
            except KeyboardInterrupt:
                console.print("\n\n[yellow]Server stopped[/yellow]")
                
        elif transport == "http":
            print_error_message("HTTP transport not yet implemented")
            console.print("[dim]Currently only stdio transport is supported[/dim]")
            raise typer.Exit(1)
        else:
            print_error_message(f"Unknown transport: {transport}")
            console.print("[dim]Supported transports: stdio, http[/dim]")
            raise typer.Exit(1)
            
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Server stopped by user[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        print_error_message(f"Server error: {e}")
        raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit"
    ),
) -> None:
    """
    Coding Agent CLI
    
    An interactive coding assistant powered by local LLMs via Ollama.
    """
    if version:
        from coding_agent import __version__
        from rich.panel import Panel
        from rich.text import Text
        
        title = Text()
        title.append("Coding Agent CLI", style="bold magenta")
        
        version_text = Text()
        version_text.append("Version: ", style="bold green")
        version_text.append(f"v{__version__}", style="bold yellow")
        version_text.append("\n")
        version_text.append("Powered by ", style="dim")
        version_text.append("Ollama", style="bold blue")
        version_text.append("\n")
        version_text.append("─" * 40, style="dim cyan")
        version_text.append("\n")
        version_text.append("Made with Love by Roy", style="italic magenta")
        version_text.append("\n\n")
        version_text.append("""⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣴⠶⢦⣤⠶⠶⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣇⠀⠀⠁⠀⢀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢧⣄⠀⣠⠞⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⡀⠀⠉⠛⠃⣠⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡞⠉⠙⢳⣄⢀⡾⠁⠈⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⡄⠀⠀⠙⢿⡇⠀⢰⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⣦⡀⠀⠀⠹⣦⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢳⣄⠀⠀⠈⠻⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡞⠋⠛⢧⡀⠀⠀⠘⢷⡀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⡴⠾⣧⡀⠀⠀⠹⣦⠀⠀⠈⣿⡄⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣿⠀⠀⠈⠻⣄⠀⠀⠀⠀⠀⠀⠈⣷⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⢠⡟⠉⠛⢷⣄⠀⠀⠈⠀⠀⠀⠀⠀⠀⣰⠏⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⢷⡀⠀⠀⠉⠃⠀⠀⠀⠀⠀⠀⠀⣴⠏⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣦⡀⠀⠀⠀⠀⠀⠀⢀⣠⠞⠁⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⠶⣤⣤⣤⡤⠶⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀""", style="dim cyan")

        panel = Panel(
            version_text,
            title=title,
            border_style="cyan",
            padding=(1, 2),
        )
        
        console.print(panel)
        raise typer.Exit()
    
    if ctx.invoked_subcommand is None:
        console.print("Use --help to see available commands")
        raise typer.Exit()


if __name__ == "__main__":
    app()
