"""Test script for the CodingAgent."""

from coding_agent.agent import CodingAgent
from coding_agent.utils.config import Config
from coding_agent.utils.display import print_panel, print_separator, console

# Initialize
config = Config()
agent = CodingAgent(
    workspace_path=str(config.workspace_path),
    ollama_host=config.ollama_host,
    model=config.ollama_model,
)

print_panel(
    "[bold]CodingAgent Test[/bold]\n\n"
    "This script tests the agent's ability to:\n"
    "• Understand file operation commands\n"
    "• Execute file operations automatically\n"
    "• Maintain conversation context",
    title="Agent Test",
    border_style="cyan"
)

# Test 1: Simple greeting
print_separator()
console.print("\n[bold yellow]Test 1: Simple Conversation[/bold yellow]")
console.print("[cyan]User: Hello! What can you help me with?[/cyan]\n")
response = agent.process_message("Hello! What can you help me with?", stream=False)

# Test 2: List files (agent should detect and execute)
print_separator()
console.print("\n[bold yellow]Test 2: File Listing Request[/bold yellow]")
console.print("[cyan]User: Can you list the Python files in the src directory?[/cyan]\n")
response = agent.process_message(
    "Can you list the Python files in the src directory? Please use LIST_FILES: src",
    stream=False
)

# Test 3: Read a file
print_separator()
console.print("\n[bold yellow]Test 3: Read File Request[/bold yellow]")
console.print("[cyan]User: Read the README.md file[/cyan]\n")
response = agent.process_message(
    "Read the README.md file. Please use READ_FILE: README.md",
    stream=False
)

# Test 4: Create a test file
print_separator()
console.print("\n[bold yellow]Test 4: Write File Request[/bold yellow]")
console.print("[cyan]User: Create a test Python file[/cyan]\n")
response = agent.process_message(
    """Create a simple test file called agent_test.py with a hello function.

WRITE_FILE: agent_test.py
CONTENT:
```python
def hello(name):
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(hello("Agent"))
```
""",
    stream=False
)

# Test 5: Edit the file
print_separator()
console.print("\n[bold yellow]Test 5: Edit File Request[/bold yellow]")
console.print("[cyan]User: Update the hello function[/cyan]\n")
response = agent.process_message(
    """Update the greeting message in agent_test.py to be more enthusiastic.

EDIT_FILE: agent_test.py
OLD:
```
return f"Hello, {name}!"
```
NEW:
```
return f"Hello, {name}! Welcome to the Coding Agent!"
```
""",
    stream=False
)

# Summary
print_separator()
workspace_info = agent.get_workspace_info()
print_panel(
    f"[bold green]Tests Complete![/bold green]\n\n"
    f"Workspace: {workspace_info['path']}\n"
    f"Files: {workspace_info['file_count']}\n"
    f"Conversation turns: {len(agent.conversation_history)}",
    title="Summary",
    border_style="green"
)

console.print("\n[dim]Check the agent_test.py file to see the created content.[/dim]")
