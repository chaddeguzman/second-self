# Operating Model

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
sources. Raw items wait under `01 Notes/00 Raw`; a reviewed transaction creates
or updates interlinked Markdown and archives successful sources under
`01 Notes/99 Processed`. Existing curated evidence stays in place.

Generated pages always remain derived. They must trace material claims to
archived or in-place evidence, preserve disagreement, and never silently
promote an interpretation into confirmed personal memory.

Wiki processing is explicit. The broker binds the exact source hashes, page
diffs, and archive moves into a journaled transaction. Interrupted transactions
must be recovered before more sources are processed.

A single `wiki_process` transaction can include two kinds of source moves:

1. **Raw → flat Processed** (legacy) — the source is archived under
   `01 Notes/99 Processed` with a timestamp prefix and the wiki `source_path`
   points to that location.
2. **Raw → 04 References/{subfolder}** (new) — the source moves directly to
   the chosen References subfolder, preserving the original filename. The wiki
   `source_path` is set at proposal time to the References path, and the broker
   verifies the file exists there after applying.

For the References route, the agent asks the user in a single prompt which
subfolder each source should go to (`00 books`, `01 quotes`, `02 research`,
`03 guides`, `04 docs`, or `05 Uncategorized`). The entire operation — wiki
pages plus source moves — is submitted as one `wiki_process` proposal and
applied together.
