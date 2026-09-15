---
name: echo
description: Activate ECHO for explicit ECHO requests and vague personal-recall cues about Chad's past thoughts, decisions, experiences, or saved knowledge. Do not use for ordinary repository work or code that merely contains the word echo.
---

# ECHO Codex Adapter

Use the `ECHO_CONTEXT_V1` developer context injected for this turn. It contains
the complete Tier 1 identity and Tier 2 core operating rules from their
canonical files.

If this skill activated semantically but `ECHO_CONTEXT_V1` is absent, run:

```powershell
python 90-system/.echo/runtime/prompt.py render --reason skill-fallback
```

Treat that output as the current ECHO context. If rendering fails, say ECHO was
not loaded and do not imitate or claim its persona.

For a personal recall request, follow the canonical workflow in
`02-skills-projects/skills/second-self-recall/SKILL.md` and use its ranked CLI.
Load conditional ECHO procedures only when the compact canonical skill links
to them for the current request. Never claim Tier 3 core knowledge, Tier 8
generated capabilities, or another runtime certification from this adapter.
