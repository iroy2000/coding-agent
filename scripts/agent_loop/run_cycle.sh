#!/usr/bin/env bash
# Orchestrator: runs one full cycle of the agentic self-improvement loop.
#
#   0) housekeeping: prune worktrees for already-merged/closed agent PRs
#   1) brainstorm ideas         (skipped if there's an unimplemented
#   2) judge/research them       backlog issue already waiting — see
#   3) file a GitHub issue       "Backlog-first" below)
#   4) spawn a coding agent to implement it and open a PR
#   5) independently test the PR branch and post proof as a PR comment
#
# By design this NEVER merges a PR automatically — a human always reviews
# and merges. Run this on a schedule (cron/launchd) to "keep the loop
# going"; a flock-based lock (see lib.sh's with_lock) makes it safe to
# schedule frequently without overlapping runs.
#
# Usage:
#   scripts/agent_loop/run_cycle.sh                # backlog issue if any, else brainstorm a new one -> PR -> proof
#   scripts/agent_loop/run_cycle.sh --brainstorm    # force a new idea even if a backlog issue exists
#   scripts/agent_loop/run_cycle.sh --issue 6       # skip brainstorm/judge, implement a specific existing issue
#   scripts/agent_loop/run_cycle.sh --review 12     # just run the review-response stage on an open PR
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source lib.sh

MODE="auto"
TARGET=""
case "${1:-}" in
    --issue) MODE="issue"; TARGET="${2:?Usage: run_cycle.sh --issue <number>}" ;;
    --review) MODE="review"; TARGET="${2:?Usage: run_cycle.sh --review <pr-number>}" ;;
    --brainstorm) MODE="brainstorm" ;;
esac

main() {
    ./cleanup.sh || true

    if [ "$MODE" = "review" ]; then
        ./6_respond_to_review.sh "$TARGET"
        return 0
    fi

    local issue_number=""
    if [ "$MODE" = "issue" ]; then
        issue_number="$TARGET"
    else
        # Backlog-first: don't keep piling up new ideas while an
        # already-approved one hasn't even been implemented yet.
        if [ "$MODE" != "brainstorm" ]; then
            issue_number="$(./find_backlog_issue.sh || true)"
        fi

        if [ -n "$issue_number" ]; then
            log "Found unimplemented backlog issue #$issue_number; implementing it before brainstorming anything new."
        else
            log "=== Stage 1: brainstorm ==="
            ./1_brainstorm.sh
            log "=== Stage 2: judge ==="
            ./2_judge.sh
            log "=== Stage 3: create issue ==="
            issue_number="$(./3_create_issue.sh | tail -1)"
            if [ -z "$issue_number" ]; then
                log "No issue approved/created this cycle. Loop ends here for now."
                return 0
            fi
        fi
    fi

    log "=== Stage 4: implement issue #$issue_number ==="
    ./4_implement.sh "$issue_number"

    local pr_url_file="$LOOP_STATE_DIR/last_pr_url.txt"
    if [ ! -s "$pr_url_file" ]; then
        log "No PR was opened; stopping before the test/proof stage."
        return 1
    fi
    local pr_number
    pr_number="$(basename "$(cat "$pr_url_file")")"

    log "=== Stage 5: test + prove PR #$pr_number ==="
    ./5_test_and_prove.sh "$pr_number"

    local pr_url
    pr_url="$(cat "$pr_url_file")"
    log "Cycle complete. PR #$pr_number is ready for human review at $pr_url."

    # Best-effort local notification (macOS). Never fails the cycle.
    if command -v osascript >/dev/null 2>&1; then
        osascript -e "display notification \"PR #$pr_number ready for review\" with title \"$PROJECT_NAME agent loop\"" >/dev/null 2>&1 || true
    fi
}

with_lock "run_cycle" main
