# Second Self — Agent Instructions

First read [AGENTS.md](AGENTS.md) — it is the canonical startup guide for any
agent. The sections below add Claude/Cline-specific notes only; they do not
override the Hermes-first, runtime-neutral contract.

## Startup

AGENTS.md already covers the full startup sequence. After completing it:

- If this is a Claude Code session, the `pre_tool_use hook` in
  `90-system/automation/hooks/pre_tool_use.py` may block accidental protected
  changes. Codex uses the same policy through `.codex/hooks.json` when its host
  supports repository hooks. Cline and other clients should use the portable
  policy and broker rather than manually registering this JSON event hook.
- Resolve private paths through `.second-self.local.json`; never hard-code them.

## Skills

Browse `02-skills-projects/skills/` to discover available skills. Each skill
has a `SKILL.md` with instructions. Use the host's skill activation when it is
available. Otherwise, read the matching `SKILL.md` directly and follow the
instructions manually.

## Personal Recall

Follow the recall workflow in AGENTS.md. Key points:

1. Start by checking `04 References` subfolders for most requests; begin with
   `00 Memory` only for identity/values questions.
2. Use the `second-self-recall` skill.
3. Cite stored sources and dates. Do not invent personal context.

## Verification

Run before committing tracked changes:

```powershell
.\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only
python -m pytest
```

For wiki or template changes also run `second-self-wiki lint`.
