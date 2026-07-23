# Second Self Agent Rules

## Startup

1. Always read
   `01-strategy-storage/00 Memory/Second Self Context.md`.
2. Read `01-strategy-storage/00 Memory/00 Memory Interview Guide.md`. When the
   immediate task permits, ask one focused question from an incomplete memory
   topic and save only a user-confirmed summary.
3. Read `90-system/docs/OPERATING-MODEL.md` and
   `90-system/docs/SECURITY.md`.
4. Resolve private paths through `.second-self.local.json`; never hard-code them.
5. If private data is assembled, retrieve only relevant notes from the approved
   core folders under `01-strategy-storage` and from
   `02-skills-projects/projects/Projects Index.md` when project context is
   needed.
6. Retrieve historical notes only when relevant.

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
.\90-system\automation\scripts\second-self.ps1 validate --privacy
python -m pytest
```
