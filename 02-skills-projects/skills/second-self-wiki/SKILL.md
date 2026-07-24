---
name: second-self-wiki
description: Process files, screenshots, bundles, quick captures, and changed curated notes into the private Second Self LLM Wiki. Use when the user asks to process Raw sources, maintain or lint the wiki, query connected knowledge, refresh changed notes, resolve wiki contradictions, or explicitly save an analysis.
---

# Second Self Wiki

Read `references/schema.md` before proposing wiki changes.

## Process sources

1. Run `python -m second_self wiki status` and resolve requested source units under `01 Notes/00 Raw`. Process at most ten.
2. Stop if an interrupted transaction exists. Run recovery only with user authorization.
3. Hash and read each source. Inspect PNG, JPG, or WebP sources visually. Never invent missing extraction or OCR.
4. Read `03-wiki/index.md`, then only relevant source, topic, entity, analysis, and primary Second Self pages.
5. Distinguish direct evidence, derived interpretation, conflicts, and missing information. Never use a generated page as the sole basis for a consequential personal claim.
6. Prepare complete page contents, index changes, one append-only log entry, open-question changes, and Raw-to-Processed moves. Use stable source IDs and final Processed paths.
7. Submit one `wiki_process` broker proposal. Do not write wiki pages or move sources directly.
8. Show intent, affected paths, the exact diff, and the move manifest together. Apply after one `Y` or `Yes`; reject after one `N` or `No`. Never request an approval phrase, proposal ID, timestamp, or second approval.
9. Run `python -m second_self wiki lint` and report the archived paths, pages changed, conflicts, and warnings.

Archive successfully reviewed duplicates with a duplicate log entry but no redundant synthesis. Keep failed, unsupported, incomplete, or unapproved units in Raw.

## Query

Read Memory first for personal recall, then the wiki index and relevant pages. Trace claims through source pages to Raw, Processed, or in-place evidence. Cite private relative paths and dates. Surface conflicting sources without choosing silently.

## Save an analysis

Only file a conversational result when the user explicitly asks. Create or update an `analyses/` page, related pages, index, and log through a reviewed `wiki_process` proposal. Do not move a source unless Raw material is part of the same request.

## Maintain

Run structural lint before semantic review. Check contradictions, stale synthesis, candidate entity duplicates, missing source coverage, and meaningful orphans. Put uncertain merges and renames in `open-questions.md`; never merge entities or rename archived sources automatically.
