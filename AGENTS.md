# Second Self Agent Rules

## Universal Entry Point

This file is the canonical startup guide for **any coding agent** (Claude Code,
Cline, Cursor, Deepseek, Windsurf, or any other LLM-powered agent). If you are
an agent reading this for the first time:

1. Read `01-strategy-storage/00 Memory/Second Self Context.md` for the system's
   purpose, architecture, privacy model, and shared human-agent context.
2. Read `01-strategy-storage/00 Memory/00 Memory Interview Guide.md`. When the
   immediate task permits, ask one focused question from an incomplete memory
   topic and save only a user-confirmed summary.
3. Read `90-system/docs/OPERATING-MODEL.md` and
   `90-system/docs/SECURITY.md`.
4. Resolve private paths through `.second-self.local.json`; never hard-code them.
5. Browse `02-skills-projects/skills/` to discover available skills. Each skill
   has a `SKILL.md` with instructions. Use the matching skill when a task
   matches its description.
6. Use `01-strategy-storage/README.md` and
   `02-skills-projects/README.md` as the folder-purpose guides. Use
   `Quick Start.md` for the independent nested-project Git workflow.
7. Before writing, moving, or deleting any file through an Obsidian-aware
   operation, confirm the active vault is Second Self. Treat this as an
   approved-vault safelist of one; never touch another vault from a Second
   Self session, even if asked.

## Startup

1. Always read
   `01-strategy-storage/00 Memory/Second Self Context.md`.
   Treat `00 Memory` as the primary durable context and the first retrieval
   location for personal recall.
2. Read `01-strategy-storage/00 Memory/00 Memory Interview Guide.md`. When the
   immediate task permits, ask one focused question from an incomplete memory
   topic and save only a user-confirmed summary.
3. Read `90-system/docs/OPERATING-MODEL.md` and
   `90-system/docs/SECURITY.md`.
4. Resolve private paths through `.second-self.local.json`; never hard-code them.
5. When a task depends on personal context, begin with relevant notes under
   `01-strategy-storage/00 Memory`, but do not treat Memory as the only context
   source. When broader context is useful, also retrieve relevant material from
   `01 Notes`, `02 Journal`, `03 Strategy`, `04 References`, and `05 Reviews`,
   plus
   `02-skills-projects/projects/Projects Index.md` when project context is
   relevant.
6. Retrieve historical notes only when relevant.
7. Use `01-strategy-storage/README.md` and
   `02-skills-projects/README.md` as the folder-purpose guides. Use
   `Quick Start.md` for the independent nested-project Git workflow.
8. Before writing, moving, or deleting any file through an Obsidian-aware
   skill, confirm the active vault is Second Self. Treat this as an
   approved-vault safelist of one; never touch another vault from a Second
   Self session, even if asked.

## Core Function: Second Brain

- Second Self is an external memory system. Its central purpose is to help the
  user recall facts, experiences, decisions, commitments, investigations,
  project context, thoughts, and ideas that human memory may not reliably
  retain.
- Do not answer personal recall questions from model memory or assumptions.
  Use the `second-self-recall` workflow and stored Markdown evidence.
- Start recall in `01-strategy-storage/00 Memory`, then assemble additional
  relevant context from `01 Notes`, `02 Journal`, `03 Strategy`,
  `04 References`, `05 Reviews`, historical sources, and project records.
- Use the available context window intentionally. A task may benefit from
  multiple complementary sources across all six Layer 1 folders rather than a
  single memory note.
- Protect privacy by retrieving task-relevant material, but do not make the
  search artificially narrow or stop after one file when useful context could
  reasonably exist elsewhere in the approved sources.
- Distinguish confirmed stored evidence, reasonable inference, and missing
  information. Cite the relevant internal file and date.
- Apply recalled context to project work, investigations, and idea development
  when it helps the user. Layer 1 provides context; Layer 2 skills and
  commands perform project work by wrapping the deterministic tooling in
  `90-system/automation`, so routine bookkeeping (indexing, manifest updates,
  coverage checks) doesn't depend on ad hoc reasoning each time; important
  outcomes and reusable lessons return through controlled writeback and
  review.

## LLM Wiki

- `01-strategy-storage/01 Notes/00 Raw` is the pending source queue.
- `01-strategy-storage/01 Notes/99 Processed` is the immutable processed-source
  archive. Corrections enter Raw as new revisions; never edit archived sources.
- `03-wiki` is private, derived, and agent-maintained. Use the
  `second-self-wiki` skill for processing, querying, saving analyses, or
  linting. `second-self-wiki` covers four distinct operations — ingest,
  query, maintain, lint — invoke the one matching the task rather than
  re-deriving the workflow from prose each time.
- Wiki pages guide navigation but do not replace primary evidence. Consequential
  personal claims must trace to Raw, Processed, or existing Second Self sources.
- Semantic wiki changes and Raw-to-Processed moves require one reviewed
  `wiki_process` broker transaction, whether the run is user-triggered or
  scheduled/automated. Existing curated notes remain in place.
- Every wiki, Notes, Journal, and Reviews page carries the shared front-matter
  fields defined in `90-system/docs/FRONT-MATTER-SCHEMA.md` (at minimum:
  created date, updated date, tags, source reference, processed flag), using
  the matching template in `90-system/docs/TEMPLATES.md` for its note type
  (source, concept, topic, entity, project, review, log). Do not freehand a
  front-matter shape for a note type that already has a template — propose a
  template change instead.
- Use standard Obsidian `[[wikilink]]` syntax for cross-references so the
  graph view and any Obsidian-CLI-aware skill stay accurate.

## Privacy-Sensitive Processing

- `00 Memory`, `03 Strategy`, and `02 Journal` hold the most sensitive
  personal content: identity, values, and reflections. If a local model
  integration is configured (see `90-system/docs/SECURITY.md`), prefer it for
  drafting from this content, using a review-before-apply pattern — the local
  model proposes a draft, a human approves it, and only then is it applied and
  enters Layer 1 evidence.
- If no local model is configured, proceed with the standard cloud agent, but
  never include raw Memory, Strategy, or Journal content in anything that
  leaves the session (exports, logs, hook output, PR or issue text) beyond
  what the task strictly requires.

## Golden Rule: Main Must Stay Aligned

- Use only the active repository's `main` branch for Second Self changes. Do
  not work from a stale parent checkout or a feature branch.
- Before changing tracked files, fetch `origin` and verify:
  - the current branch is `main`;
  - the working tree contains no unexplained changes; and
  - `git rev-list --left-right --count main...origin/main` returns `0 0`.
- If local `main` and `origin/main` differ, stop normal work and align them
  safely before making additional changes. Preserve a recovery branch before
  rewriting any existing local history.
- Completed tracked changes must not be left uncommitted. Validate privacy and
  tests, commit on local `main`, and let the post-commit hook publish to the
  workflow-only `automation/main` branch.
- After required checks pass, merge the automated pull request with **Create a
  merge commit**, pull in VS Code, and verify that the working tree is clean and
  `main...origin/main` is again `0 0` before starting another change.
- Do not use **Rebase and merge**, **Squash and merge**, direct pushes to
  protected `main`, or VS Code **Sync Changes** in this workflow.

## Evidence

- Treat stored sources as equally valid evidence.
- When sources disagree, cite both files and dates and ask which applies before
  consequential use.
- Cite internal sources for decisions, commitments, preferences, and recalled
  personal facts.
- If evidence is missing, state what was searched and ask. Do not invent
  personal context.
- A live user correction wins in the current session and should be captured as
  a reconciliation proposal.

## Editing

- Use `python -m second_self broker` for protected changes.
- Protected changes include identity or strategy edits, private-context
  exports, deletes, moves, renames, and changes to five or more existing files.
- The only approved top-level folders under `01-strategy-storage` are
  `00 Memory`, `01 Notes`, `02 Journal`, `03 Strategy`, `04 References`, and
  `05 Reviews`.
- Creating any other top-level folder under `01-strategy-storage` is protected
  and requires one approval of the proposal's exact change.
- Protected changes require one Yes/No decision after reviewing the exact diff
  or payload. Accept `Y` or `Yes` to apply and `N` or `No` to reject. Never
  require an approval phrase, proposal ID, timestamp, or second approval.
  Changed inputs invalidate approval and require a new proposal.
- Deletion means moving to private trash. Permanent purge is separately
  protected.
- Project agents may update their own project record directly. Put broader
  lessons and proposed Layer 1 changes in the inbox.
- Never expose private paths or personal content in Git, logs, hook output, or
  public issue/PR text.

## Verification

Run:

```powershell
.\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only
python -m pytest
```

Before committing anything that touches `03-wiki`, `01 Notes`, or templates,
also run the `second-self-wiki` lint operation. Privacy validation checks for
data leakage; wiki lint checks front-matter compliance, broken links, and
orphaned pages — both are required, and neither substitutes for the other.