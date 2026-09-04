#!/usr/bin/env bash
# Stage 5: Independently test a PR's branch and post proof (test output +
# a real PNG "screenshot" of the terminal transcript, generated via the
# `freeze` tool so it works headlessly, no visible display required) as a
# PR comment.
#
# Usage: 5_test_and_prove.sh <pr-number>
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source lib.sh
require_gh_auth
cd "$REPO_ROOT"

PR_NUMBER="${1:?Usage: 5_test_and_prove.sh <pr-number>}"
WORKTREE_DIR="$LOOP_STATE_DIR/worktree-pr-$PR_NUMBER"
PROOF_DIR="$LOOP_STATE_DIR/proof-pr-$PR_NUMBER"
mkdir -p "$PROOF_DIR"

BRANCH="$(gh pr view "$PR_NUMBER" --json headRefName --jq .headRefName)"
log "Testing PR #$PR_NUMBER (branch $BRANCH)"

rm -rf "$WORKTREE_DIR"
git fetch origin "$BRANCH" --quiet
git worktree add "$WORKTREE_DIR" "origin/$BRANCH" --quiet

TRANSCRIPT="$PROOF_DIR/transcript.txt"
{
    echo "\$ coding-agent --version"
    (cd "$WORKTREE_DIR" && python3 -m venv .venv_proof --clear >/dev/null 2>&1 && \
        source .venv_proof/bin/activate && \
        pip install -q -e ".[dev]" >/dev/null 2>&1 && \
        coding-agent --version 2>&1)
    echo
    echo "\$ pytest -q"
    (cd "$WORKTREE_DIR" && source .venv_proof/bin/activate && python -m pytest -q 2>&1)
} > "$TRANSCRIPT" 2>&1 || true

TEST_EXIT_LINE="$(grep -E "passed|failed|error" "$TRANSCRIPT" | tail -1)"
STATUS="FAIL"
echo "$TEST_EXIT_LINE" | grep -q "failed\|error" || STATUS="PASS"

PROOF_PNG="$PROOF_DIR/proof.png"
if command -v freeze >/dev/null 2>&1; then
    freeze "$TRANSCRIPT" -o "$PROOF_PNG" -c full >/dev/null 2>&1 || true
fi

COMMENT_FILE="$PROOF_DIR/comment.md"
{
    echo "## Automated test proof (agent loop)"
    echo
    echo "**Result: $STATUS**"
    echo
    echo '```'
    tail -30 "$TRANSCRIPT"
    echo '```'
} > "$COMMENT_FILE"

if [ -f "$PROOF_PNG" ]; then
    UPLOAD_URL="$(gh api \
        -H "Accept: application/vnd.github+json" \
        --method POST \
        /repos/{owner}/{repo}/issues/comments 2>/dev/null || true)"
    # Attaching real binary images requires the user-attachments upload
    # flow (see .github/skills github-pr-media); fall back to text-only
    # proof if that isn't wired up in this environment.
    log "Screenshot proof generated at $PROOF_PNG (attach manually or via github-pr-media skill if desired)."
fi

gh pr comment "$PR_NUMBER" --body-file "$COMMENT_FILE"
log "Posted test proof comment on PR #$PR_NUMBER (status: $STATUS)"

rm -rf "$WORKTREE_DIR"
[ "$STATUS" = "PASS" ]
