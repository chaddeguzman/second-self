# Semantic Memory Architecture

## Data flow

Markdown sources -> transient `SemanticDocument` -> optional local embedder ->
private SQLite vectors and metadata -> metadata-only semantic matches ->
source-backed recall results.

Layer 1 documents use `layer1/<relative path>` and ECHO durable memory uses
`memory/<relative path>`. Staging and session memory are excluded.

## Index contract

The index stores path, source, SHA-256 content hash, model identifier, and
packed vector. It never stores source text. `status()` compares supplied
current documents to indexed metadata and returns only aggregate counts and
model readiness. It does not create a database or run embedding work.
`refresh()` is explicit, atomic, and removes deleted paths. Its
`fallback_reason` is one of `semantic-index-ready`, `semantic-index-empty`,
`semantic-index-stale`, `semantic-model-mismatch`, or
`semantic-index-corrupt`.

The doctor command adds model availability and keyword-fallback state to the
same aggregate, with no source text, vectors, or filesystem paths.

## Recall contract

`hybrid_recall()` combines existing keyword results with optional semantic
matches from both sources. Results include provenance and retrieval mode.
Source text is read only through the normal evidence workflow. A stale index,
missing model, malformed vector, or semantic exception falls back to keyword
recall.

## Ranking and conflict policy

Keyword and semantic scores are normalized to bounded components. Strong exact
keyword evidence outranks weak semantic similarity; strong paraphrase evidence
can outrank weak keyword coincidence. Ties are deterministic. A conservative
claim parser compares returned preference/action claims for normalized polarity
and a bounded set of opposing objects, while conflict-oriented paths remain
flagged as well. Conflicting
evidence remains visible with a review flag and is never silently resolved.

## Privacy and compatibility

Evaluation fixtures are synthetic. Reports and diagnostics contain no source
text, private paths, vectors, or exception details. Existing Layer 1 recall
callers remain supported through the compatibility wrapper.
