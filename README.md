# Coding Agent CLI 🤖

An interactive coding assistant CLI powered by local LLMs via Ollama. Get AI-powered help with code generation, refactoring, debugging, and more - all running locally on your machine.

## ✨ Features

- 🎯 **Interactive Chat Mode** - Natural conversation with your coding assistant
- 📁 **File Operations** - Read, write, and edit files in your workspace
- 🔍 **Diff Preview** - Review a unified diff and approve/deny before any file is written or edited
- 🖥️ **Shell Command Execution** - Agent can run tests, linters, and builds (with confirmation) to verify its own changes
- 🧠 **Context-Aware** - Maintains conversation history and workspace understanding
- 🎨 **Beautiful Output** - Colored, formatted terminal output with syntax highlighting
- 🔒 **100% Local** - Uses Ollama for complete privacy and offline capability
- 🚀 **Language Agnostic** - Works with any programming language

## 📋 Prerequisites

Before installing, make sure you have:

1. **Python 3.9+** installed
2. **Ollama** installed and running

### Install Ollama

```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Or visit https://ollama.com for other platforms
```

### Pull a Coding Model

```bash
# Recommended models
ollama pull codellama          # Meta's CodeLlama (7B)
ollama pull deepseek-coder     # DeepSeek Coder (6.7B)
ollama pull qwen2.5-coder      # Qwen 2.5 Coder (7B)

# Or use a smaller model for faster responses
ollama pull codellama:7b-code
```

## 🚀 Installation

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/iroy2000/coding-agent.git
cd coding-agent-cli

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env

# Edit .env with your preferred settings
nano .env
```

### From PyPI

Package metadata is release-ready (`pyproject.toml` fixed, `python -m build` + `twine check`
verified, CI runs the full test suite before every publish). A maintainer can ship the first
release by pushing a `v*.*.*` tag, which triggers `.github/workflows/release.yml` to build,
test, and publish to PyPI automatically:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Once published, install with:

```bash
pip install coding-agent-cli
```

## 🎮 Quick Start

### Initialize Configuration

```bash
coding-agent init
```

### Start Interactive Chat

```bash
coding-agent chat
```

### Example Session

```bash
$ coding-agent chat

Welcome to Coding Agent CLI! 🤖
Type 'exit' or 'quit' to end the session.
Type 'help' for available commands.

> Create a Python function to calculate fibonacci numbers

Agent: I'll create a fibonacci function for you.
[Creating file: fibonacci.py]
✓ File created successfully

I've created a fibonacci function using memoization for efficiency.
Would you like me to add tests or examples?

> Yes, add some test cases

Agent: I'll add pytest test cases.
[Creating file: test_fibonacci.py]
✓ File created successfully

I've added comprehensive test cases. You can run them with: pytest test_fibonacci.py
```

## 📖 Usage

### Commands

```bash
# Start interactive chat session
coding-agent chat

# Auto-approve shell commands and file writes/edits (use with caution)
coding-agent chat --yes

# Auto-commit each successful file write/edit to git (only if workspace is a git repo)
coding-agent chat --git-commit

# Undo the last agent-made git commit (safe: refuses to undo commits it didn't make)
coding-agent undo

# Initialize configuration (first-time setup)
coding-agent init

# View current configuration
coding-agent config --show

# Update configuration
coding-agent config --set OLLAMA_MODEL=deepseek-coder
coding-agent config --set MAX_HISTORY_LENGTH=100

# List conversation history
coding-agent history --list
coding-agent history --list --limit 10

# View specific conversation
coding-agent history --view <session-id>

# Delete a conversation session
coding-agent history --delete <session-id>

# Export conversation to file
coding-agent history --export <session-id> --output chat.md --format md
coding-agent history --export <session-id> --output chat.json --format json
coding-agent history --export <session-id> --output chat.txt --format txt

# Show version
coding-agent --version

# Show help
coding-agent --help
```

### Chat Commands

While in interactive mode, you can use these commands:

- `exit` or `quit` - End the session
- `help` - Show available commands
- `clear` - Clear conversation history
- `workspace` - Show current workspace info
- `models` - List available Ollama models

## ⚙️ Configuration

Configuration is managed through a `.env` file:

```env
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=codellama:latest

# Workspace Configuration
WORKSPACE_PATH=.

# History Configuration
MAX_HISTORY_LENGTH=50
HISTORY_ENABLED=true

# Display Configuration
SHOW_SPINNER=true
SYNTAX_THEME=monokai
```

## 🎯 What Can It Do?

### Generate Code

```
> Create a REST API endpoint in Python using FastAPI for user authentication
```

### Refactor Code

```
> Refactor the main.py file to use async/await pattern
```

### Debug Issues

```
> I'm getting a "TypeError: 'NoneType' object is not subscriptable" in line 42 of utils.py, can you help?
```

### Answer Questions

```
> What's the difference between @staticmethod and @classmethod in Python?
```

### Review Code

```
> Review the error handling in my database.py file and suggest improvements
```

## 🏗️ Project Structure

```
coding-agent-cli/
├── src/
│   └── coding_agent/
│       ├── cli.py              # CLI interface
│       ├── agent.py            # Core agent logic
│       ├── llm/                # LLM integration
│       ├── tools/              # File operations
│       ├── storage/            # History management
│       └── utils/              # Utilities
├── tests/                      # Test suite
├── .env.example               # Configuration template
├── pyproject.toml             # Project metadata
└── README.md                  # This file
```

## 🧪 Development

### Run Tests

```bash
pytest
```

### Run Tests with Coverage

```bash
pytest --cov=src/coding_agent --cov-report=html
```

### Format Code

```bash
black src/ tests/
```

### Lint Code

```bash
ruff check src/ tests/
```

### Type Check

```bash
mypy src/
```

## 🗺️ Roadmap

### Completed ✅
- [x] Basic chat interface
- [x] Streaming responses in chat
- [x] File read/write operations
- [x] File editing (search & replace)
- [x] Shell command execution tool (run tests/build/lint, with safety confirmation)
- [x] Diff preview & confirmation before file writes/edits
- [x] Git integration: opt-in auto-commit of agent changes + safe `undo` (git revert, agent-commits only)
- [x] Conversation history with search
- [x] Session management (list, view, delete, export)
- [x] Configuration management
- [x] .gitignore respect
- [x] Colored terminal output with Rich
- [x] Multiple export formats (JSON, TXT, Markdown)
- [x] CI pipeline (GitHub Actions) running tests on every push/PR
- [x] Comprehensive test suite (150+ tests, 44%+ coverage)

### In Progress 🚧
- [ ] Enhanced error handling
- [ ] Performance optimizations
- [ ] Extended documentation

### Planned 🎯
- [ ] Plugin system
- [ ] Multiple LLM provider support (OpenAI, Anthropic, etc.)
- [ ] Web UI
- [ ] VS Code extension
- [ ] Code review mode
- [ ] Workspace templates
- [ ] Repository indexing / semantic search
- [ ] Structured tool-calling (replace regex-based action parsing)

## 🔌 MCP Server (Beta)

**Model Context Protocol** support is now available! Expose your coding-agent's capabilities to other MCP-enabled applications like Claude Desktop.

### Quick Start

Start the MCP server with Safe Mode defaults (recommended):

```bash
coding-agent serve
```

This exposes three tools to MCP clients:
- `read_file` - Read files from your workspace
- `list_files` - List and search files
- `explain_code` - Get AI explanations of code snippets

### Claude Desktop Integration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "coding-agent": {
      "command": "coding-agent",
      "args": ["serve", "--workspace", "/path/to/your/project"]
    }
  }
}
```

Now Claude Desktop can read and analyze files in your project!

### Advanced Usage

```bash
# Serve specific workspace
coding-agent serve --workspace /path/to/project

# Enable all tools (including history)
coding-agent serve --enable-history-tools

# Disable Safe Mode for full access
coding-agent serve --no-safe-mode

# Show all options
coding-agent serve --help
```

### Safe Mode (Default)

For security and cost control, Safe Mode enables only:
- ✅ **read_file** - Read-only file access
- ✅ **list_files** - Directory listing
- ✅ **explain_code** - Code explanations (low cost)
- ❌ **write_file** - Disabled (requires explicit opt-in)
- ❌ **generate_code** - Disabled (expensive operations)
- ❌ **search_history** - Disabled (privacy)

### What is MCP?

[Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open standard by Anthropic that enables AI applications to securely access data and tools. Think of it as a universal adapter that lets different AI tools work together.

**Status**: Phase 1A Complete (stdio transport foundation)
- ✅ Tool registration system
- ✅ Safe Mode defaults
- ✅ CLI command with full options
- ⏳ Full MCP stdio protocol (Phase 1B)
- ⏳ MCP Inspector testing (Phase 1B)

See [MCP_STATUS.md](MCP_STATUS.md) for detailed status and roadmap.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.com) for making local LLM inference easy
- [Typer](https://typer.tiangolo.com) for the amazing CLI framework
- [Rich](https://rich.readthedocs.io) for beautiful terminal output

## 📧 Support

- 🐛 [Report a bug](https://github.com/iroy2000/coding-agent-cli/issues)
- 💡 [Request a feature](https://github.com/iroy2000/coding-agent-cli/issues)
- 📖 [Documentation](https://github.com/iroy2000/coding-agent-cli/wiki)
- 💬 [Discussions](https://github.com/iroy2000/coding-agent-cli/discussions)

Project Link: [https://github.com/iroy2000/coding-agent-cli](https://github.com/iroy2000/coding-agent-cli)

---

Made with Love by Roy

```
⠀⠀⠀⣀⣀⣤⣤⣦⣶⢶⣶⣿⣿⣿⣿⣿⣿⣿⣷⣶⣶⡄⠀⠀⠀⠀⠀⠀⠀⠀
⠀⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡀⠀⠀⠀⠀⠀⠀
⠀⠉⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⠀⠀⠀⠀
⠀⠀⠀⠈⠙⠻⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠈⠙⠻⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⠻⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⠻⢿⣿⣿⣿⣿⣿⣿⣿⣿⣷⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⠻⢿⣿⣿⣿⣿⣿⣧⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⢻⣿⣿⣿⡆
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⣿⣿⡇
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⣿⡇
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠃
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡿⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡇⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
```
