# Codex Adapter

This directory contains optional Codex-host integration for Second Self.

- `hooks.json` registers the protected-edit check and ECHO prompt enrichment
  when the Codex host supports repository hooks.
- `echo_prompt_hook.py` translates the portable ECHO assembler output into the
  Codex prompt-hook response shape.

The adapter is not the source of truth and is not a security boundary. The
portable contract is `../AGENTS.md`; canonical ECHO behavior lives under
`../90-system/.echo/`. If a Codex host does not load hooks, read the matching
skill directly and use the broker and validation commands documented in
`../90-system/docs/CODEX-SETUP-GUIDE.md`.
