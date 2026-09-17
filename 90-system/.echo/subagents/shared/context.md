# Shared Context — Sub-Agent Tasks

> Written by ECHO before delegating. Fresh per task; stale context is replaced,
> not accumulated. All sub-agents read this at task start.

## Current Task: None

The semantic-memory acceptance-gap continuation is complete. Future work must
write a fresh task-specific context before delegation.

**Current project snapshot:**
- `echo-google-calendar/PLAN.md`: all 5 phases Done; read-only Calendar is integrated.
- `echo-local-agent-foundation/PLAN.md`: all 17 phases Done; foundation is complete.
- Next planned cycle: reconcile operational status and harden readiness. Local-
  only privacy and safe keyword fallback remain mandatory.

**Current boundaries:** Calendar remains read-only; Gmail and Drive remain
stubs; future tasks must write a fresh exact scope before delegation.

## Background (why this exists)

OpenJarvis comparison review (2026-09-07) led to a Calendar-first probe.
Calendar is now integrated as a read-only connector; Gmail and Drive remain
stubs by design.

## Related files

- `02-skills-projects/projects/echo-google-calendar/` — plan + phases
- `90-system/.echo/scripts/echo-session.py` — style reference
- `90-system/tests/test_echo_session.py` — test style reference
- `90-system/docs/SECURITY.md` — token/secret rules (no secrets in Git)
- `90-system/.echo/subagents/shared/templates/` — doc templates
