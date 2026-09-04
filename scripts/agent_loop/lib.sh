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

# Project identity used in prompts below. Auto-detected from the GitHub
# repo itself (so this whole scripts/agent_loop/ directory is portable —
# copy it into any repo and it adapts) but overridable via env vars if
# auto-detection is unavailable/wrong (e.g. no network, private repo
# without gh access yet, or you want a more specific description than the
# repo's one-line GitHub description).
PROJECT_NAME="${PROJECT_NAME:-$(cd "$REPO_ROOT" && gh repo view --json name --jq .name 2>/dev/null || basename "$REPO_ROOT")}"
PROJECT_DESCRIPTION="${PROJECT_DESCRIPTION:-$(cd "$REPO_ROOT" && gh repo view --json description --jq .description 2>/dev/null || echo "a software project")}"

# Cap per-invocation spend/turns so a single stage can never run away.
# Override via env vars if you need more headroom for a harder task.
# copilot enforces a hard floor of 30 credits; 40 leaves a little slack.
COPILOT_MAX_CREDITS="${COPILOT_MAX_CREDITS:-40}"
COPILOT_MODEL="${COPILOT_MODEL:-claude-sonnet-5}"

# Tools the nested agent is NEVER allowed to use, regardless of stage.
# These are deliberately broader than just "don't push to main": a nested
# agent implementing a GitHub issue has no legitimate reason to touch repo
# settings, CI workflows, release tags, or merge/delete anything itself —
# all of that requires a human. (See issue #4 in this repo for why a
# denylist alone is an imperfect safety net; this is defense-in-depth on
# top of --no-ask-user, not a sandbox.)
COPILOT_DENY_TOOLS=(
    --deny-tool='shell(git push origin main)'
    --deny-tool='shell(git push origin main:*)'
    --deny-tool='shell(git push --force*)'
    --deny-tool='shell(git push -f*)'
    --deny-tool='shell(git tag*)'
    --deny-tool='shell(git branch -D main)'
    --deny-tool='shell(gh pr merge*)'
    --deny-tool='shell(gh pr close*)'
    --deny-tool='shell(gh repo edit*)'
    --deny-tool='shell(gh repo delete*)'
    --deny-tool='shell(gh api*repos*/branches*)'
    --deny-tool='shell(gh workflow*)'
    --deny-tool='shell(gh secret*)'
    --deny-tool='shell(sudo*)'
    --deny-tool='shell(rm -rf /*)'
    --deny-tool='shell(rm -rf ~*)'
)

log() {
    echo "[agent-loop] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2
}

# run_copilot <prompt-file> <output-file> [extra copilot args...]
#
# Runs Copilot CLI non-interactively with a bounded credit budget and the
# COPILOT_DENY_TOOLS safety list applied, capturing its final response to
# a plain text file (silent mode = response only, no stats) plus a JSON
# usage-tracking sidecar file for cost auditing.
run_copilot() {
    local prompt_file="$1"
    local output_file="$2"
    shift 2
    log "Running copilot (budget=$COPILOT_MAX_CREDITS credits) -> $output_file"
    copilot \
        --silent \
        --allow-all-tools \
        "${COPILOT_DENY_TOOLS[@]}" \
        --no-ask-user \
        --max-ai-credits "$COPILOT_MAX_CREDITS" \
        --model "$COPILOT_MODEL" \
        --usage-output-file "$output_file.usage.json" \
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

# extract_json <file>
#
# Models sometimes wrap "raw JSON only" responses in markdown code fences
# anyway. Strip a leading/trailing ```json ... ``` or ``` ... ``` fence (if
# present) in place, then validate the result actually parses as JSON,
# failing loudly with the raw content shown for debugging instead of a
# cryptic python traceback deeper in the pipeline.
extract_json() {
    local file="$1"
    python3 - "$file" <<'PYEOF'
import json
import re
import sys

path = sys.argv[1]
raw = open(path, encoding="utf-8").read().strip()
fenced = re.match(r"^```(?:json)?\s*\n(.*?)\n?```$", raw, re.DOTALL)
if fenced:
    raw = fenced.group(1).strip()
try:
    json.loads(raw)
except json.JSONDecodeError as e:
    sys.stderr.write(f"extract_json: model output at {path} is not valid JSON: {e}\n")
    sys.stderr.write(f"--- raw content ---\n{raw}\n")
    sys.exit(1)
open(path, "w", encoding="utf-8").write(raw)
PYEOF
}

# with_lock <lockname> <command...>
#
# Serializes full-cycle runs so a scheduled cron/launchd job never overlaps
# with a still-running previous cycle (which would race on shared
# .agent_loop_state/ files and worktrees). Implemented with `mkdir`
# (atomic on all POSIX filesystems) rather than `flock`, since flock is a
# Linux-only util-linux tool with no equivalent shipped on macOS, and the
# `exec {fd}>file` auto-fd syntax needs bash >= 4.1 (macOS ships bash 3.2).
with_lock() {
    local lockname="$1"
    shift
    local lockdir="$LOOP_STATE_DIR/$lockname.lockdir"
    if ! mkdir "$lockdir" 2>/dev/null; then
        log "Another agent-loop run holds the '$lockname' lock ($lockdir exists). Exiting."
        exit 1
    fi
    # shellcheck disable=SC2064 (intentionally expand $lockdir now)
    trap "rmdir '$lockdir' 2>/dev/null" EXIT
    "$@"
}
