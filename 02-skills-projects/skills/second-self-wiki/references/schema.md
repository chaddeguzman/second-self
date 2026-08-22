# Second Self Wiki Schema

## Invariants

- Raw is pending; References is the single source of truth.
- Existing curated notes stay in place.
- Every generated page has valid frontmatter and `verification: derived`.
- Topic, entity, and analysis claims trace to source pages.
- Source pages link to the actual archived or in-place evidence.
- Use relative Markdown links. Preserve `log.md` history.
- Do not create links solely to eliminate an orphan.

## Source pages

Store under `03-wiki/sources/<source-id-prefix>-<slug>.md`.

Required frontmatter:

```yaml
type: wiki-source
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
verification: derived
source_id: <12-char truncated sha256 or bundle manifest hash>
source_path: <private-relative final path>
source_sha256: <full sha256 or bundle manifest hash>
source_kind: <format or bundle>
processed_at: <ISO timestamp>
duplicate_of: ""
supersedes: ""
tags: []
projects: []
related: []
```

`source_id` is the first 12 hex characters (48 bits) of the SHA-256 digest,
matching the source-page filename prefix (e.g. `072958a2620b-<slug>.md`). It
serves as the primary key for deduplication and is collision-safe for a
personal vault. `source_sha256` retains the full 64-character digest and is
used for integrity and change detection.

Use sections: Summary, Key Evidence, Connections, Uncertainties, and Source.
Label visual transcription or interpretation as agent-generated.

## Topic, entity, and analysis pages

Required frontmatter:

```yaml
type: wiki-topic # or wiki-entity / wiki-analysis
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
verification: derived
source_ids: []
source_count: 0
tags: []
projects: []
related: []
```

Use claim-level source links where practical. Include tensions or uncertainty
instead of flattening disagreement.

## Special files

- `index.md`: retain generated markers; catalog every page in a unified table with columns `| Type | Page | Description | Sources |`. Type is `Topic` or `Source`; Page is a relative Markdown link; Sources is a count for topics or `—` for source pages.
- `log.md`: maintain a table with columns `| Date | Operation | Title | Details |`. Operation is one of `ingest`, `query`, `lint`, `refresh`, or `duplicate`. Details joins multiple bullet points with `<br>` tags. New rows are prepended bottom-to-top (latest entry is the first data row).
- `open-questions.md`: record contradictory claims, ambiguous identities, stale material, and missing evidence.

## Broker specification

Use:

```json
{
  "operation": "wiki_process",
  "changes": [{"path": "03-wiki/...", "content": "..."}],
  "moves": [{
    "from": "01-strategy-storage/01 Capture/00 Raw/...",
    "to": "01-strategy-storage/04 References/{subfolder}/OriginalName.ext"
  }]
}
```

The broker limits a proposal to ten moved source units, verifies input hashes,
validates generated pages, journals the transaction, and rolls back synchronous
failures.

Preserve the original source name and extension. Add a minimal numeric suffix
only when names collide. The broker removes emptied Raw parent folders after
the transaction succeeds.
