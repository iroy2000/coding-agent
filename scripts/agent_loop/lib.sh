#!/usr/bin/env bash
# Shared helpers for the agentic self-improvement loop.
#
# The loop uses the GitHub Copilot CLI (`copilot`) itself, invoked
# non-interactively via `-p/--prompt`, as the "brain" for every stage
# (brainstorm, judge, implement, review-response, test/prove). This file
# centralizes the safety defaults so every stage is capped and auditable.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOOP_STATE_DIR="${LOOP_STATE_DIR:-$REPO_ROOT/.agent_loop_state}"
mkdir -p "$LOOP_STATE_DIR"

# Cap per-invocation spend/turns so a single stage can never run away.
# Override via env vars if you need more headroom for a harder task.
COPILOT_MAX_CREDITS="${COPILOT_MAX_CREDITS:-40}"
COPILOT_MODEL="${COPILOT_MODEL:-claude-sonnet-5}"

log() {
    echo "[agent-loop] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2
}

# run_copilot <prompt-file> <output-file> [extra copilot args...]
#
# Runs Copilot CLI non-interactively with a bounded credit budget, no
# ability to touch git history destructively, and captures its final
# response to a plain text file (silent mode = response only, no stats).
run_copilot() {
    local prompt_file="$1"
    local output_file="$2"
    shift 2
    log "Running copilot (budget=$COPILOT_MAX_CREDITS credits) -> $output_file"
    copilot \
        --silent \
        --allow-all-tools \
        --deny-tool='shell(git push origin main)' \
        --deny-tool='shell(git push --force*)' \
        --no-ask-user \
        --max-ai-credits "$COPILOT_MAX_CREDITS" \
        --model "$COPILOT_MODEL" \
        --prompt "$(cat "$prompt_file")" \
        "$@" \
        > "$output_file" 2>"$output_file.stderr" || {
            log "copilot invocation failed; see $output_file.stderr"
            return 1
        }
}

require_gh_auth() {
    gh auth status >/dev/null 2>&1 || {
        log "gh CLI is not authenticated. Run 'gh auth login' first."
        exit 1
    }
}
