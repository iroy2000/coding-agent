# scripts/

Developer-only helper scripts. **None of these are part of the automated
test suite** (`pytest` only collects from `tests/`, per `testpaths` in
`pyproject.toml`) — they're standalone scripts for manual debugging,
demos, and live protocol checks during development.

- `debug/` — ad-hoc scripts for poking at Ollama responses and regex parsing
  while debugging the agent's action-parsing logic.
- `manual_tests/` — pre-pytest smoke-test scripts that exercise `CodingAgent`
  and `FileManager` by running them directly and printing output. Superseded
  by the real automated suite in `tests/`, kept around for quick manual
  sanity checks against a live Ollama instance.
- `mcp/` — manual MCP protocol scripts. These start a real `coding-agent
  serve` process and exchange JSON-RPC messages over stdio to validate the
  MCP stdio server end-to-end (`test_mcp_integration.py`,
  `test_mcp_protocol.py`), plus a startup validator (`validate_mcp_server.py`).
- `sandbox/` — gitignored scratch space for one-off experiments; nothing
  here is tracked or published.
- `agent_loop/` — the agentic self-improvement loop: brainstorm ideas ->
  judge/research them -> file a GitHub issue -> spawn a coding agent to
  implement it and open a PR -> independently test + post proof. See
  `agent_loop/README.md` for the full design and safety guardrails.

Run any of these from the repo root, e.g.:

```bash
python scripts/debug/debug_ollama.py
python scripts/mcp/validate_mcp_server.py
```
