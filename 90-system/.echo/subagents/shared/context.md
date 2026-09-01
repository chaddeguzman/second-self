# Shared Context — Sub-Agent Tasks

> Written by ECHO before delegating. Fresh per task; stale context is replaced,
> not accumulated. All sub-agents read this at task start.

## Current Task: ECHO Session Manager CLI

### Session file convention (from `90-system/.echo/hermes-ready/HERMES-SETUP.md`)

Sessions are one file each under `memory/sessions/`, named
`YYYY-MM-DDTHHMM.md`. Each has a one-line **session state** header including
`turn_count` and `mode` (for drift-check). The active session is pointed to
by `memory/current-session.md`.

Session files contain:
- A header line with session state (turn_count, mode, summary of aged-out turns)
- The most recent ~20 turns kept verbatim
- Durable facts are promoted to long-term memory; transient state ages out

### Task scope

Build a CLI tool (`echo-session`) that formalizes session management:

- **create** — start a new session file with the right naming convention
- **list** — show all sessions with their state headers
- **resume** — point `current-session.md` at an existing session for restart
- **archive** — move a session file (preserve, don't delete)
- **summary** — extract session state header (turn_count, mode, aged-out summary)

The tool should use the **existing** session file convention — not invent a
new format. It's a formalization of operations ECHO already does manually.

### Constraints

- Pure Python script (no external dependencies — `pyproject.toml` already
  manages `click` if needed, but stdlib `argparse` is preferred)
- No secrets handling
- No vault writes outside `memory/sessions/`
- Output format: clean CLI with `--help`

### Related files

- `90-system/.echo/hermes-ready/HERMES-SETUP.md` — session convention (this file)
- `90-system/.echo/memory/current-session.md` — if it exists, the pointer pattern
- `90-system/.echo/memory/sessions/` — session files live here
- `pyproject.toml` — available dependencies
- `requirements.lock` — pinned versions
