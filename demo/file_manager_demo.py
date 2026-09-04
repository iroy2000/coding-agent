"""Demo script showing FileManager capabilities."""

from coding_agent.tools.file_manager import FileManager
from coding_agent.utils.config import Config
from coding_agent.utils.display import (
    print_file_list,
    print_file_content,
    print_file_operation_result,
    print_panel,
    print_separator,
    console
)

# Initialize
config = Config()
fm = FileManager(config.workspace_path)

print_panel(
    f"[bold]FileManager Demo[/bold]\n\n"
    f"Workspace: [cyan]{fm.workspace}[/cyan]",
    title="Welcome",
    border_style="green"
)

# Demo 1: List files
print_separator()
console.print("\n[bold yellow]Demo 1: List Files[/bold yellow]")
success, files = fm.list_files("src", max_depth=2)
if success:
    print_file_list(files, title="Source Files")
else:
    print_file_operation_result(success, files, "List files")

# Demo 2: Read a file
print_separator()
console.print("\n[bold yellow]Demo 2: Read File[/bold yellow]")
success, content = fm.read_file("pyproject.toml")
if success:
    print_file_content(content, "pyproject.toml", max_lines=30)
else:
    print_file_operation_result(success, content, "Read file")

# Demo 3: Create a demo directory and files
print_separator()
console.print("\n[bold yellow]Demo 3: Write Files[/bold yellow]")

# Create a Python module
demo_code = '''"""Demo module created by FileManager."""


def greet(name: str) -> str:
    """
    Generate a greeting message.
    
    Args:
        name: Name to greet
        
    Returns:
        Greeting message
    """
    return f"Hello, {name}! Welcome to Coding Agent CLI."


def calculate_sum(numbers: list[int]) -> int:
    """
    Calculate the sum of a list of numbers.
    
    Args:
        numbers: List of integers
        
    Returns:
        Sum of all numbers
    """
    return sum(numbers)


if __name__ == "__main__":
    print(greet("Developer"))
    print(f"Sum of [1, 2, 3, 4, 5]: {calculate_sum([1, 2, 3, 4, 5])}")
'''

success, message = fm.write_file("demo/example.py", demo_code, overwrite=True)
print_file_operation_result(success, message, "Write Python file")

# Create a markdown doc
demo_doc = '''# Demo Documentation

This documentation was created by the FileManager.

## Features

The FileManager supports:

1. **Reading Files** - Read any text file in the workspace
2. **Writing Files** - Create new files with automatic directory creation
3. **Editing Files** - Find and replace text in existing files
4. **Listing Files** - Recursively list files with .gitignore support
5. **File Info** - Get detailed information about any file

## Code Example

```python
from coding_agent.tools.file_manager import FileManager

fm = FileManager("/path/to/workspace")
success, content = fm.read_file("example.py")
if success:
    print(content)
```

## Security

- All paths are validated to be within the workspace
- .gitignore patterns are respected
- Permission errors are handled gracefully
'''

success, message = fm.write_file("demo/README.md", demo_doc, overwrite=True)
print_file_operation_result(success, message, "Write Markdown file")

# Demo 4: Edit a file
print_separator()
console.print("\n[bold yellow]Demo 4: Edit File[/bold yellow]")
success, message = fm.edit_file(
    "demo/example.py",
    "Welcome to Coding Agent CLI",
    "Welcome to the Coding Agent CLI - Your AI Programming Assistant"
)
print_file_operation_result(success, message, "Edit file")

# Verify the edit
success, content = fm.read_file("demo/example.py")
if success:
    # Show just the relevant part
    lines = content.split("\n")
    relevant_lines = [l for l in lines if "Welcome" in l]
    console.print(f"\n[dim]Updated line:[/dim] [green]{relevant_lines[0].strip()}[/green]")

# Demo 5: Get file info
print_separator()
console.print("\n[bold yellow]Demo 5: File Information[/bold yellow]")
success, info = fm.get_file_info("demo/example.py")
if success:
    from rich.table import Table
    table = Table(title="File Information", show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Name", info["name"])
    table.add_row("Path", info["path"])
    table.add_row("Size", info["size_human"])
    table.add_row("Type", "File" if info["is_file"] else "Directory")
    table.add_row("Extension", info["extension"] or "None")
    
    console.print(table)
else:
    print_file_operation_result(success, info, "Get file info")

# Demo 6: List the demo directory
print_separator()
console.print("\n[bold yellow]Demo 6: List Demo Directory[/bold yellow]")
success, files = fm.list_files("demo", max_depth=1)
if success:
    print_file_list(files, title="Demo Files")
else:
    print_file_operation_result(success, files, "List directory")

# Summary
print_separator()
print_panel(
    "[bold green]Demo Complete![/bold green]\n\n"
    "The FileManager is fully functional and ready to use.\n"
    "Check the [cyan]demo/[/cyan] directory for the created files.",
    title="Summary",
    border_style="green"
)
