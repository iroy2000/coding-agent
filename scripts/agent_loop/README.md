# Agentic self-improvement loop

This is a working implementation of a recursive loop where the [GitHub
Copilot CLI](https://docs.github.com/copilot/how-tos/copilot-cli) is used
non-interactively (`copilot -p "..." --allow-all-tools`) as the "brain" for
every stage of improving this very project:

```
 ┌────────────┐   ┌───────────┐   ┌──────────────┐   ┌──────────────┐   ┌────────────────┐
 │ 1 Brainstorm│ → │ 2 Judge / │ → │ 3 Create      │ → │ 4 Implement  │ → │ 5 Test + prove │
 │  ideas      │   │  research │   │  GitHub issue │   │  (agent → PR)│   │  (proof comment)│
 └────────────┘   └───────────┘   └──────────────┘   └──────────────┘   └────────────────┘
                                                              ▲                    │
                                                              │                    ▼
                                                   ┌──────────┴───────┐   human reviews & merges
                                                   │ 6 Respond to PR   │   (never auto-merged)
                                                   │   review comments │
                                                   └───────────────────┘
```

## Why this is safe to run unattended

- **Every stage is a separate, bounded `copilot -p` invocation** with
  `--max-ai-credits` set (default 40, see `lib.sh`) and a per-invocation
  usage/cost JSON sidecar file, so a single stage can never run away with
  unbounded spend and cost is auditable after the fact.
- **A broad tool denylist applies to every nested agent invocation**
  (`COPILOT_DENY_TOOLS` in `lib.sh`): no pushing/force-pushing to `main`,
  no tagging releases, no merging/closing PRs itself, no editing repo
  settings or GitHub Actions workflows/secrets, no `sudo`. This is
  defense-in-depth on top of `--no-ask-user`, not a sandbox — see issue #4
  in this repo for why a denylist alone is never a complete safety net.
- **Implementation and review-response happen in an isolated `git
  worktree` on a dedicated branch** (`agent/issue-<n>`), never on the
  operator's own checkout and never on `main`. `git push origin main` and
  any `--force` push are explicitly denied tools.
- **Nothing is ever merged automatically.** Stage 4 opens a PR; stage 5
  posts an independent test-proof comment; a human always does the actual
  review + merge.
- **Issues filed by the loop are labeled `ai-generated`** so they're never
  confused with human-filed issues, and the judge stage (stage 2) is a
  *separate* Copilot session with no memory of proposing the ideas — its
  job is to find reasons to reject them, including checking they aren't
  duplicates of already-open issues.

## Usage

```bash
# Run one full cycle: brainstorm -> judge -> issue -> implement -> PR -> test/prove
scripts/agent_loop/run_cycle.sh

# Skip brainstorming and implement a specific existing issue
scripts/agent_loop/run_cycle.sh --issue 6

# Just respond to review comments on an already-open agent PR
scripts/agent_loop/run_cycle.sh --review 12
```

To "keep the loop going" per the original ask, schedule `run_cycle.sh` on a
cron/launchd job (e.g. nightly). Each run is idempotent and safe to
overlap-guard with a simple lockfile if you run it more often than a full
cycle typically takes.

## Individual stages

Each numbered script in this directory can also be run standalone (useful
for debugging or resuming a partial cycle):

| Script | Purpose |
|---|---|
| `1_brainstorm.sh` | Propose 3 new, scoped enhancement ideas as JSON |
| `2_judge.sh` | Adversarially review ideas against the real codebase + open issues; approve at most one |
| `3_create_issue.sh` | File the approved idea as a GitHub issue (`ai-generated` label) |
| `4_implement.sh <issue#>` | Implement the issue, write/run tests, commit, push, open a PR |
| `5_test_and_prove.sh <pr#>` | Independently re-test the PR branch and post a proof comment, including a real embedded screenshot uploaded via GitHub's attachment API |
| `6_respond_to_review.sh <pr#>` | Address open review/PR comments and push fixes |
| `find_backlog_issue.sh` | Find the oldest `ai-generated` issue with no linked open PR yet ("backlog-first": `run_cycle.sh` implements this before brainstorming something new) |
| `cleanup.sh` | Prune local worktrees/branches for issues whose PR has since been merged/closed |

State (prompts, raw model output, per-invocation usage/cost JSON,
worktrees) is written to `.agent_loop_state/` at the repo root, which is
gitignored. `run_cycle.sh` holds an `mkdir`-based lock for the duration of
a cycle (see `with_lock` in `lib.sh`) so scheduling it frequently via cron/
launchd never overlaps with a still-running previous cycle.

## Requirements

- `gh` CLI, authenticated with permission to create issues/PRs on this repo.
- `copilot` CLI, authenticated (this is literally the GitHub Copilot CLI
  you're reading this from).
- [`freeze`](https://github.com/charmbracelet/freeze) (optional, for the
  PNG proof artifact): `brew install charmbracelet/tap/freeze`.

## Known limitations

- GitHub's hosted "Copilot coding agent" (assigning an issue to `@copilot`
  to get an automatic PR) is **not** currently enabled/licensed on this
  repo — `gh api repos/{owner}/{repo}/assignees` only lists human users.
  This loop works around that by driving the local `copilot` CLI directly
  instead, which is why it needs to run somewhere with `copilot` installed
  and authenticated (a developer machine, or a self-hosted CI runner) —
  it will not run on GitHub-hosted Actions runners as-is.
- The "screenshot" proof is a real PNG rendered from the test transcript
  via `freeze` (works headlessly, no visible display needed), not a
  literal screen capture of a terminal window — this is intentional so
  the loop works unattended/in CI-like environments.
