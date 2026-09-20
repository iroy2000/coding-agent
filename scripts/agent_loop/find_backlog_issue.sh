#!/usr/bin/env bash
# Helper: find the oldest open "ai-generated" issue that doesn't already
# have a linked/open PR, so the loop can work through a backlog of
# already-approved ideas instead of always brainstorming something new.
#
# Usage: find_backlog_issue.sh
# Prints an issue number on stdout, or nothing (exit 0) if the backlog is
# empty.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source lib.sh
require_gh_auth
cd "$REPO_ROOT"

# Issues already referenced by an open PR body ("Closes #N" / "closes #N")
# are considered in-flight and skipped.
OPEN_PR_BODIES="$(gh pr list --state open --json body --jq '.[].body' 2>/dev/null || true)"

gh issue list --state open --label ai-generated --json number,createdAt \
    --jq 'sort_by(.createdAt) | .[].number' | while read -r issue_num; do
    if echo "$OPEN_PR_BODIES" | grep -qiE "#$issue_num([^0-9]|$)"; then
        continue
    fi
    echo "$issue_num"
    exit 0
done
