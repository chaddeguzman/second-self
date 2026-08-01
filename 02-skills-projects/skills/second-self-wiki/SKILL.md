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
6. Prepare complete page contents, index changes, one log entry, and open-question changes. The index uses a unified table (`| Type | Page | Description | Sources |`). The log uses a table (`| Date | Operation | Title | Details |`) with new rows prepended bottom-to-top (latest entry first). Join multiple detail bullets with `<br>` tags in the Details cell.
7. **Ask the user where each source should live.** Present the list of files and ask which `04 References` subfolder each belongs to. Accept the user's answer for all files in a single response. Valid subfolders: `01 books`, `02 quotes`, `03 research`, `04 guides`, `05 docs`, `06 Uncategorized`. Use `06 Uncategorized` when no other subfolder fits.
8. **Build the destination paths.** For each source, use `references_destination(paths, source_path, subfolder_name)` from `wiki.py` to get the collision-safe target. This preserves the original filename (no timestamp prefix). Set `source_path` in the wiki source page front-matter to this exact References-relative path.
9. **Prepare the move manifest.** Each move entry must use:
   - `from`: the relative path of the source inside `01 Notes/00 Raw`
   - `to`: the relative path under `04 References/{subfolder}/` returned by `references_destination()`
   - `source_id`: the SHA-256 hash of the source
10. Submit one `wiki_process` broker proposal containing wiki page changes plus the move manifest. Do not write wiki pages or move sources directly.
11. Show intent, affected paths, the exact diff, and the move manifest together. Apply after one `Y` or `Yes`; reject after one `N` or `No`. Never request an approval phrase, proposal ID, timestamp, or second approval.
12. Run `python -m second_self wiki lint` and report the moved paths, pages changed, conflicts, and warnings.

Archive successfully reviewed duplicates with a duplicate log entry but no redundant synthesis. Keep failed, unsupported, incomplete, or unapproved units in Raw.

## Query

Read Memory first for personal recall, then the wiki index and relevant pages. Trace claims through source pages to Raw, References, or in-place evidence. Cite private relative paths and dates. Surface conflicting sources without choosing silently.

## Save an analysis

Only file a conversational result when the user explicitly asks. Create or update an `analyses/` page, related pages, index, and log through a reviewed `wiki_process` proposal. Do not move a source unless Raw material is part of the same request.

## Maintain

Run structural lint before semantic review. Check contradictions, stale synthesis, candidate entity duplicates, missing source coverage, and meaningful orphans. Put uncertain merges and renames in `open-questions.md`; never merge entities or rename archived sources automatically.

