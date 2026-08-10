# Second Self Skills

This directory contains all registered Second Self skills. Each skill lives in
its own subfolder with a `SKILL.md` that provides the agent-facing workflow
instructions. Skills are invoked when a user's task matches the skill
description.

## Skill Catalog

| Skill                                                                   | Version | Purpose                                                                 |
| ----------------------------------------------------------------------- | ------- | ----------------------------------------------------------------------- |
| [second-self-backup](second-self-backup/SKILL.md)                       | 1.0.0   | Create encrypted or sync backups on removable storage.                  |
| [second-self-capture](second-self-capture/SKILL.md)                     | 1.0.0   | Capture thoughts, notes, quotes, links, and corrections into the inbox. |
| [second-self-commit](second-self-commit/SKILL.md)                       | 1.0.0   | Commit and merge changes through the protected main workflow.           |
| [second-self-conflict-review](second-self-conflict-review/SKILL.md)     | 1.0.0   | Review contradictory claims and prepare a user decision.                |
| [second-self-intake](second-self-intake/SKILL.md)                       | 1.0.0   | Import and extract PDF, DOCX, XLSX, or TXT material with provenance.    |
| [second-self-project-handoff](second-self-project-handoff/SKILL.md)     | 1.1.0   | Prepare an auditable private project context brief.                     |
| [second-self-project-writeback](second-self-project-writeback/SKILL.md) | 1.0.0   | Return project status, decisions, and lessons to Second Self.           |
| [second-self-quarterly-review](second-self-quarterly-review/SKILL.md)   | 1.1.0   | Run the guided quarterly review.                                        |
| [second-self-recall](second-self-recall/SKILL.md)                       | 1.0.0   | Retrieve personal facts, preferences, decisions, and history.           |
| [second-self-restore](second-self-restore/SKILL.md)                     | 1.0.0   | Verify and restore an encrypted snapshot into a new directory.          |
| [second-self-weekly-review](second-self-weekly-review/SKILL.md)         | 1.0.0   | Run the guided weekly review.                                           |
| [second-self-wiki](second-self-wiki/SKILL.md)                           | —       | Process sources, maintain, query, and lint the private LLM Wiki.        |

## Detailed Descriptions

### second-self-backup

**When to use:** The user connects a backup drive or requests a verified
private-data snapshot.

Creates a manual dated encrypted Second Self backup on removable storage. The
skill supports two modes:

- **Encrypted backup (disaster recovery):** Runs `backup.ps1` with an
  `age`-encrypted archive, manifest, and SHA-256 checksum. The passphrase is
  entered interactively and never recorded. Older snapshots are never pruned
  automatically.
- **Obsidian-readable sync backup (portable copy):** Runs `backup.ps1
  -SyncTo` to create a plain folder mirror that can be opened in Obsidian,
  copied to another machine, or pushed to GitHub. Caches are excluded; the
  five newest sync backups are retained.

### second-self-capture

**When to use:** The user asks to remember, record, save, capture, or
reconcile new personal context.

Captures a thought, note, quote, link, or live user correction into the
Second Self inbox. The user's original wording is preserved and distinguished
from agent interpretation. Captures are left as `inbox` classification;
weekly review determines durable placement. The skill returns the created
private path without exposing contents publicly.

### second-self-commit

**When to use:** The user asks to commit, push, merge, or sync changes to the
Second Self repository.

Guides any trusted local AI agent through the full protected `main` workflow:
pre-checks (fetch, verify `0 0`), stage, validate (privacy + tests), commit on
`main` (pre-commit hook runs privacy validation, post-commit hook auto-publishes
to `automation/main`), wait for CI, merge the pull request via `gh` with a merge
commit, pull, and verify `main...origin/main` is `0 0` with a clean working
tree. The merge subject uses the prefix `Merge Pull Request #<PR-number>`.
Private paths (`00 Memory`, `04 References`, `03-wiki`, projects, local config)
are never staged. Failure recovery covers hook failures, push retries, CI
failures, missing PRs, and merge conflicts.

### second-self-conflict-review

**When to use:** Notes disagree or a live correction conflicts with stored
context.

Reviews contradictory Second Self claims and prepares a user decision without
silently choosing a winner. Each claim is listed with its date, source path,
and applicable context. The user decides which claim is current, conditional,
or superseded. Identity or strategy changes are routed through the edit
broker. Prior sources are preserved after resolution.

### second-self-intake

**When to use:** Files are dropped for journals, notes, references, quotes,
books, or lessons.

Imports and extracts PDF, DOCX, XLSX, or TXT material into Second Self with
immutable provenance. The skill runs `python -m second_self ingest`, reports
duplicate status and SHA-256 hashes, and proposes categorized derived notes
with source links. Derived notes remain proposals until review. Image-only,
encrypted, or unreadable files are flagged; OCR output is never invented.

### second-self-project-handoff

**When to use:** Before focused work in a registered project or when the user
asks what personal context should guide that project.

Prepares an auditable private project context brief from Second Self. The
skill reads the private project record and searches only relevant Layer 1
context, then drafts outcomes, constraints, decisions, priorities, and cited
sources. If the brief will leave private storage, the exact export payload
and destination are shown for one `Y`/`N` decision. The dated authoritative
brief is stored in the private project record area.

### second-self-project-writeback

**When to use:** After project work changes priorities, produces a
consequential decision, or reveals a reusable personal lesson.

Returns project status, decisions, and lessons to Second Self. The registered
project's status, decisions, and next actions are updated directly with
citations to the supporting repository revision or artifact. Broader lessons
and Layer 1 proposals go into the inbox. Identity and strategy are never
rewritten directly. Project indexes are regenerated after updates.

### second-self-quarterly-review

**When to use:** The user wants to reassess purpose, values, identity,
strategy, goals, commitments, project portfolio, and accumulated lessons.

Runs the guided Second Self quarterly review. The skill summarizes the prior
quarter from reviews, decisions, projects, and lessons; compares current
commitments with purpose, values, and strategy; surfaces contradictions and
missing evidence; and drafts current-view changes without erasing historical
sources. Every identity or strategy diff is routed through one broker
approval after showing the exact change. The review is archived and indexes
are regenerated.

### second-self-recall

**When to use:** An answer should rely on stored personal context or the user
asks what was previously recorded.

Retrieves personal facts, preferences, decisions, commitments, lessons, or
history from Second Self. The skill reads compact current-view indexes first,
then searches titles, metadata, and content for the specific topic. The
`recall` CLI subcommand provides ranked results scored by folder priority,
recency, tag strength, and title match. Every matching source is treated as
evidence; conflicts are not discarded. Paths and dates are cited for
consequential claims. If evidence is missing or contradictory, the skill
states what was searched and asks. Unrelated journals or history are not
loaded.

### second-self-restore

**When to use:** A new workstation, recovery test, or explicit disaster
recovery request.

Verifies and restores an encrypted Second Self snapshot into a new empty
directory. The skill runs `restore.ps1` with the archive, checksum file, and
empty destination. The `age` passphrase is entered interactively. The skill
stops on checksum failure, wrong passphrase, or a non-empty destination.
Restored metadata is validated before changing active configuration. An
active private-data directory is never merged or overwritten automatically.

### second-self-weekly-review

**When to use:** The user wants to process inbox captures, imported
documents, project priorities, returned lessons, tags, and unresolved
conflicts.

Runs the guided Second Self weekly review. The skill inventories the inbox
and proposed records without moving anything, proposes classifications,
derived notes, tag changes, and source links, reviews every active project's
priorities and next actions, surfaces conflicts and lessons that may change
current views, previews all changes, and routes protected changes through the
broker. An archived dated weekly review is created and indexes are
regenerated.

### second-self-wiki

**When to use:** The user asks to process Raw sources, maintain or lint the
wiki, query connected knowledge, refresh changed notes, resolve wiki
contradictions, or explicitly save an analysis.

Processes files, screenshots, bundles, quick captures, and changed curated
notes into the private Second Self LLM Wiki. The skill covers four operations:

- **Ingest:** Hashes and reads each source, creates linked source and topic
  pages, appends a log entry, and rebuilds the index. Sources are categorized
  into `04 References` subfolders through a reviewed `wiki_process` broker
  proposal.
- **Query:** Searches wiki pages for keywords and returns matching pages with
  snippets. Memory is read first for personal recall.
- **Maintain:** Rebuilds the index, appends a maintenance log entry, and lints
  the wiki for front-matter compliance, broken links, and orphaned pages.
- **Save analysis:** Creates or updates an `analyses/` page through a reviewed
  broker proposal.

The wiki index uses a unified table (`| Type | Page | Description | Sources |`)
and the log uses a table (`| Date | Operation | Title | Details |`) with
bottom-to-top ordering (latest entry first).

## Usage

Each skill is activated by matching the user's request to the skill
description. Read the skill's `SKILL.md` for the full workflow instructions
before executing. Skills that modify protected content (identity, strategy,
deletes, moves) route changes through the `second_self broker` with one
`Y`/`N` approval.