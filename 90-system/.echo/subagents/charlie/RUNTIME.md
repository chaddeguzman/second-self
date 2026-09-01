# Charlie — Runtime Contract

> What Charlie needs from the runtime to function. If any requirement is
> missing, Charlie reports `Blocked: missing tool X` instead of silently
> failing. This file is the spawn instruction for any runtime standing
> up a Charlie session.

## Required capabilities

| Capability | Why Charlie needs it |
|------------|---------------------|
| File read/write | Read SKILL.md, log.md, wip.md, patterns.md, shared/context.md; write results and status updates |
| Shell/command execution | Run tests, run the built code, verify behavior |
| Git access | Commit incrementally, use feature branches for large work |

## Required context files

| File | Purpose |
|------|---------|
| `SKILL.md` | Who Charlie is, how he works |
| `log.md` | Task queue and history |
| `wip.md` | In-progress build state (if present) |
| `patterns.md` | Accumulated patterns and anti-patterns |
| `../shared/context.md` | Current mission context from ECHO |

## Boot prompt (session opener)

The exact first message to give the LLM session when spawning Charlie:

```text
You are Charlie, ECHO's development sub-agent.
Your operating rules live in 90-system/.echo/subagents/charlie/SKILL.md.
Run your boot sequence now (per your SKILL.md), then report your status.
```

The session's very first instruction is to orient — no drift possible
before it happens.

## Verification steps (operator checklist)

After spawning a Charlie session, verify:

1. [ ] Session reports its status line (proves SKILL.md loaded)
2. [ ] Session can read its log.md (proves file access)
3. [ ] Session can run a trivial command (proves shell access)
4. [ ] Session can create a test file (proves write access)

If any step fails → the session reports `Blocked: missing [capability]`
and ECHO escalates to Chad.

## Runtime mapping

| Runtime | How to spawn Charlie |
|---------|---------------------|
| Hermes | New session with the boot prompt; grant file + shell + git tools |
| Claude Code | New session in the repo with the boot prompt; tools available natively |
| Codex | New session with the boot prompt; grant file + shell + git tools |