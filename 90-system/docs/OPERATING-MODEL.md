# Operating Model

## Runtime Model

Hermes is the first ECHO runtime. Its canonical behavior is defined by
`90-system/.echo/IDENTITY.md` and the ECHO skill; Hermes-ready files are
generated outputs. Codex CLI, Codex in VS Code, Codex Desktop, Claude Code,
Cline, and other local agents use the same `AGENTS.md`, skills, broker, and
validation commands. Runtime hooks can improve ergonomics, but no workflow may
require a hook that one of the supported clients does not implement.

## Purpose

Second Self supports reliable personal recall and action aligned with Chad's
current identity, values, principles, knowledge, strategy, history,
relationships, experiences, and commitments.
## Authority

Current-view notes are concise working summaries, not a mechanism for erasing
history. Historical sources retain equal evidentiary standing. A live correction
wins for the current session and creates a proposed reconciliation item.

When sources conflict, surface each claim with its source and date. Do not pick
one silently.
## Capture And Review

New thoughts and imports enter the inbox. Weekly review classifies captures,
reviews project priorities, resolves tags, and surfaces conflicts. Quarterly
review revisits identity, strategy, goals, commitments, and promoted lessons.

Each review produces an archived review note plus approved current-view updates,
project priorities, promoted lessons, and an unresolved-conflict list.
## Projects

Second Self owns project intent, status, decisions, next actions, and lessons.
Code and detailed execution artifacts remain in external repositories. Only
explicitly registered, trusted local project agents receive Second Self adapters.
## Retrieval

Session startup uses compact current-view and index notes. Use metadata indexes
and text search for deeper retrieval. Do not load the entire archive into a
prompt. Consequential responses cite the relevant private note and date.
## LLM Wiki

The wiki is a persistent derived navigation layer between questions and primary
sources. Raw items wait under `01 Capture/00 Raw`; a reviewed transaction
creates or updates interlinked Markdown and moves successful sources into
`04 References/{subfolder}`. Existing curated evidence stays in place.

Generated pages always remain derived. They must trace material claims to
archived or in-place evidence, preserve disagreement, and never silently
promote an interpretation into confirmed personal memory.

Wiki processing is explicit. The broker binds the exact source hashes, page
diffs, and source moves into a journaled transaction. Interrupted transactions
must be recovered before more sources are processed.

A `wiki_process` transaction moves sources from Raw to
`04 References/{subfolder}`, preserving the original filename. The wiki
`source_path` is set at proposal time to the References path, and the broker
verifies the file exists there after applying.

The agent asks the user in a single prompt which subfolder each source should
go to (`01 books`, `02 quotes`, `03 research`, `04 guides`, `05 docs`, or
`06 Uncategorized`). The entire operation — wiki pages plus source moves — is
submitted as one `wiki_process` proposal and applied together.
# Reproducible dependency profiles and backup recovery

Install the smallest profile needed: core dependencies use `pip install -e .`,
semantic work uses `pip install -e .[semantic]`, Calendar integration uses
`pip install -e .[calendar]`, and contributor tooling uses `pip install -e .[dev]`.
`requirements.lock` is the checked-in Windows CI lock; verify it before use with
`python 90-system/automation/scripts/verify-dependency-lock.py`.

Encrypted backup requires the archive, `.sha256`, and `.manifest.json` artifacts.
Restore verifies all three, decrypts and validates members in a disposable staging
directory, and refuses a non-empty destination. Test recovery only with the
synthetic fixture and never a personal vault as a drill target.
