"""Debug the regex parsing."""

import re

response = """I'll create a test file called demo_agent.txt

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

# Pattern for WRITE_FILE with content
write_pattern = r"WRITE_FILE:\s*([^\n]+)[\s\n]+CONTENT:\s*```(?:\w+)?\s*(.*?)```"

matches = list(re.finditer(write_pattern, response, re.IGNORECASE | re.DOTALL))

print(f"Found {len(matches)} matches")

for match in matches:
    print(f"Path: {match.group(1).strip()}")
    print(f"Content: {match.group(2).strip()}")
