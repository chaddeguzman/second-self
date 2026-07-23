# Second Self Agent Rules

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
   `02-skills-projects/README.md` as the folder-purpose guides. Use the main
   `README.md` for the independent nested-project Git workflow.

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
  when it helps the user. Layer 1 provides context; Layer 2 skills and commands
  perform project work; important outcomes and reusable lessons return through
  controlled writeback and review.

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
  and requires intent approval followed by approval of the exact change.
- Protected changes require proposal approval followed by approval of the exact
  diff. Changed inputs invalidate approval.
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
