# Coding Agent CLI

An interactive coding assistant that runs entirely on local LLMs via [Ollama](https://ollama.com). Ask it to write code, refactor, debug, or explain something, and it works in your terminal against the files in your workspace — nothing gets sent to a third-party API.

## What it does

- **Interactive chat** in your terminal, with the model aware of your workspace.
- **Reads, writes, and edits files** directly, and shows you a diff before anything is applied.
- **Runs shell commands** (tests, linters, builds) to check its own work — also with confirmation first, and a denylist for obviously destructive commands.
- **Keeps conversation history** per session, with list/view/delete/export.
- **Optional git integration** — auto-commit each change it makes, with a safe `undo` that will only revert commits it made itself.
- Works with any Ollama model and any programming language.

## Prerequisites

- Python 3.9+
- [Ollama](https://ollama.com), installed and running

Install Ollama:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Pull a model suited to coding:

```bash
ollama pull codellama          # 7B, good general default
ollama pull deepseek-coder     # 6.7B, strong at code generation
ollama pull qwen2.5-coder      # 7B, fast — must be pulled explicitly, it isn't bundled with Ollama
```

Any of these work fine as a starting point; use whichever is already on your machine.

## Installation

### From source

```bash
git clone https://github.com/iroy2000/coding-agent.git
cd coding-agent

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -e ".[dev]"

cp .env.example .env
# edit .env if you want to change the default model/host
```

### From PyPI

Not published yet — see [issue #12](https://github.com/iroy2000/coding-agent/issues/12) for the first-release plan. Once it's out:

```bash
pip install coding-agent-cli
```

## Quick start

```bash
coding-agent init    # writes config, checks Ollama is reachable
coding-agent chat    # start a session
```

Example:

```
$ coding-agent chat

Welcome to Coding Agent CLI!
Type 'exit' or 'quit' to end the session, 'help' for commands.

> Create a Python function to calculate fibonacci numbers

Agent: I'll create a fibonacci function for you.
[Creating file: fibonacci.py]
✓ File created successfully

I've created a fibonacci function using memoization for efficiency.
Would you like me to add tests?

> Yes, add some test cases

Agent: I'll add pytest test cases.
[Creating file: test_fibonacci.py]
✓ File created successfully

You can run them with: pytest test_fibonacci.py
```

## Usage

```bash
coding-agent chat                  # interactive session
coding-agent chat --yes            # auto-approve file writes and shell commands (careful with this)
coding-agent chat --git-commit     # auto-commit each successful change (workspace must be a git repo)
coding-agent undo                  # revert the last agent-made commit

coding-agent init                  # first-time setup
coding-agent config --show
coding-agent config --set OLLAMA_MODEL=deepseek-coder
coding-agent config --set MAX_HISTORY_LENGTH=100

coding-agent history --list
coding-agent history --list --limit 10
coding-agent history --view <session-id>
coding-agent history --delete <session-id>
coding-agent history --export <session-id> --output chat.md --format md

coding-agent --version
coding-agent --help
```

In-chat commands: `exit`/`quit`, `help`, `clear`, `workspace`, `models`.

## Configuration

Settings live in a `.env` file in the project (or `~/.coding-agent/.env`):

```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=codellama:latest

WORKSPACE_PATH=.

MAX_HISTORY_LENGTH=50
HISTORY_ENABLED=true

SHOW_SPINNER=true
SYNTAX_THEME=monokai
```

## Things you can ask it

```
> Create a REST API endpoint in Python using FastAPI for user authentication
> Refactor the main.py file to use async/await
> I'm getting "TypeError: 'NoneType' object is not subscriptable" on line 42 of utils.py, can you help?
> What's the difference between @staticmethod and @classmethod in Python?
> Review the error handling in database.py and suggest improvements
```

See [EXAMPLES.md](EXAMPLES.md) and [USAGE_GUIDE.md](USAGE_GUIDE.md) for more.

## Project structure

```
coding-agent-cli/
├── src/coding_agent/
│   ├── cli.py           # CLI entry point (Typer)
│   ├── agent.py         # Core agent loop
│   ├── llm/             # Ollama client + prompts
│   ├── tools/           # File operations, shell execution
│   ├── storage/         # Conversation history
│   └── utils/           # Config, display
├── tests/
├── scripts/             # dev-only helper scripts, see scripts/README.md
└── pyproject.toml
```

## Development

```bash
pytest                                          # run tests
pytest --cov=src/coding_agent --cov-report=html # with coverage
black src/ tests/                               # format
ruff check src/ tests/                          # lint
mypy src/                                       # type check
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full dev setup.

## Roadmap

Active work is tracked in [GitHub Issues](https://github.com/iroy2000/coding-agent/issues), not duplicated here. A few things currently open:

- Structured tool-calling instead of regex-parsed actions ([#8](https://github.com/iroy2000/coding-agent/issues/8))
- Support for LLM providers beyond Ollama ([#9](https://github.com/iroy2000/coding-agent/issues/9))
- Repository-wide search/indexing ([#10](https://github.com/iroy2000/coding-agent/issues/10))
- First PyPI release ([#12](https://github.com/iroy2000/coding-agent/issues/12))

What's already working: chat, file read/write/edit with diff confirmation, shell command execution with a safety denylist, git auto-commit/undo, history with export, and CI running the full test suite (200+ tests) on every push.

## MCP server (early / beta)

`coding-agent serve` runs an MCP (Model Context Protocol) server over stdio, so tools like Claude Desktop can call into your workspace. This is genuinely early — three tools are wired up (`read_file`, `list_files`, `explain_code`), Safe Mode is on by default, and the full protocol surface is still being built out. Treat it as a preview, not a finished integration.

```bash
coding-agent serve                          # Safe Mode: read_file, list_files, explain_code only
coding-agent serve --workspace /path/to/project
coding-agent serve --enable-history-tools   # also expose history search
coding-agent serve --no-safe-mode           # full tool access — only do this if you trust the client
```

Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

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

Safe Mode enables `read_file`, `list_files`, and `explain_code`; it leaves `write_file`, `generate_code`, and `search_history` off by default since those are either destructive, expensive, or privacy-sensitive.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Short version: fork, branch, make sure `pytest` passes, open a PR.

## License

MIT — see [LICENSE](LICENSE).

## Thanks

Built on [Ollama](https://ollama.com) for local inference, [Typer](https://typer.tiangolo.com) for the CLI, and [Rich](https://rich.readthedocs.io) for terminal output.

## Links

- [Report a bug / request a feature](https://github.com/iroy2000/coding-agent/issues)
- [Repo](https://github.com/iroy2000/coding-agent)

---

Made by Roy.
