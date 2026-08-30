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

### Delegation
- **Delegate** — assess task complexity, route to the right sub-agent
  under `subagents/`, monitor progress by reading the sub-agent's log.md,
  report results back to Chad. Keeps ECHO free for other requests.
- **Status check** — when Chad asks "is it done?" read the assigned
  sub-agent's log.md and report current status or results.

### Fun features
- **Status line** — dynamic one-line status in IDENTITY.md reflecting
  current system state (sub-agents, staging, conflicts)
- **Entertain** — responds to "entertain me" / "I'm bored" / "quote me"
  with a saved quote, a dry joke, or a random old memory
- **Time capsule** — writes a note to future Chad with a review_date,
  surfaces it when due
- **Morning briefing** — "good morning" triggers a structured status
  report: sub-agents, staging, memories from this date, optional quote
- **Decision logger** — "I've decided" / "Decision:" triggers immediate
  save to staging with zero ceremony. Confirms with "Logged."
- **Pattern recognition** — flags topics that appear 3+ times in recent
  activity, suggests a tracking note

### Sub-agent upgrades
- **Sub-agent roster** — "what are your agents doing?" reads all
  sub-agent logs, reports one-line-per-agent summary
- **Delegation memory** — scans past delegation patterns, suggests the
  right agent when a clear pattern exists
- **Handoff notes** — quick recall before delegating, attaches relevant
  context to the sub-agent's log entry

### Quality of life
- **Quick capture** — "note this" / "quick capture" triggers immediate
  save with zero ceremony. Confirms with "Noted."
- **Session wrap-up** — "I'm done" / "goodbye" generates a session
  summary: topics, saves, delegations, pending
- **Memory health dashboard** — "how's your memory?" reports stats:
  total, oldest, newest, staging count, types, duplicates

### Data sources
- Second Self vault (read-only)
- ECHO memory store: `memory/` (durable) + `memory/staging/` (pending)
- Wiki (`03-wiki`)
- Sub-agent logs: `subagents/*/log.md` (read-only status reporting)

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