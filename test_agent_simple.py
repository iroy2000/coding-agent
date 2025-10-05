"""Simple test of agent file operations."""

from coding_agent.agent import CodingAgent
from coding_agent.utils.config import Config

config = Config()
agent = CodingAgent(
    workspace_path=str(config.workspace_path),
    ollama_host=config.ollama_host,
    model=config.ollama_model,
)

print("=" * 60)
print("Test 1: Explicit READ_FILE command")
print("=" * 60)

# Direct command that should be parsed
message = """Please read the pyproject.toml file.

READ_FILE: pyproject.toml
"""

response = agent.process_message(message, stream=False)

print("\n" + "=" * 60)
print("Test 2: Create a file")
print("=" * 60)

message2 = """Create a test file called demo_agent.txt

WRITE_FILE: demo_agent.txt
CONTENT:
```
This is a test file created by the Coding Agent.
It demonstrates the agent's ability to write files.

Features:
- Automatic file creation
- Directory handling
- Content formatting
```
"""

response2 = agent.process_message(message2, stream=False)

print("\n" + "=" * 60)
print("Done! Check if demo_agent.txt was created.")
print("=" * 60)
