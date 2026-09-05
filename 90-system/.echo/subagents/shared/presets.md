# Delegation Presets

> Named delegation bundles ECHO applies when Chad uses the preset name.
> Chad says the preset name → apply the bundle; Chad can override any part.
> Presets are a convenience, not a straitjacket — the underlying
> conventions (subagents/README.md, Charlie's SKILL.md) still govern.

## Presets

| Preset | Agent | Task template | Project documents | Checkpoints | Confidence target |
|--------|-------|---------------|-------------------|-------------|-------------------|
| `quick-build` | Charlie | `build` | Skipped (size gate) | Single milestone | 90% |
| `full-build` | Charlie | `build` | PRD → Architecture → Essentials scaffold | 25/50/75% | 90% |
| `deep-dive` | Sherlock | `investigation` | None (investigation, not a build) | 75% | ≥ 85% |
| `research` | Walter | `research` | None (research, not a build) | None | 90% |

## Bundle details

### `quick-build`
- **Agent:** Charlie
- **When:** small feature, script, or fix — under the size gate
- **Docs:** none (size gate skips PRD/Architecture)
- **Milestones:** single deliverable, report when done
- **Handoff notes:** attach if relevant context exists

### `full-build`
- **Agent:** Charlie
- **When:** anything above the size gate — a real app, system, or tool
- **Docs:** PRD.md → ARCHITECTURE.md → ARCHITECTURE-ESSENTIALS.md,
  scaffolded before any feature code (templates in
  `subagents/shared/templates/`), plus thin per-project AGENTS.md
- **Milestones:** MVP → v1 → polished, reported incrementally
- **Checkpoints:** 25/50/75% log updates
- **Handoff notes:** always attach relevant context

### `deep-dive`
- **Agent:** Sherlock
- **When:** investigation, root-cause tracing, cross-referencing
- **Docs:** none — investigation output goes in the log + findings
- **Checkpoints:** 75% update
- **Confidence:** target ≥ 85%; below that, gaps are listed explicitly

### `research`
- **Agent:** Walter
- **When:** new topic, literature scan, source gathering
- **Docs:** none — findings with citations in the log
- **Confidence:** tagged per finding; gaps listed

## Overrides

Chad can override any part of a preset at delegation time:
- "full-build but skip the PRD" → Charlie builds without the doc scaffold
- "deep-dive with Walter instead" → reassign per the standard override rule
- "quick-build but give me checkpoints" → checkpoints added

The preset is a starting bundle, not a contract.