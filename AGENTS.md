# Main Brain Agent Rules

## Startup

1. Always read
   `01-strategy-storage/00 Memory/Main Brain Context.md`.
2. Read `01-strategy-storage/00 Memory/00 Memory Interview Guide.md`. When the
   immediate task permits, ask one focused question from an incomplete memory
   topic and save only a user-confirmed summary.
3. Read `90-system/docs/OPERATING-MODEL.md` and
   `90-system/docs/SECURITY.md`.
4. Resolve private paths through `.main-brain.local.json`; never hard-code them.
5. If private data is assembled, read the compact current-view indexes:
   - `01-strategy-storage/10-current/Current Identity.md`
   - `01-strategy-storage/10-current/Current Strategy.md`
   - `02-skills-projects/projects/Projects Index.md`
   - `01-strategy-storage/55-conflicts/Conflicts Index.md`
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

- Use `python -m main_brain broker` for protected changes.
- Protected changes include identity or strategy edits, private-context
  exports, deletes, moves, renames, and changes to five or more existing files.
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
.\90-system\automation\scripts\brain.ps1 validate --privacy
python -m pytest
```
