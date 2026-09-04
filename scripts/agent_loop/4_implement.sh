#!/usr/bin/env bash
# Stage 4: Spawn a coding agent to implement a single GitHub issue.
#
# Usage: 4_implement.sh <issue-number>
#
# Creates an isolated git worktree on a fresh branch, points a
# non-interactive Copilot session at it with the issue body as context,
# and requires the agent to: implement the fix, add/adjust tests, run the
# full test suite itself, commit, push the branch, and open a PR that
# closes the issue. Never touches main directly (branch + PR only).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source lib.sh
require_gh_auth
cd "$REPO_ROOT"

ISSUE_NUMBER="${1:?Usage: 4_implement.sh <issue-number>}"
BRANCH="agent/issue-$ISSUE_NUMBER"
WORKTREE_DIR="$LOOP_STATE_DIR/worktree-issue-$ISSUE_NUMBER"

ISSUE_JSON="$(gh issue view "$ISSUE_NUMBER" --json title,body)"
ISSUE_TITLE="$(echo "$ISSUE_JSON" | python3 -c "import json,sys;print(json.load(sys.stdin)['title'])")"
ISSUE_BODY="$(echo "$ISSUE_JSON" | python3 -c "import json,sys;print(json.load(sys.stdin)['body'])")"

log "Implementing issue #$ISSUE_NUMBER: $ISSUE_TITLE"

# Fresh worktree so this never disturbs the operator's own working tree or
# risks touching main.
rm -rf "$WORKTREE_DIR"
git fetch origin main --quiet
git worktree add -B "$BRANCH" "$WORKTREE_DIR" origin/main --quiet

PROMPT_FILE="$LOOP_STATE_DIR/4_implement_prompt_$ISSUE_NUMBER.txt"
RESULT_FILE="$LOOP_STATE_DIR/4_implement_result_$ISSUE_NUMBER.txt"

cat > "$PROMPT_FILE" <<EOF
You are implementing GitHub issue #$ISSUE_NUMBER on the "coding-agent-cli"
repository. You are already on a dedicated branch "$BRANCH" checked out in
this worktree — do not create or switch branches, and never commit
directly to main.

Issue title: $ISSUE_TITLE

Issue body:
$ISSUE_BODY

Requirements:
1. Implement a correct, minimal, surgical fix/feature for this issue.
2. Add or update automated tests (pytest) that fail before your change and
   pass after it.
3. Run the full test suite (pytest) yourself and confirm everything
   passes before proceeding. Do not skip this.
4. Run ruff/mypy if configured and fix anything you introduced.
5. Commit your changes with a clear message referencing "#$ISSUE_NUMBER".
6. Push the branch to origin ("git push -u origin $BRANCH").
7. Open a pull request via 'gh pr create' with a body that includes
   "Closes #$ISSUE_NUMBER" and a summary of what you changed and how you
   tested it.
8. Print the final PR URL as the last line of your response.
EOF

(
    cd "$WORKTREE_DIR"
    run_copilot "$PROMPT_FILE" "$RESULT_FILE"
)

log "Implementation session finished. Result:"
cat "$RESULT_FILE"

PR_URL="$(grep -Eo 'https://github.com/[^ ]+/pull/[0-9]+' "$RESULT_FILE" | tail -1 || true)"
if [ -n "$PR_URL" ]; then
    echo "$PR_URL" > "$LOOP_STATE_DIR/last_pr_url.txt"
    log "Opened PR: $PR_URL"
else
    log "WARNING: could not detect a PR URL in the agent's output; check $RESULT_FILE manually."
fi
