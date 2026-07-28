# Second Self — Agent Instructions

First read [AGENTS.md](AGENTS.md) — it is the canonical startup guide for any
agent. The sections below add Claude/Cline-specific notes.

## Startup

AGENTS.md already covers the full startup sequence. After completing it:

- If this is a Claude Code session, the `pre_tool_use hook` in
  `90-system/automation/hooks/pre_tool_use.py` may block accidental protected
  changes. Other agents (Cline, Deepseek, Cursor, Windsurf) do not use this
  hook.
- Resolve private paths through `.second-self.local.json`; never hard-code them.

## Skills

Browse `02-skills-projects/skills/` to discover available skills. Each skill
has a `SKILL.md` with instructions. Use `use_skill` when a task matches a
skill's description. If `use_skill` is unavailable, read the SKILL.md directly
and follow the instructions manually.

## Personal Recall

Follow the recall workflow in AGENTS.md. Key points:

1. Start in `01-strategy-storage/00 Memory`, then assemble broader context.
2. Use the `second-self-recall` skill.
3. Cite stored sources and dates. Do not invent personal context.

## Verification

Run before committing tracked changes:

```powershell
.\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only
python -m pytest
```

For wiki or template changes also run `second-self-wiki lint`.