#!/usr/bin/env bash
# Stage 6: Respond to review comments on an open PR.
#
# Usage: 6_respond_to_review.sh <pr-number>
#
# Fetches unresolved review comments + issue-style PR comments and, if any
# exist, spawns a Copilot session in the PR's own branch worktree to
# address them, push fixes, and reply.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source lib.sh
require_gh_auth
cd "$REPO_ROOT"

PR_NUMBER="${1:?Usage: 6_respond_to_review.sh <pr-number>}"
WORKTREE_DIR="$LOOP_STATE_DIR/worktree-pr-$PR_NUMBER"

COMMENTS="$(gh pr view "$PR_NUMBER" --json comments,reviews \
    --jq '(.comments // []) + (.reviews // []) | map(.body) | join("\n---\n")')"

if [ -z "$COMMENTS" ] || [ "$COMMENTS" = "null" ]; then
    log "No comments to address on PR #$PR_NUMBER."
    exit 0
fi

BRANCH="$(gh pr view "$PR_NUMBER" --json headRefName --jq .headRefName)"
git worktree remove --force "$WORKTREE_DIR" 2>/dev/null || true
git worktree prune
git fetch origin "$BRANCH" --quiet
git worktree add "$WORKTREE_DIR" "origin/$BRANCH" --quiet

PROMPT_FILE="$LOOP_STATE_DIR/6_review_prompt_$PR_NUMBER.txt"
RESULT_FILE="$LOOP_STATE_DIR/6_review_result_$PR_NUMBER.txt"

cat > "$PROMPT_FILE" <<EOF
You are addressing review feedback on PR #$PR_NUMBER of "coding-agent-cli".
You are already on the PR's branch in this worktree.

Review/PR comments to address:
$COMMENTS

1. Make the requested changes (or explain in a PR comment why you're not,
   if a request is out of scope/incorrect).
2. Re-run the full test suite and confirm it passes.
3. Commit and push your fixes to this same branch.
4. Post a PR comment (via 'gh pr comment $PR_NUMBER') summarizing what you
   addressed.
EOF

(cd "$WORKTREE_DIR" && run_copilot "$PROMPT_FILE" "$RESULT_FILE")
log "Review-response session finished:"
cat "$RESULT_FILE"
git worktree remove --force "$WORKTREE_DIR" 2>/dev/null || true
git worktree prune
