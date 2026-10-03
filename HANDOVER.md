# Handover Document

**Purpose of this file:** a single, up-to-date entry point for whoever (human or
coding agent) picks this project up next — e.g. after a laptop switch. Treat
this as the source of truth over any other local planning doc (see
["About the other docs in this repo"](#about-the-other-docs-in-this-repo)
below — most of them are stale and were never committed to GitHub).

Last updated: 2026-10-02. Repo state at time of writing: `main` @ `4acfaec`,
414 tests passing, working tree clean.

---

## 1. What this product is

**Coding Agent CLI** (`coding-agent`) is a terminal-based AI coding assistant,
similar in spirit to tools like Aider/Claude Code, but designed to run
**entirely against a local LLM via [Ollama](https://ollama.com)** by default
(no data leaves the machine), with optional support for hosted OpenAI/
Anthropic models if the user wants more capable models and is OK sending
code to a third party.

Core capabilities:
- Interactive chat REPL (`coding-agent chat`) that is aware of the current
  workspace.
- The model can autonomously **read, list, search, write, and edit files**,
  and **run shell commands** (tests/linters/builds) — each write/command is
  shown as a diff/preview and requires user confirmation unless `--yes` is
  passed.
- **Conversation history** persisted per session (list/view/export/delete).
- **Git integration**: optional auto-commit of each successful file
  operation, plus a safe `undo` that only reverts commits the agent itself
  made.
- **MCP (Model Context Protocol) server** (`coding-agent serve`) — lets
  external MCP clients (e.g. Claude Desktop) call into the workspace via a
  small, safety-gated tool surface (`read_file`, `list_files`,
  `explain_code`, optionally `search_history`). This is explicitly a
  "preview" feature per the README, not fully built out.

Target user: a developer who wants a terminal coding assistant without
sending their code to a cloud API, and is fine with the more limited
code-understanding of local 7B-ish models (codellama, deepseek-coder,
qwen2.5-coder, llama3.2, etc.) in exchange for that.

## 2. Repo / where things live

- GitHub: https://github.com/iroy2000/coding-agent (owner `iroy2000`)
- Default branch: `main`. No branch protection beyond CI — PRs are merged by
  an agent/maintainer once all 3 CI jobs (Python 3.10/3.11/3.12) are green,
  using `gh pr merge <N> --squash --admin --delete-branch`.
- CI: GitHub Actions, runs the full `pytest` suite on 3.10/3.11/3.12 on every
  push/PR. `ruff` also runs in CI but is `continue-on-error: true` —
  informational only, not a merge gate.
- License: MIT.

## 3. Current state (as of this handover)

- **414 tests passing**, 0 failing, ~80% coverage (`pytest --cov`).
- `main` is clean and green. No open PRs, no uncommitted local changes.
- Two open GitHub issues (both longer-term, not urgent):
  - **#12** — cut the first PyPI release (v0.1.0). Package has never been
    published; `pip install coding-agent-cli` does not work yet. Only
    `pip install -e .` from a local clone works today.
  - **#8** — replace the regex/text-based action-parsing fallback (used by
    the default `ollama` provider) with native tool-calling, the way
    OpenAI/Anthropic providers already do (see §5). This is partially done:
    OpenAI and Anthropic use real structured tool-calling; Ollama still uses
    regex parsing of `READ_FILE:`/`WRITE_FILE:`/etc. text commands because
    most local models don't reliably support function-calling the way hosted
    models do. Worth revisiting if Ollama's tool-calling support matures.
- A long, multi-session effort (see §7, "Recent history") has been spent
  finding and fixing real bugs via a repeatable process: write/extend unit
  tests, reproduce bugs live against a real local Ollama server, fix, add
  regression tests, verify no new lint debt, open a PR, wait for green CI,
  squash-merge. As of this handover, **~20 real bugs have been found and
  fixed this way across rounds 6–8 alone** (see git log on `main`, PRs
  #23–#38). The codebase is in good, well-tested shape, but this process is
  open-ended — there is no reason to believe all bugs are gone, and the user
  has repeatedly asked to keep looping on "test the CLI, find bugs, fix them
  one at a time" as an ongoing improvement loop.

## 4. Getting started on a new machine

```bash
git clone https://github.com/iroy2000/coding-agent.git
cd coding-agent

python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env   # adjust OLLAMA_MODEL etc. if needed
```

Install Ollama and pull at least one model to do live/manual testing (unit
tests use mocks and don't need this, but hands-on verification does):

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2          # small/fast, good for quick smoke tests
ollama pull codellama         # repo's own default model (OLLAMA_MODEL=codellama:latest)
```

Run the test suite:

```bash
pytest                                            # full suite, ~5-6s, 414 tests
pytest --cov=src/coding_agent --cov-report=term   # with coverage
ruff check src/ tests/                            # lint (informational in CI)
mypy src/                                         # type check
```

Try the CLI end-to-end:

```bash
coding-agent init
coding-agent chat --yes      # --yes auto-approves writes/commands, convenient for scripted testing
```

No OpenAI or Anthropic API keys are available in most sandboxed dev
environments — changes to `openai_client.py`/`anthropic_client.py` can only
be verified via unit tests / mocked SDK calls (see tests for examples of
this pattern), not live end-to-end. Ollama-provider changes should always be
live-verified with a real local Ollama server in addition to unit tests.

## 5. Architecture

```
src/coding_agent/
├── cli.py              # Typer CLI entry point: chat, init, config, history,
│                        #   undo, serve, --version
├── agent.py            # Core agent loop (CodingAgent class): builds context,
│                        #   calls the LLM, parses/executes actions
│                        #   (READ_FILE/WRITE_FILE/EDIT_FILE/LIST_FILES/
│                        #   SEARCH_FILES/RUN_COMMAND), manages conversation
│                        #   history + auto-commit
├── llm/
│   ├── base.py          # LLMProvider abstract interface (generate,
│                        #   stream_generate, generate_with_tools)
│   ├── factory.py       # create_llm_client()/get_active_model()/
│                        #   test_llm_connection() — dispatches on
│                        #   Config.llm_provider ("ollama"|"openai"|"anthropic")
│   ├── ollama_client.py # default provider; uses prompts.py's text-format
│                        #   command protocol (no native tool-calling)
│   ├── openai_client.py # uses OpenAI's native function/tool-calling API
│   ├── anthropic_client.py # uses Anthropic's native tool-calling API;
│                        #   NOTE: Anthropic requires strict user/assistant
│                        #   role alternation in `messages` — see §6
│   ├── tool_schemas.py  # TOOL_DEFINITIONS shared JSON-schema tool
│                        #   definitions used by the OpenAI/Anthropic
│                        #   native tool-calling paths
│   └── prompts.py       # system prompt + the READ_FILE/WRITE_FILE/etc.
│                        #   text-command protocol docs sent to Ollama
├── tools/
│   ├── file_manager.py  # workspace-sandboxed read/write/edit/list/search;
│                        #   ripgrep-backed search with a pure-Python
│                        #   fallback when `rg` isn't installed
│   └── git_manager.py   # auto-commit + safe undo (only reverts agent's own
│                        #   commits, detected via a commit message marker)
├── mcp/
│   ├── server.py        # in-process dict-based MCPServer (exported as
│                        #   coding_agent.mcp.MCPServer) — used for the
│                        #   startup tool-listing banner in `serve`, and
│                        #   has its own unit test suite
│   ├── stdio_server.py  # the ACTUAL stdio JSON-RPC MCP protocol server
│                        #   used by `coding-agent serve --transport stdio`
│                        #   (the only implemented transport — `http` is a
│                        #   stub that errors out)
│   └── client.py        # MCPClient/MCPClientManager — client-side code for
│                        #   *connecting to* external MCP servers; currently
│                        #   not wired into any CLI command (effectively
│                        #   unused/incomplete feature, not a bug)
├── storage/
│   └── history.py       # session persistence under ~/.coding-agent/history/,
│                        #   list/view/delete/export (json/txt/md)
└── utils/
    ├── config.py         # .env-backed Config class + validate()
    └── display.py        # Rich-based terminal output helpers
```

**Important architectural quirk: `mcp/server.py` vs `mcp/stdio_server.py` are
two separate implementations of overlapping functionality that do NOT share
code.** Only `stdio_server.py` is on the path real MCP clients (Claude
Desktop, etc.) actually use, since HTTP transport isn't implemented.
`server.py`'s `MCPServer` class is nonetheless part of the public, tested
API surface (`coding_agent.mcp.MCPServer`). **Any fix to one does not
automatically apply to the other** — this has caused several real bugs
(schema/handler drift, inconsistent error handling) found and fixed across
multiple rounds. Check both whenever touching MCP-related behavior.

## 6. Known quirks / gotchas worth remembering

These were each the root cause of at least one real, previously-shipped bug.
Keep them in mind when touching related code:

1. **Rich markup swallows brackets silently.** `rich.console.Console.print()`
   and `Table.add_row()`/`Panel()` treat `[...]` as markup syntax; any
   dynamic/untrusted string interpolated into an f-string passed to these
   without `rich.markup.escape()` can have bracketed content silently
   deleted (not printed literally, no error/exception). Always wrap dynamic
   values with `from rich.markup import escape`. This class of bug has been
   swept and fixed project-wide at least twice (rounds 6–8); if you add new
   `console.print(f"...")` calls, escape dynamic content.
2. **Anthropic requires strict `user`/`assistant` role alternation** in the
   `messages` list — unlike OpenAI/Ollama, which tolerate consecutive
   same-role messages or system messages interleaved anywhere. Code that
   filters/merges messages for Anthropic (`_split_system_and_messages` in
   `anthropic_client.py`) must guard against leaving two same-role messages
   adjacent after filtering (fixed in PR #34).
3. **`OllamaClient.generate()`/`stream_generate()` must defensively copy
   `context`** (`list(context or [])`) rather than aliasing the caller's own
   list, matching `OpenAIProvider`'s pattern — otherwise `.append()` mutates
   state the caller may reuse across calls (fixed in PR #35).
4. **`EDIT_FILE` must reject an empty `old_text`.** Python's
   `str.replace("", x)` doesn't no-op; it inserts `x` at every character
   boundary. A model hallucinating an empty `OLD:` block (a real, observed
   failure mode especially with smaller models) would otherwise silently
   corrupt the target file (fixed in PR #36 — `FileManager.edit_file` now
   rejects `old_text == ""` explicitly).
5. **Don't parse ripgrep's plain-text `path:line:content` output by naively
   splitting on `:`** — paths can legitimately contain colons. Use
   `rg --json` and read the structured `path`/`line_number`/`lines` fields
   instead (fixed in PR #37, in `FileManager._search_files_ripgrep`).
6. **MCP dual-implementation drift** (see §5) — schema/handler
   inconsistencies between `server.py` and `stdio_server.py` have shipped
   more than once (argument name mismatches, missing schema properties,
   inconsistent `max_depth` defaults for `list_files`). Cross-check both
   when touching MCP tool definitions.
7. **Shell safety tool blocks backticks in `git commit -m`/`gh pr create
   --body`** when working in this kind of sandboxed agent environment —
   write the message to a temp file and use `git commit -F <file>` /
   `gh pr create --body-file <file>` instead.

## 7. Recent history (how we got here)

This project has gone through a documented, multi-round "test the CLI,
find real bugs via hands-on usage + unit tests, fix one at a time, verify,
ship a PR per fix" loop, driven by the repo owner's standing instruction to
keep improving the CLI this way indefinitely. Concretely, each fix in PRs
#23 through #38 followed this pattern:

1. Investigate a module via code reading, live CLI usage against a real
   Ollama server, or targeted exploration subagents.
2. Reproduce the suspected bug with a minimal standalone script first.
3. Root-cause it, fix it with a surgical change.
4. Add/update regression tests that would have caught it on the old code.
5. Run the full test suite (`pytest`) and a `ruff check` before/after diff
   (via `git stash`) to confirm no new lint debt was introduced.
6. Live-verify with a real local Ollama server end-to-end where applicable
   (not possible for OpenAI/Anthropic-only changes — no API keys available).
7. Commit on a `fix/*` branch, push, `gh pr create`, wait for CI
   (~45–90s for all 3 Python versions), then
   `gh pr merge <N> --squash --admin --delete-branch`, and re-sync `main`.

If you (human or agent) are picking this up: **this loop is still open**.
The repo owner has asked, verbatim and repeatedly, to "keep improving this
coding agent cli, test the cli, check if there are bugs, if so fix it one by
one, keep looping until you see no bugs." There is no fixed end state for
this — use judgment about when a pass has diminishing returns, but the
default expectation is to keep finding and fixing real, reproducible bugs
using the process above, not to treat the codebase as "done."

Good places to keep looking (not yet exhaustively audited as of this
writing):
- `mcp/stdio_server.py`'s less-covered handlers (large sections at 51%
  coverage, see `pytest --cov` output).
- `storage/history.py`'s uncovered branches (session pruning, export edge
  cases).
- `tools/git_manager.py`'s uncovered lines (auto-commit/undo edge cases
  around dirty working trees, detached HEAD, etc.).
- Symlink-based workspace-boundary edge cases in `file_manager.py`'s
  `list_files`/`_search_files_python` fallback (flagged as theoretical
  during a review but not yet fixed — a symlinked directory pointing
  outside the workspace is followed during directory traversal without an
  explicit safety check, unlike the main read/write/edit path which does
  check). Worth a dedicated look if you want a next concrete task.
- MCP `list_files` has inconsistent default traversal depth between
  `server.py` (defaults to `FileManager`'s own default, 3) and
  `stdio_server.py` (hardcodes 5) — not yet reconciled, noted but
  deliberately left alone in PR #38 as lower-priority than the other fixes
  in that PR.

## 8. About the other docs in this repo

There is a large set of `.md` files in the repo root
(`PROJECT_STATUS.md`, `PLANNING.md`, `ROADMAP.md`, `PROGRESS.md`,
`MCP_*.md`, `STEP_*_COMPLETE.md`, `PHASE_2_PLAN.md`,
`ENTERPRISE_PRODUCT_DOC.md`, `TODAY_ACCOMPLISHMENTS.md`,
`EMOJI_REMOVAL.md`) and an `architecture/` directory. **Almost all of these
are gitignored** (`.gitignore` ignores `*.md` except `README.md`,
`CONTRIBUTING.md`, `EXAMPLES.md`, and `USAGE_GUIDE.md`) — they exist only as
local scratch/planning files on whichever machine created them and were
**never pushed to GitHub**. They mostly describe a much earlier, ~67%-done
MVP state (no tests, no multi-provider support, no MCP server, no git
integration) and are now significantly out of date; don't trust them over
this file, the README, or the actual code/tests/git history.

If you're setting up on a new machine and don't see those files, that's
expected — they were local-only. This `HANDOVER.md` (tracked in git) is the
intended replacement as the up-to-date, durable source of truth, along with:
- `README.md` — user-facing overview, install, usage, config reference.
- `CONTRIBUTING.md` — dev setup / PR conventions for contributors.
- `EXAMPLES.md` / `USAGE_GUIDE.md` — worked usage examples.
- GitHub Issues — active roadmap items (#8, #12 as of this writing).
- `git log` on `main` — the real changelog; every merged PR has a
  descriptive title and body explaining what was found/fixed and how it was
  verified.

## 9. Testing conventions

- Framework: `pytest` + `pytest-asyncio` (strict mode) + `pytest-cov`.
  Config lives in `pyproject.toml`.
- Tests mock the Ollama/OpenAI/Anthropic SDK clients (`unittest.mock`) for
  unit coverage; there is no built-in live-Ollama test tier — live
  verification during development is done manually (see the bash-tool-based
  patterns used throughout this project's PR history: pipe scripted input
  into `coding-agent chat --yes` against a real workspace and real local
  Ollama server).
- Regression-test convention: when fixing a bug, add a test whose name and
  docstring explain *why* the old behavior was wrong (not just what the new
  behavior is) — see e.g. `test_merges_consecutive_same_role_messages`,
  `test_edit_file_rejects_empty_old_text`, `test_generate_does_not_mutate_caller_context`
  for examples of this style.
- `ruff` is informational only in CI (`continue-on-error: true`), but PRs in
  this project's history consistently verify no *new* lint debt was
  introduced by diffing `ruff check` output before/after a change (via
  `git stash`), even though it isn't a hard gate.
