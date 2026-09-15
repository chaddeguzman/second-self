# ECHO — Stable and Dynamic Context

`ECHO_CONTEXT_V1` is assembled afresh for every matched Codex prompt by
`90-system/.echo/runtime/prompt.py`. The assembler is deterministic and
provider-neutral; `.codex/echo_prompt_hook.py` only translates the Codex hook
protocol.

## Stable block

The stable block contains, in this exact order:

1. the complete canonical `90-system/.echo/IDENTITY.md`;
2. the complete canonical `02-skills-projects/skills/echo/SKILL.md`;
3. explicit markers stating that Tier 3 core knowledge and Tier 8 generated
   capabilities are not loaded in this cycle.

The assembler computes a SHA-256 fingerprint over the stable block bytes. The
block and fingerprint remain identical until a canonical source changes. Both
sources are read again on every matched turn, so an edit is visible without a
process or session restart.

## Dynamic block

The dynamic suffix contains the Asia/Shanghai timestamp, activation reason,
and a statement that recall results must be retrieved for the current request.
It may change every turn and is excluded from the stable fingerprint.

The complete envelope is limited to 8,000 UTF-8 bytes to remain below Codex's
approximate 2,500-token model-visible hook-output ceiling. Assembly failures
produce a short privacy-safe context: ECHO is not loaded, the prompt continues,
and no absolute or private path is exposed.

## Codex activation

`.codex/hooks.json` registers a `UserPromptSubmit` hook. It injects the envelope
as `hookSpecificOutput.additionalContext` for explicit ECHO invocations and
conservative personal-recall cues. It emits nothing for ordinary prompts,
shell `echo` commands, or identifiers that merely contain “echo.” The
repo-local `.agents/skills/echo/SKILL.md` provides discovery and a render
fallback when semantic skill activation falls outside those hook patterns.

## Runtime certification

| Runtime | Tier 1–2 status |
| --- | --- |
| Codex Desktop | Tier 1–2 certified 2026-09-15 by automated checks and a disposable-repository live session |
| Cline | Documented, not certified in this cycle |
| Claude Code | Documented, not certified in this cycle |
| Hermes | Bundle refreshed from canonical files, not certified in this cycle |

The certification observed nonzero `cached_input_tokens`, including 30,976 on
the resumed BETA turn. This records one run; provider-side caching is never
required or promised.
