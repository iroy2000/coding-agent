# Usage Guide

A deeper walkthrough of `coding-agent`, beyond what's in the README.

## Contents

1. [First-time setup](#first-time-setup)
2. [Chat mode](#chat-mode)
3. [File edits, shell commands & git](#file-edits-shell-commands--git)
4. [Configuration](#configuration)
5. [History](#history)
6. [Multiple projects / models](#multiple-projects--models)
7. [Writing good prompts](#writing-good-prompts)
8. [Troubleshooting](#troubleshooting)

---

## First-time setup

```bash
curl -fsSL https://ollama.com/install.sh | sh   # install Ollama
ollama pull codellama                            # pull a model

coding-agent init                                # creates config, checks Ollama connection
coding-agent chat                                # start chatting
```

---

## Chat mode

```bash
coding-agent chat
```

You'll get a prompt in your workspace:

```
Welcome to Coding Agent CLI!

Workspace: /Users/you/project
Model: codellama:latest
Type 'help' for commands or start chatting!

>
```

A few things you can ask it:

```
> What's the difference between list.append() and list.extend() in Python?
> Create a Python function that validates email addresses using regex
> Refactor the calculate_total function in utils.py to be more efficient
> I'm getting a KeyError on line 42 in data_processor.py. Can you help?
```

In-chat commands:

| Command | Does |
|---|---|
| `help` | Show available commands |
| `exit` / `quit` | End the session |
| `clear` | Clear current conversation context |
| `workspace` | Show current workspace info |
| `models` | List available Ollama models |

A short session, showing the agent creating a file and then following up:

```
$ coding-agent chat

> Create a FastAPI endpoint for user registration

Agent: I'll create a user registration endpoint for you.

[File: api/routes/auth.py]
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter()

class UserRegistration(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None

@router.post("/register")
async def register_user(user: UserRegistration):
    hashed_password = hash_password(user.password)
    # ... store user, return response ...
    return {"message": "User registered successfully"}
```

Want me to add password hashing, database integration, or email verification next?

> Add password hashing using bcrypt

Agent: I'll add password hashing functionality.
...
```

---

## File edits, shell commands & git

The agent asks before it changes anything on disk or runs a command — you stay in control by default.

### Diffs before writes

Every file create/edit shows a unified diff first:

```
> Refactor the fibonacci function to use memoization

Agent: Here's the change I'd like to make to fibonacci.py:

--- fibonacci.py
+++ fibonacci.py
@@ -1,3 +1,6 @@
+from functools import lru_cache
+
+@lru_cache(maxsize=None)
 def fibonacci(n):
     ...

Apply this change? [y/N]
```

`y` applies it, anything else (including just Enter) rejects it. Nothing touches disk until you approve.

### Shell commands

The agent can run things like `pytest` or a linter to check its own work, but it asks first and refuses a denylist of destructive commands outright (`rm -rf /`, fork bombs, `sudo`, etc.):

```
> Run the test suite to make sure your change didn't break anything

Agent: I'd like to run: pytest -q
Proceed? [y/N]
```

Note the denylist covers destructive local commands, not remote-code patterns like `curl | bash` — don't rely on it as a full sandbox (tracked in [issue #4](https://github.com/iroy2000/coding-agent/issues/4)).

### `--yes` for scripts/CI

```bash
coding-agent chat --yes
```

Skips both the file-write and shell-command confirmations. Only use this in trusted environments — it removes the one manual review step that exists.

### Git integration

```bash
coding-agent chat --git-commit
```

Commits each successful change with a `[coding-agent]` prefix, so they're easy to spot in `git log`. If one turns out to be wrong:

```bash
coding-agent undo
```

`undo` does a `git revert`, not a reset, and only ever touches commits the agent made itself — it won't touch your own commits or its own revert commits, so you can't double-undo by accident.

---

## Configuration

```bash
coding-agent config --show
coding-agent config --set OLLAMA_MODEL=deepseek-coder
coding-agent config --set OLLAMA_HOST=http://192.168.1.100:11434
coding-agent config --set WORKSPACE_PATH=/path/to/project
coding-agent config --set MAX_HISTORY_LENGTH=100
```

| Variable | Default | What it does |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `codellama:latest` | Model used for chat |
| `WORKSPACE_PATH` | `.` | Working directory the agent operates in |
| `MAX_HISTORY_LENGTH` | `50` | Max messages kept in memory per session |
| `HISTORY_ENABLED` | `true` | Whether conversation history is saved |

---

## History

```bash
coding-agent history --list
coding-agent history --list --limit 5
coding-agent history --view <session-id>
coding-agent history --delete <session-id>
coding-agent history --export <session-id> --output chat.md --format md    # or json / txt
```

`--list` currently shows history across all workspaces, not just the current one — filtering by workspace is tracked in [issue #5](https://github.com/iroy2000/coding-agent/issues/5).

---

## Multiple projects / models

Each workspace keeps its own history:

```bash
cd ~/projects/web-app && coding-agent chat
cd ~/projects/data-pipeline && coding-agent chat
```

Switch models depending on the task:

```bash
coding-agent config --set OLLAMA_MODEL=codellama          # general coding
coding-agent config --set OLLAMA_MODEL=deepseek-coder     # code generation
coding-agent config --set OLLAMA_MODEL=codellama:7b-code  # faster, smaller
```

If Ollama runs on another machine, point at it:

```bash
coding-agent config --set OLLAMA_HOST=http://192.168.1.100:11434
```

MCP server integration (exposing `coding-agent` to Claude Desktop and other MCP clients via `coding-agent serve`) is covered in the [README](README.md#mcp-server-early--beta) rather than repeated here.

---

## Writing good prompts

Vague requests get vague results. Instead of:

```
> Make this code better
```

try being specific about what "better" means:

```
> Refactor the process_data function in utils.py to:
1. Add error handling for file not found
2. Use type hints
3. Add docstrings
```

When asking about an error, include the message, the file/line, and what you were doing:

```
> I'm getting "AttributeError: 'NoneType' object has no attribute 'split'"
> on line 42 of parser.py when parsing CSV files with empty cells. How
> can I handle this?
```

And always read generated code before running it — check error handling, edge cases, and whether it actually matches your project's conventions. The agent doesn't know your standards unless you tell it.

---

## Troubleshooting

**"Failed to connect to Ollama"**
```bash
ollama list                              # is it running?
curl http://localhost:11434/api/tags     # is it reachable?
coding-agent config --show               # check configured host
```

**"Model 'xyz' not found"**
```bash
ollama pull codellama
coding-agent config --set OLLAMA_MODEL=codellama:latest
```

**Slow responses** — try a smaller/quantized model:
```bash
coding-agent config --set OLLAMA_MODEL=codellama:7b-code
```

**History not saving**
```bash
coding-agent config --show                          # check HISTORY_ENABLED
coding-agent config --set HISTORY_ENABLED=true
ls -la ~/.coding-agent/history                       # check permissions
```

**"Permission denied" / "File not in workspace"** — the agent refuses to touch files outside the configured workspace as a safety measure. Check `coding-agent config --show` for the current `WORKSPACE_PATH` and verify the target file's permissions.

**`.env` not picked up** — if you installed via `pip`/`pipx` (not `-e`), config loading currently has a bug where it doesn't reliably find your `.env` — see [issue #2](https://github.com/iroy2000/coding-agent/issues/2). Workaround: set the variable via `coding-agent config --set` instead, or export it as a real environment variable.

---

## Getting help

```bash
coding-agent --help
coding-agent chat --help
coding-agent config --help
coding-agent history --help
```

Or `help` inside a chat session.

Bugs and feature requests: [GitHub Issues](https://github.com/iroy2000/coding-agent/issues).
