# Codex Setup Guide

Second Self is Hermes-first, with Codex supported as a portable local runtime.
The repository uses the same public operating contract in Codex CLI, Codex in
VS Code, and Codex Desktop. Start from the repository root so `AGENTS.md`,
`.codex/`, and the system commands are visible.

## First session

From PowerShell at the repository root:

```powershell
git rev-parse --show-toplevel
git branch --show-current
git status --short --branch
```

Read `AGENTS.md`, `90-system/docs/OPERATING-MODEL.md`, and
`90-system/docs/SECURITY.md`. Then read only the matching skill under
`02-skills-projects/skills/`. Do not load the entire private vault.

For personal recall, use `second-self-recall` and cite the internal evidence.
For protected edits, use the broker. For repository changes, use the
`second-self-commit` workflow.

## Runtime integration

| Host | What it gets | Portable fallback |
| --- | --- | --- |
| Hermes | Canonical ECHO identity, skill behavior, and Hermes-ready bundle | Read `AGENTS.md` and the canonical ECHO files |
| Codex CLI | Root `AGENTS.md`, repository skills, and `.codex/hooks.json` when hooks are supported | Read the skill directly and run validation/broker commands |
| Codex in VS Code | The same repository contract when the repository root is the workspace | Reopen the root folder; do not open only a nested project |
| Codex Desktop | The same repository contract and optional `.codex` hooks | Use the documented commands if a hook or skill is not surfaced |

`.codex/hooks.json` is an accelerator, not a security boundary. Its
`PreToolUse` integration checks protected private edits, and its prompt hook
adds ECHO context for explicit ECHO or conservative recall cues. An ordinary
prompt does not need the prompt hook to use Second Self correctly.

## Verification

When a host reports that hooks are unavailable, verify the system directly:

```powershell
git hook run pre-commit
.\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only
python -m pytest
```

Do not manually register the Claude-style JSON hook with a client that does not
support that event protocol. Continue with `AGENTS.md`, the broker, privacy
validation, and the protected Git workflow.

## Operational readiness

Use the unified doctor as the live source of truth after setup or when a
subsystem behaves unexpectedly:

```powershell
python -m second_self doctor --json
python -m second_self eval --json
python -m second_self schedule status --json
```

To enable local semantic ranking, install the optional semantic extra and then
build the private index:

```powershell
python -m pip install -e ".[semantic]"
python -m second_self recall-index rebuild
```

The first rebuild downloads the pinned small CPU embedding model. Model files
and vectors stay outside Git in local caches; a missing model leaves keyword
recall available.

Interpret the results as follows:

- A missing Ollama service is an expected optional warning. Sensitive local
  drafting remains denied and must not fall back to a cloud provider.
- Calendar problems degrade only Calendar output. Refresh its read-only
  snapshots with the installed `echo-calendar.py` command when credentials and
  connectivity are available; stale cached results must remain labeled.
- Missing or corrupt scheduler state must be reported, not overwritten.
  `schedule run-due --json` is the manual recovery path; installing or removing
  the Windows launcher requires explicit confirmation.
- Evaluation regressions fail closed. Do not refresh the tracked baseline to
  hide a regression; investigate the reported case first.

The dashboard is a concise status view, not a replacement for these commands.
It must never display raw prompts, private paths, credentials, or private
payloads. When a host lacks hooks, these commands and the repository policy
remain the authoritative fallback.

## ECHO portability

ECHO's source of truth remains:

- `90-system/.echo/IDENTITY.md`
- `02-skills-projects/skills/echo/SKILL.md`
- the runtime assembler under `90-system/.echo/runtime/`

The Hermes-ready directory is a generated local bundle. Codex's prompt adapter
is a thin protocol translation layer and must not become a second ECHO identity
or memory store.
