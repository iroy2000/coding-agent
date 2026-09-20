#!/usr/bin/env bash
# Stage 3: File the approved idea as a GitHub issue.
#
# Reads scripts/agent_loop's verdict.json (from 2_judge.sh) and, if
# approved, creates a real GitHub issue labeled "ai-generated" so it's
# clearly distinguishable from human-filed issues, then prints the new
# issue number for the next stage to consume.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source lib.sh
require_gh_auth
cd "$REPO_ROOT"

VERDICT_FILE="$LOOP_STATE_DIR/verdict.json"
[ -s "$VERDICT_FILE" ] || { log "No verdict file at $VERDICT_FILE; run 2_judge.sh first"; exit 1; }

APPROVED="$(python3 -c "import json,sys; print(json.load(open('$VERDICT_FILE')).get('approved', False))" 2>/dev/null || echo False)"

if [ "$APPROVED" != "True" ]; then
    log "Judge did not approve any idea this cycle. Nothing to file."
    exit 0
fi

TITLE="$(python3 -c "import json; print(json.load(open('$VERDICT_FILE'))['title'])")"
BODY="$(python3 -c "import json; print(json.load(open('$VERDICT_FILE'))['body_markdown'])")"

# Ensure the label exists (idempotent).
gh label create "ai-generated" --description "Filed automatically by the agent loop" --color "5319e7" 2>/dev/null || true

ISSUE_URL="$(gh issue create --title "$TITLE" --body "$BODY" --label "ai-generated" --label "enhancement")"
ISSUE_NUMBER="$(basename "$ISSUE_URL")"
echo "$ISSUE_NUMBER" > "$LOOP_STATE_DIR/last_issue_number.txt"
log "Created issue #$ISSUE_NUMBER: $ISSUE_URL"
echo "$ISSUE_NUMBER"
