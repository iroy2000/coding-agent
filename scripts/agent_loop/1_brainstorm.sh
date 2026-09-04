#!/usr/bin/env bash
# Stage 1: Brainstorm candidate enhancements/ideas for the project.
#
# Reads the README, current open issues, and (if present) the local
# ROADMAP.md for context, then asks Copilot to propose a short list of
# concrete, scoped enhancement ideas as JSON.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source lib.sh

require_gh_auth
cd "$REPO_ROOT"

OPEN_ISSUES="$(gh issue list --state open --limit 50 --json number,title,labels \
    --jq '.[] | "#\(.number) [\(.labels | map(.name) | join(","))] \(.title)"' 2>/dev/null || true)"

PROMPT_FILE="$LOOP_STATE_DIR/1_brainstorm_prompt.txt"
IDEAS_FILE="$LOOP_STATE_DIR/ideas.json"

cat > "$PROMPT_FILE" <<EOF
You are brainstorming for "$PROJECT_NAME": $PROJECT_DESCRIPTION.

Read README.md and, if it exists, ROADMAP.md in the current directory for
context on what already exists and what's already planned.

Here are the currently OPEN GitHub issues (do not propose duplicates of
these):
$OPEN_ISSUES

Propose exactly 3 NEW, concrete, scoped enhancement ideas that would move
this project closer to mainstream adoption (compare it to the best-in-class
tools/products in its category). Each idea must be small enough to be
implemented and fully tested in a single focused pull request (do not
propose vague, multi-week initiatives).

Respond with ONLY a raw JSON array (no markdown fences, no commentary),
where each element has this exact shape:
{"title": "short imperative title", "problem": "1-2 sentence problem statement", "proposal": "1-3 sentence concrete proposal", "effort": "small|medium|large", "impact": "low|medium|high"}
EOF

run_copilot "$PROMPT_FILE" "$IDEAS_FILE"
extract_json "$IDEAS_FILE"
log "Ideas written to $IDEAS_FILE"
cat "$IDEAS_FILE"
