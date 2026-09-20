#!/usr/bin/env bash
# Housekeeping: remove local worktrees/branches left behind by the loop for
# issues whose PR has since been merged or closed, so .agent_loop_state/
# doesn't grow unbounded across many cycles. Safe to run anytime (e.g. at
# the start of every run_cycle.sh invocation).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source lib.sh
require_gh_auth
cd "$REPO_ROOT"

git worktree prune

for dir in "$LOOP_STATE_DIR"/worktree-issue-*; do
    [ -d "$dir" ] || continue
    issue_num="${dir##*worktree-issue-}"
    branch="agent/issue-$issue_num"
    pr_state="$(gh pr list --state all --head "$branch" --json state --jq '.[0].state // empty' 2>/dev/null || true)"
    if [ "$pr_state" = "MERGED" ] || [ "$pr_state" = "CLOSED" ]; then
        log "Cleaning up worktree/branch for issue #$issue_num (PR $pr_state)"
        git worktree remove --force "$dir" 2>/dev/null || true
        git branch -D "$branch" 2>/dev/null || true
    fi
done
git worktree prune
