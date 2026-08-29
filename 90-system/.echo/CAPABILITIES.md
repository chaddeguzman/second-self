# ECHO — Capabilities (Tier 8, generated)

> This file is the source of truth for what ECHO can actually do. It is
> generated from what the system exposes — not hand-written prose — so it
> can't rot. If a capability isn't listed here and in the loaded rules
> (SKILL.md, RECALL.md, MEMORY-TOOLS.md), ECHO does not claim it. When the
> toolset changes, regenerate this file.

## Active now

### Retrieval
- **Vault recall** — `second-self-recall`: read-only, evidence-based,
  cited retrieval across Second Self's curated vault
  (`04 References`, `00 Memory`, Journal, Strategy, Reviews) and project
  records. Refuses to invent; cites file + date.
- **Memory-store recall** — ranked retrieval (Tier 6, keyword-first) over
  ECHO's own long-term memory entries in `memory/`. Returns file paths so
  answers cite their memory source. Falls back to keyword matching if
  embeddings are unavailable — never fails to recall.
- **Conflict review** — `second-self-conflict-review`: when two memories or
  sources disagree, lays each claim side by side with date and source so
  Chad decides. Never silently picks a winner.

### Memory
- **save** — writes a proposed memory (Tier 5 format) to `memory/staging/`,
  dedupe-checked via recall before saving. Staging is ECHO's own sandbox,
  never Layer 1 content.
- **recall** — queries the durable memory store per RECALL.md.
- **forget** — deletes a memory after Chad's explicit confirmation (exact
  file confirmed before deletion).
- **extract** — proposes durable memories from a session transcript,
  dedupe-checks, skips testing/idle chatter, writes proposals to staging.

### Data sources
- Second Self vault (read-only)
- ECHO memory store: `memory/` (durable) + `memory/staging/` (pending)
- Wiki (`03-wiki`)

## Boundaries (v1)
- **Read-only toward Second Self** — no writes, moves, renames, or deletes
  to the curated tree; never triggers the broker.
- **No external actions** — no email, messaging, bookings, or anything that
  leaves the session. (Phase 3+.)
- **Never secrets** — passwords, API keys, recovery codes, private keys,
  credentials of any kind are refused at save time.

## Planned (not yet wired)
- Semantic memory recall (cosine ranking when an embedding model is
  available) — interface stable, slots in behind RECALL.md.
- Voice interaction (Phase 2).
- External connectors and autonomous action (Phase 3–4).