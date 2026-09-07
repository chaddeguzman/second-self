# Shared Context — Sub-Agent Tasks

> Written by ECHO before delegating. Fresh per task; stale context is replaced,
> not accumulated. All sub-agents read this at task start.

## Current Task: Project 3, Phase 1 only — echo-google-calendar scaffold

**Read first:** `02-skills-projects/projects/echo-google-calendar/PLAN.md`
(master status + hard rules), then
`02-skills-projects/projects/echo-google-calendar/phase-1-scaffold.md`
(the exact scope).

**Mission:** create the project documents (PRD, ARCHITECTURE,
ARCHITECTURE-ESSENTIALS, per-project AGENTS.md) in
`02-skills-projects/projects/echo-google-calendar/` and the code
skeleton (`echo-calendar.py` stubs, connector stubs, test scaffold) per
the phase file. Templates live in
`90-system/.echo/subagents/shared/templates/`.

**Locked decisions (from brainstorm with Chad — do not re-litigate):**
- Token storage: keyring primary, `.second-self.local.json` fallback
- Stack: official `google-api-python-client` + `google-auth-oauthlib`
- Fetch: live + snapshot fallback; scope today + week, single calendar,
  `calendar.readonly`
- Gmail/Drive: `NotImplementedError` stub interfaces ONLY — zero working code

**Hard boundaries:** Phase 1 is scaffold only — no OAuth code, no API
calls, no deps, no integration. Work EXACTLY this phase. Update the
phase file header, PLAN.md table, and your log together at completion.

## Background (why this exists)

OpenJarvis comparison review (2026-09-07): OpenJarvis's `jarvis connect
gdrive` covers Gmail/Calendar via one OAuth flow. ECHO's Phase 3 roadmap
includes read-only email/calendar. Chad chose a Calendar-first probe
(Gmail/Drive later as stubs), executed as five small phases so future
sessions never guess what's done. Phase 3 has a built-in human wall
(Chad's Google Cloud console setup) — Blocked status there is correct.

## Related files

- `02-skills-projects/projects/echo-google-calendar/` — plan + phases
- `90-system/.echo/scripts/echo-session.py` — style reference
- `90-system/tests/test_echo_session.py` — test style reference
- `90-system/docs/SECURITY.md` — token/secret rules (no secrets in Git)
- `90-system/.echo/subagents/shared/templates/` — doc templates