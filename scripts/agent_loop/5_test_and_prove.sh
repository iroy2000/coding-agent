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

git worktree remove --force "$WORKTREE_DIR" 2>/dev/null || true
git worktree prune
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
IMAGE_URL=""
if command -v freeze >/dev/null 2>&1; then
    freeze "$TRANSCRIPT" -o "$PROOF_PNG" -c full >/dev/null 2>&1 || true
fi

if [ -f "$PROOF_PNG" ]; then
    REPO_SLUG="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
    REPO_ID="$(gh api "repos/$REPO_SLUG" --jq .id 2>/dev/null || true)"
    case "$REPO_ID" in
        ''|*[!0-9]*)
            log "Could not resolve repository_id for $REPO_SLUG; skipping image upload, text proof only."
            ;;
        *)
            TOKEN="$(gh auth token)"
            IMAGE_URL="$(curl --fail-with-body -sS -X POST \
                "https://uploads.github.com/user-attachments/assets" \
                --url-query "name=agent-loop-proof-pr-$PR_NUMBER.png" \
                --url-query "content_type=image/png" \
                --url-query "repository_id=$REPO_ID" \
                -H "Content-Type: application/octet-stream" \
                -H "X-GitHub-Api-Version: 2022-11-28" \
                -H "Authorization: Bearer $TOKEN" \
                --data-binary "@$PROOF_PNG" 2>/dev/null | jq -r .url 2>/dev/null || true)"
            case "$IMAGE_URL" in
                https://*) log "Uploaded screenshot proof: $IMAGE_URL" ;;
                *) log "Screenshot upload failed; falling back to text-only proof."; IMAGE_URL="" ;;
            esac
            ;;
    esac
fi

COMMENT_FILE="$PROOF_DIR/comment.md"
{
    echo "## Automated test proof (agent loop)"
    echo
    echo "**Result: $STATUS**"
    echo
    if [ -n "$IMAGE_URL" ]; then
        echo "![test proof]($IMAGE_URL)"
        echo
    fi
    echo '```'
    tail -30 "$TRANSCRIPT"
    echo '```'
} > "$COMMENT_FILE"

gh pr comment "$PR_NUMBER" --body-file "$COMMENT_FILE"
log "Posted test proof comment on PR #$PR_NUMBER (status: $STATUS, screenshot: ${IMAGE_URL:-none})"

git worktree remove --force "$WORKTREE_DIR" 2>/dev/null || true
git worktree prune
[ "$STATUS" = "PASS" ]
