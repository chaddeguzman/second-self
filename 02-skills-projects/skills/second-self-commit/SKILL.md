---
name: second-self-commit
description: Commit and merge Second Self changes to GitHub through the protected main workflow. Use when the user asks to commit, push, merge, or sync changes to the Second Self repository.
---

# Second Self Commit

Version: `1.0.0`

This skill guides any trusted local AI agent (Codex, Claude Code, Cline, Cursor,
Deepseek, Windsurf, or any other LLM-powered agent) through the full protected
`main` workflow: pre-checks, validate, stage, commit, auto-publish, CI wait,
PR merge via `gh`, pull, and final `0 0` verification.

It works from both VS Code and a terminal. All commands are plain Git, `gh`, or
Second Self validation calls — no agent-specific tool format is required.

## Prerequisites

- The active repository is the Second Self vault root.
- `git` is configured with `core.hooksPath` pointing to
  `90-system/automation/git-hooks` (set by `bootstrap.ps1`).
- `gh` (GitHub CLI) is installed and authenticated.
- The current branch is `main`.

## Never stage these paths

The privacy validation hook and `.gitignore` block most of these, but the agent
must also enforce this rule when staging:

- `01-strategy-storage/00 Memory/` — private identity and durable context
- `01-strategy-storage/04 References/` — private reference material
- `01-strategy-storage/01 Notes/` — private notes (except scaffold `.gitkeep`)
- `01-strategy-storage/02 Journal/` — private journals
- `01-strategy-storage/03 Strategy/` — private strategy
- `01-strategy-storage/05 Reviews/` — private reviews
- `03-wiki/` — private derived wiki (except scaffold `.gitkeep` and `README.md`)
- `02-skills-projects/projects/` — private project records
- `.second-self.local.json` — local private configuration
- `.second-self-schema`, `.second-self-cache/` — runtime state
- Any file containing passwords, API keys, tokens, or absolute user paths

If the user asks to commit one of these, refuse and explain why.

## Workflow

### 1. Pre-checks (align before changing)

1. Confirm the current branch is `main`:
   ```sh
   git symbolic-ref --short HEAD
   ```
   If not on `main`, stop and ask the user before switching.

2. Fetch the latest remote state:
   ```sh
   git fetch origin
   ```

3. Verify local `main` and `origin/main` are aligned:
   ```sh
   git rev-list --left-right --count main...origin/main
   ```
   The output must be `0 0` (zero commits ahead, zero behind).

4. If the count is not `0 0`:
   - If local is behind (`0 N`): run `git pull origin main` (fast-forward only).
   - If local is ahead (`N 0`): the post-commit hook should have published;
     wait for the PR to merge, then pull.
   - If diverged (`N M`): preserve a recovery branch with
     `git branch backup/main-before-realign-$(date +%Y%m%d)`, then align
     safely. Stop normal work until `0 0` is restored.

5. Review the working tree and report to the user:
   ```sh
   git status
   ```
   List uncommitted modifications and untracked files so the user can confirm
   what will be staged.

### 2. Stage changes

1. Stage tracked modifications and new files per the user's request:
   ```sh
   git add <path1> <path2> ...
   ```
   Or stage all tracked changes (excluding ignored files):
   ```sh
   git add -u
   ```
   To include new untracked files as well:
   ```sh
   git add -A
   ```

2. **Never stage** the private paths listed above. Double-check `git status`
   after staging to confirm no private file was accidentally included.

3. If there are no staged changes, inform the user and exit gracefully:
   ```sh
   git diff --cached --quiet && echo "No staged changes."
   ```

### 3. Validate

Run all three checks before committing. Stop on any error.

1. Privacy validation (tracked files only):
   ```powershell
   .\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only
   ```
   Or from any shell:
   ```sh
   python -m second_self validate --privacy --tracked-only
   ```

2. Tests:
   ```sh
   python -m pytest
   ```

3. If the changes touch `03-wiki`, `01 Notes`, or templates, also run:
   ```sh
   python -m second_self wiki lint
   ```

4. If any validation or test fails, fix the issue and re-run before proceeding.

### 4. Commit

1. Draft a descriptive commit message from the staged diff:
   ```sh
   git diff --cached --stat
   ```
   The message should summarize what changed and why. Keep the subject line
   under 72 characters.

2. Commit on `main`:
   ```sh
   git commit -m "<subject>" -m "<optional body>"
   ```

3. The **pre-commit hook** runs `python -m second_self validate --privacy
   --tracked-only` automatically. If it fails, the commit is aborted. Fix the
   privacy issue, re-stage, and re-commit.

4. The **post-commit hook** auto-publishes the new commit to
   `origin/automation/main` using `--force-with-lease`. If successful, GitHub
   Actions will open or update a pull request.

5. If `SECOND_SELF_AUTO_PUBLISH=0` is set (hook disabled), manually publish:
   ```sh
   git push --force-with-lease=refs/heads/automation/main origin HEAD:refs/heads/automation/main
   ```

### 5. Wait for CI

1. Wait a few seconds for GitHub Actions to trigger, then find the latest run:
   ```sh
   gh run list --branch automation/main --limit 1
   ```

2. Watch the run until it completes:
   ```sh
   gh run watch <run-id>
   ```
   Or poll periodically:
   ```sh
   gh run view <run-id>
   ```

3. If CI fails:
   - Show failure details:
     ```sh
     gh run view <run-id> --log-failed
     ```
   - Fix the issue, re-stage, and re-commit. The new commit re-publishes
     automatically.

### 6. Merge PR

1. Find the open PR for `automation/main` → `main`:
   ```sh
   gh pr list --head automation/main --base main --state open
   ```

2. If no PR exists, create one:
   ```sh
   gh pr create --head automation/main --base main \
     --title "<commit subject>" \
     --body "Automated update from local main commit."
   ```

3. Verify all CI checks pass on the PR:
   ```sh
   gh pr checks <PR-number>
   ```

4. Merge with a **merge commit** (never squash or rebase):
   ```sh
   gh pr merge <PR-number> --merge --subject "Merge Pull Request #<PR-number>"
   ```
   The merge subject must use the prefix `Merge Pull Request #<PR-number>`.

### 7. Pull and verify

1. Pull the merged `main` from origin (fast-forward only):
   ```sh
   git pull origin main
   ```

2. Verify local and remote are aligned:
   ```sh
   git rev-list --left-right --count main...origin/main
   ```
   Output must be `0 0`.

3. Verify the working tree is clean:
   ```sh
   git status --porcelain
   ```
   Output must be empty.

4. Report success to the user:
   - PR number that was merged
   - Merge commit hash
   - Confirmation that `main...origin/main` is `0 0`
   - Confirmation that the working tree is clean

## Failure recovery

| Failure | Recovery |
|---------|----------|
| Pre-commit hook fails (privacy) | Fix the flagged file, re-stage, re-commit. |
| Post-commit push fails | Retry: `git push --force-with-lease=refs/heads/automation/main origin HEAD:refs/heads/automation/main` |
| CI checks fail | `gh run view <run-id> --log-failed`, fix, commit again. |
| No PR after push | `gh pr create --head automation/main --base main --title "<subject>" --body "Automated update."` |
| PR merge conflict (origin/main moved) | `git pull origin main`, resolve conflicts, re-commit. The new commit re-publishes. |
| `gh` not installed or not authenticated | Fall back to the GitHub UI: merge with **Create a merge commit**, then `git pull origin main` in the terminal. |
| Diverged local `main` | Preserve a recovery branch, align to `origin/main`, then proceed. |

## Quick reference

```sh
# 1. Pre-check
git symbolic-ref --short HEAD
git fetch origin
git rev-list --left-right --count main...origin/main   # must be 0 0
git status

# 2. Stage
git add <paths>

# 3. Validate
python -m second_self validate --privacy --tracked-only
python -m pytest

# 4. Commit (hooks auto-publish to automation/main)
git commit -m "<subject>"

# 5. Wait for CI
gh run list --branch automation/main --limit 1
gh run watch <run-id>

# 6. Merge PR
gh pr list --head automation/main --base main --state open
gh pr checks <PR-number>
gh pr merge <PR-number> --merge --subject "Merge Pull Request #<PR-number>"

# 7. Pull and verify
git pull origin main
git rev-list --left-right --count main...origin/main   # must be 0 0
git status --porcelain                                  # must be empty