# Coding Agent CLI - Usage Guide

Complete guide to using the Coding Agent CLI effectively.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Interactive Chat Mode](#interactive-chat-mode)
3. [Configuration](#configuration)
4. [History Management](#history-management)
5. [Advanced Usage](#advanced-usage)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Getting Started

### First-Time Setup

1. **Install Ollama** (if not already installed):
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Pull a coding model**:
   ```bash
   # Recommended for coding tasks
   ollama pull codellama
   
   # Alternative models
   ollama pull deepseek-coder    # Excellent for code generation
   ollama pull qwen2.5-coder     # Fast and efficient
   ```

3. **Initialize Coding Agent**:
   ```bash
   coding-agent init
   ```

   This will:
   - Create configuration files
   - Set up history directory
   - Test Ollama connection
   - Configure default model

4. **Start chatting**:
   ```bash
   coding-agent chat
   ```

---

## Interactive Chat Mode

### Starting a Session

```bash
coding-agent chat
```

You'll see:
```
Welcome to Coding Agent CLI!

Workspace: /Users/you/project
Model: codellama:latest
Type 'help' for commands or start chatting!

>
```

### Basic Interactions

#### Ask Questions
```
> What's the difference between list.append() and list.extend() in Python?
```

#### Generate Code
```
> Create a Python function that validates email addresses using regex
```

#### Refactor Code
```
> Refactor the calculate_total function in utils.py to be more efficient
```

#### Debug Code
```
> I'm getting a KeyError on line 42 in data_processor.py. Can you help?
```

### In-Chat Commands

While in chat mode, you can use these special commands:

| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `exit` or `quit` | End the chat session |
| `clear` | Clear current conversation context |
| `workspace` | Show current workspace information |
| `models` | List available Ollama models |

### Example Session

```bash
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
    # Hash password
    hashed_password = hash_password(user.password)
    
    # Store user in database
    # ... implementation ...
    
    return {"message": "User registered successfully"}
```

I've created a basic registration endpoint. Would you like me to:
1. Add password hashing implementation?
2. Add database integration?
3. Add email verification?

> Add password hashing using bcrypt

Agent: I'll add password hashing functionality.
...
```

---

## Configuration

### View Configuration

```bash
coding-agent config --show
```

Output:
```
╔════════════════════════════════════════╗
║        Current Configuration           ║
╚════════════════════════════════════════╝

Ollama Configuration
  > Host:  http://localhost:11434
  > Model: codellama:latest

Workspace Configuration
  > Path:  /Users/you/project

History Configuration
  > Max Length: 50
  > Enabled:     true
```

### Update Configuration

#### Change Model
```bash
coding-agent config --set OLLAMA_MODEL=deepseek-coder
```

#### Change Ollama Host
```bash
coding-agent config --set OLLAMA_HOST=http://192.168.1.100:11434
```

#### Change Workspace
```bash
coding-agent config --set WORKSPACE_PATH=/path/to/project
```

#### Adjust History Length
```bash
coding-agent config --set MAX_HISTORY_LENGTH=100
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `codellama:latest` | Model to use for chat |
| `WORKSPACE_PATH` | `.` | Current working directory |
| `MAX_HISTORY_LENGTH` | `50` | Max messages to keep in memory |
| `HISTORY_ENABLED` | `true` | Enable conversation history |

---

## History Management

### List All Conversations

```bash
coding-agent history --list
```

Output:
```
╔════════════════════════════════════════════════════════╗
║              Conversation History                      ║
╚════════════════════════════════════════════════════════╝

┌─────────────────────┬──────────┬─────────────────────┐
│ Session ID          │ Messages │ Last Updated        │
├─────────────────────┼──────────┼─────────────────────┤
│ 20251005_143022_... │ 12       │ 2025-10-05 14:45:10 │
│ 20251005_120430_... │ 8        │ 2025-10-05 12:15:22 │
│ 20251004_163015_... │ 24       │ 2025-10-04 17:20:45 │
└─────────────────────┴──────────┴─────────────────────┘
```

### Limit Results

```bash
coding-agent history --list --limit 5
```

### View Specific Conversation

```bash
coding-agent history --view 20251005_143022_123456
```

### Delete Conversation

```bash
coding-agent history --delete 20251005_143022_123456
```

### Export Conversations

#### Export to Markdown
```bash
coding-agent history --export 20251005_143022_123456 \
  --output conversation.md \
  --format md
```

#### Export to JSON
```bash
coding-agent history --export 20251005_143022_123456 \
  --output conversation.json \
  --format json
```

#### Export to Plain Text
```bash
coding-agent history --export 20251005_143022_123456 \
  --output conversation.txt \
  --format txt
```

---

## Advanced Usage

### Working with Multiple Projects

```bash
# Project 1
cd ~/projects/web-app
coding-agent chat

# Project 2
cd ~/projects/data-pipeline
coding-agent chat
```

Each project maintains its own conversation context and workspace.

### Using Different Models

For different types of tasks, you might want to use different models:

```bash
# For code generation
coding-agent config --set OLLAMA_MODEL=codellama

# For general questions
coding-agent config --set OLLAMA_MODEL=deepseek-coder

# For faster responses (smaller model)
coding-agent config --set OLLAMA_MODEL=codellama:7b-code
```

### Remote Ollama Server

If you have Ollama running on another machine:

```bash
coding-agent config --set OLLAMA_HOST=http://192.168.1.100:11434
```

---

## Best Practices

### 1. Be Specific in Requests

❌ **Not ideal:**
```
> Make this code better
```

✅ **Better:**
```
> Refactor the process_data function in utils.py to:
1. Add error handling for file not found
2. Use type hints
3. Add docstrings
```

### 2. Provide Context

When asking about errors, include:
- Error message
- File name and line number
- What you were trying to do

Example:
```
> I'm getting "AttributeError: 'NoneType' object has no attribute 'split'" 
> on line 42 of parser.py when trying to parse CSV files with empty cells.
> How can I handle this?
```

### 3. Review Generated Code

Always review code before running it:
- Check for security issues
- Verify error handling
- Test edge cases
- Ensure it fits your coding style

### 4. Use History for Learning

Export conversations to create personal knowledge bases:
```bash
coding-agent history --export SESSION_ID --output notes.md --format md
```

### 5. Manage Workspace Carefully

- Set workspace to project root
- Ensure .gitignore is configured
- The agent respects .gitignore patterns

---

## Troubleshooting

### Ollama Connection Issues

**Problem:** "Failed to connect to Ollama"

**Solutions:**
1. Verify Ollama is running:
   ```bash
   ollama list
   ```

2. Check Ollama status:
   ```bash
   curl http://localhost:11434/api/tags
   ```

3. Restart Ollama:
   ```bash
   # macOS/Linux
   sudo systemctl restart ollama
   ```

4. Check configuration:
   ```bash
   coding-agent config --show
   ```

### Model Not Found

**Problem:** "Model 'xyz' not found"

**Solution:** Pull the model first:
```bash
ollama pull codellama
coding-agent config --set OLLAMA_MODEL=codellama:latest
```

### Slow Responses

**Solutions:**
1. Use a smaller model:
   ```bash
   coding-agent config --set OLLAMA_MODEL=codellama:7b-code
   ```

2. Check CPU/GPU usage during generation

3. Consider using quantized models

### History Not Saving

**Solutions:**
1. Check if history is enabled:
   ```bash
   coding-agent config --show
   ```

2. Enable history:
   ```bash
   coding-agent config --set HISTORY_ENABLED=true
   ```

3. Check directory permissions:
   ```bash
   ls -la ~/.coding-agent/history
   ```

### File Operations Failing

**Problem:** "Permission denied" or "File not in workspace"

**Solutions:**
1. Verify workspace path:
   ```bash
   coding-agent config --show
   ```

2. Check file permissions:
   ```bash
   ls -la /path/to/file
   ```

3. Ensure file is within workspace (security feature)

---

## Tips & Tricks

### 1. Quick Model Switching

Create aliases for different models:
```bash
alias agent-fast="coding-agent config --set OLLAMA_MODEL=codellama:7b-code && coding-agent chat"
alias agent-smart="coding-agent config --set OLLAMA_MODEL=deepseek-coder && coding-agent chat"
```

### 2. Project Templates

Create a project initialization script:
```bash
#!/bin/bash
cd $1
coding-agent init
coding-agent chat
```

### 3. Batch Processing

For multiple similar tasks:
```bash
for file in *.py; do
    echo "Review $file for security issues" | coding-agent chat
done
```

### 4. Integration with Git

```bash
# Before committing
git diff | coding-agent chat
# Ask: "Review these changes for potential issues"
```

### 5. Documentation Generation

```bash
# Ask agent to document your code
coding-agent chat
> Generate comprehensive docstrings for all functions in api/routes/users.py
```

---

## Keyboard Shortcuts

While in chat mode:

- `Ctrl+C` - Cancel current input
- `Ctrl+D` - Exit chat (same as `exit`)
- `Up Arrow` - Previous command (coming soon)
- `Down Arrow` - Next command (coming soon)

---

## Getting Help

### Command Help
```bash
coding-agent --help
coding-agent chat --help
coding-agent config --help
coding-agent history --help
```

### In-Chat Help
```
> help
```

### Community Support
- GitHub Issues: https://github.com/iroy2000/coding-agent-cli/issues
- Discussions: https://github.com/iroy2000/coding-agent-cli/discussions

---

## Next Steps

- Explore [Advanced Examples](EXAMPLES.md)
- Read [API Documentation](API.md)
- Check out [Contributing Guide](CONTRIBUTING.md)
- Join the community discussions

Happy coding with your AI assistant! 🤖✨
