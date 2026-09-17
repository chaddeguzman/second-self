# Semantic Memory Architecture Essentials

Source: `90-system/docs/semantic-memory/ARCHITECTURE.md`

- Markdown is authoritative; SQLite is private and rebuildable.
- Index metadata is path, source, content hash, model ID, and vector only.
- Sources: Layer 1 plus durable ECHO memory; exclude staging and sessions.
- Recall is unified, provenance-aware, deterministic, and keyword-fallback safe.
- Staleness is reported, not auto-refreshed during recall.
- Conflicts are surfaced for review, never silently resolved.
- Tests are synthetic and privacy-safe.
