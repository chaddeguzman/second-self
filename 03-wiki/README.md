# LLM Wiki

`03-wiki` is the private, derived knowledge layer of Second Self. It turns
reviewed source material and curated Second Self notes into linked topics,
entities, source pages, and analyses that make relevant context easier to
retrieve.

The wiki is a navigation and synthesis layer, not a replacement for primary
evidence. Material claims must trace back to a source in `01 Notes/00 Raw`, the
immutable `01 Notes/99 Processed` archive, or an existing Second Self note.

## Folder Guide

### `sources`

Contains source pages that describe imported or curated evidence and preserve
its provenance. A source page should identify the originating relative path,
date, and any relevant extraction or processing details.

Use source pages as the evidence bridge between wiki synthesis and the
underlying material. Do not rewrite archived source files to correct them;
record a new revision in Raw and process it through review.

### `topics`

Contains pages organized around subjects, themes, questions, and areas of
knowledge. Topic pages synthesize connected evidence and link to the source,
entity, and analysis pages that support them.

Keep interpretation distinct from confirmed facts, and preserve meaningful
disagreement instead of silently choosing one account.

### `entities`

Contains pages for recurring people, organizations, projects, places, concepts,
or other identifiable entities. Entity pages provide a stable place to connect
references across multiple sources.

Do not merge ambiguous or potentially duplicate entities automatically. Record
uncertain identity matches and proposed merges in `open-questions.md`.

### `analyses`

Contains explicit, derived analyses created for a question or decision. Each
analysis should state its purpose, distinguish inference from evidence, and
link to the primary pages it relies on.

Analyses are revisable interpretations, not durable personal memory. Important
decisions or confirmed lessons should return to the appropriate Layer 1 folder
through the review or project-writeback workflow.

### `index.md`

Provides generated navigation across processed wiki pages. It is a derived
index and should be refreshed by the wiki workflow rather than maintained as a
second source of truth.

### `log.md`

Records reviewed wiki processing activity and structural maintenance. Keep the
log concise and traceable to the relevant source or transaction.

### `open-questions.md`

Tracks unresolved contradictions, ambiguous identities, stale synthesis,
missing evidence, and proposed merges or renames. Questions remain open until
there is sufficient evidence or an explicit user decision.

## Processing Workflow

1. Place captures and imported material in `01 Notes/00 Raw`.
2. Read the wiki index and only the sources and primary notes relevant to the
   task.
3. Hash and inspect each selected source, preserving its provenance.
4. Create or update linked source, topic, entity, or analysis pages.
5. Record conflicts and uncertainty in `open-questions.md`.
6. Submit the complete change as one reviewed `wiki_process` broker
   transaction.
7. Archive successfully processed inputs in `01 Notes/99 Processed` and update
   the index and log as part of the same reviewed transaction.

Wiki changes and Raw-to-Processed moves must not be performed by editing files
directly outside the broker workflow. Interrupted transactions must be
recovered before another source is processed.

## Evidence and Retrieval

- Start with `01-strategy-storage/00 Memory` for durable personal context.
- Use the wiki index to locate relevant derived pages.
- Trace consequential claims through wiki source pages to their primary
  evidence.
- Surface conflicting sources and distinguish confirmed evidence, inference,
  and unanswered questions.
- Retrieve only task-relevant material; do not load the entire wiki by default.

## Privacy and Structure

- Wiki contents are private and must not be committed to Git.
- Do not store passwords, API keys, recovery codes, or private cryptographic
  keys here.
- Keep generated pages and transaction records inside `03-wiki`.
- Do not edit files under `01 Notes/99 Processed`.
- Do not merge entities, rename archived sources, or erase historical evidence
  without the protected review workflow.
