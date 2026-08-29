# ECHO — Stable Block (cacheable)

> The stable block is everything that must be present in full on every turn:
> persona, operating rules, core knowledge, capabilities. It changes only when
> a human edits its source files. The dynamic block — current time, per-turn
> recall results, session state — is never part of this file; it arrives as
> fresh tool output every turn.

## Assembly order (load verbatim, in this order)

1. **Persona** — `90-system/.echo/IDENTITY.md`, in full. It is the single
   source of persona truth; never inline a copy of it here, so a mid-run edit
   keeps taking effect on ECHO's very next response.
2. **Operating rules** — `02-skills-projects/skills/echo/SKILL.md`, in full
   (what ECHO is, fragment-first behavior, interaction pattern, v1
   boundaries, examples).
3. **Core knowledge** — `90-system/.echo/CORE_KNOWLEDGE.md`
   *(Tier 3 — slot reserved; file not yet created)*. Until it exists, skip
   this slot; never substitute guesses for its content.
4. **Capabilities** — `90-system/.echo/CAPABILITIES.md`
   *(Tier 8 — slot reserved; generated, not hand-written)*. Until it exists,
   ECHO claims only what this skill and the runtime's actually-exposed tools
   cover — never an invented capability.

## Cache marking

The stable block is cache-stable within a session: treat it as the cacheable
prefix. Only a change to its source files (IDENTITY.md, SKILL.md, or the
Tier 3 / Tier 8 files once they exist) invalidates it.

## Dynamic block (never cached)

Injected fresh each turn, as tool output:

- **Current time** — from the runtime, each turn.
- **Recall results** — `second-self-recall` (or the ECHO recall path) run
  per message; results are cited, tagged `[confirmed]` / `[inferred]` /
  `[not found]`, and never written back into the stable block.
- **Per-turn state** — anything transient the runtime exposes.

## Runtime mapping

| Runtime | Stable block loads via | Dynamic block arrives via |
| --- | --- | --- |
| Hermes (primary) | Rules/instructions file loaded into the system prompt each session, following this manifest's assembly order | Tool result per message |
| Claude Code | System prompt assembled from IDENTITY.md + SKILL.md | Tool result per message |
| Codex | Rules/instructions file, same sources | Tool result per message |
| Cline | Rules file under `90-system/.echo/` (a root `.clinerules/` thin pointer only if Cline demands root placement to auto-load) | Tool result per message |

The two-block split is a file convention, not engineered machinery:
**stable block = rules files, dynamic block = tool output.** If
`second-self-recall` becomes an MCP server, the split falls out for free.