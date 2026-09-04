#!/usr/bin/env bash
# Orchestrator: runs one full cycle of the agentic self-improvement loop.
#
#   1) brainstorm ideas
#   2) judge/research them, approve at most one
#   3) file it as a GitHub issue (label: ai-generated)
#   4) spawn a coding agent to implement it and open a PR
#   5) independently test the PR branch and post proof as a PR comment
#
# By design this NEVER merges a PR automatically — a human always reviews
# and merges. Run this on a schedule (cron/launchd) to "keep the loop
# going"; each run is idempotent and state-isolated under
# .agent_loop_state/ (gitignored).
#
# Usage:
#   scripts/agent_loop/run_cycle.sh                # full cycle: new idea -> issue -> PR -> proof
#   scripts/agent_loop/run_cycle.sh --issue 6       # skip brainstorm/judge, implement an existing issue
#   scripts/agent_loop/run_cycle.sh --review 12     # just run the review-response stage on an open PR
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source lib.sh

MODE="full"
TARGET=""
if [ "${1:-}" = "--issue" ]; then
    MODE="issue"
    TARGET="${2:?Usage: run_cycle.sh --issue <number>}"
elif [ "${1:-}" = "--review" ]; then
    MODE="review"
    TARGET="${2:?Usage: run_cycle.sh --review <pr-number>}"
fi

if [ "$MODE" = "review" ]; then
    ./6_respond_to_review.sh "$TARGET"
    exit 0
fi

if [ "$MODE" = "full" ]; then
    log "=== Stage 1/5: brainstorm ==="
    ./1_brainstorm.sh
    log "=== Stage 2/5: judge ==="
    ./2_judge.sh
    log "=== Stage 3/5: create issue ==="
    ISSUE_NUMBER="$(./3_create_issue.sh | tail -1)"
    if [ -z "$ISSUE_NUMBER" ]; then
        log "No issue approved/created this cycle. Loop ends here for now."
        exit 0
    fi
else
    ISSUE_NUMBER="$TARGET"
fi

log "=== Stage 4/5: implement issue #$ISSUE_NUMBER ==="
./4_implement.sh "$ISSUE_NUMBER"

PR_URL_FILE="$LOOP_STATE_DIR/last_pr_url.txt"
if [ ! -s "$PR_URL_FILE" ]; then
    log "No PR was opened; stopping before the test/proof stage."
    exit 1
fi
PR_NUMBER="$(basename "$(cat "$PR_URL_FILE")")"

log "=== Stage 5/5: test + prove PR #$PR_NUMBER ==="
./5_test_and_prove.sh "$PR_NUMBER"

log "Cycle complete. PR #$PR_NUMBER is ready for human review at $(cat "$PR_URL_FILE")."
