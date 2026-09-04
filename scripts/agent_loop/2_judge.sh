#!/usr/bin/env bash
# Stage 2: Judge/researcher pass over the brainstormed ideas.
#
# Takes scripts/agent_loop's ideas.json and asks a fresh Copilot session
# (acting as a skeptical judge, with no memory of "having proposed" the
# ideas) to research feasibility against the actual codebase and pick at
# most ONE idea worth turning into an issue. This adversarial second pass
# is what keeps the loop from filing low-value or already-solved issues.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source lib.sh
cd "$REPO_ROOT"

IDEAS_FILE="$LOOP_STATE_DIR/ideas.json"
[ -s "$IDEAS_FILE" ] || { log "No ideas file at $IDEAS_FILE; run 1_brainstorm.sh first"; exit 1; }

PROMPT_FILE="$LOOP_STATE_DIR/2_judge_prompt.txt"
VERDICT_FILE="$LOOP_STATE_DIR/verdict.json"

cat > "$PROMPT_FILE" <<EOF
You are a skeptical staff engineer acting as judge + researcher for the
"coding-agent-cli" project. You did NOT write the following candidate
ideas and have no attachment to them; your job is to find reasons to
reject bad ones.

Candidate ideas (JSON array):
$(cat "$IDEAS_FILE")

For each idea, actually inspect the codebase (grep/view relevant files) to
verify: (a) it isn't already implemented, (b) it isn't a duplicate of an
already-open GitHub issue (check with 'gh issue list'), (c) the proposal
is technically sound given the actual code structure.

Then pick AT MOST ONE idea that is genuinely worth an issue (reject all if
none clear the bar). Respond with ONLY a raw JSON object (no markdown
fences, no commentary) of this exact shape:
{"approved": true|false, "title": "...", "body_markdown": "full issue body in markdown, including a Problem, Why it matters, and Suggested approach section", "rejected_reasons": ["reason for each rejected idea, or empty array if approved is false with no candidates worth mentioning"]}
EOF

run_copilot "$PROMPT_FILE" "$VERDICT_FILE"
log "Verdict written to $VERDICT_FILE"
cat "$VERDICT_FILE"
