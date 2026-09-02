# WIP: Build ECHO Session Manager CLI (echo-session)

**Status:** Done — 14/14 tests pass, self-review complete, confidence 90%

## Requirements interrogation

- **Problem:** ECHO manages sessions by hand-editing files. CLI formalizes the operations so they're repeatable and scriptable.
- **Users:** ECHO (auto-spawn/resume sessions), Chad (query session state manually)
- **Done:** Working `echo-session` CLI with 5 subcommands, 14 tests passing, documented.
- **Implicit:** Runs from repo root; pure Python (stdlib only); operates on `90-system/.echo/memory/sessions/`; manages `current-session.md` pointer.
- **Risks:** Writing a new format instead of reusing SESSION-CONVENTION.md; pointer file races; missing session files.

## Design

### Approach
- **Standalone script:** `90-system/.echo/scripts/echo-session.py`
  - Not a subcommand of the vault CLI — ECHO's runtime tooling stays in `.echo/`
  - Stdlib `argparse` (no new dependencies; matches existing CLI pattern)
  - Path resolution: default base dir `90-system/.echo/memory/`, overridable via `--base-dir`

### Commands
- `create` — Generate `YYYY-MM-DDTHHMM.md` filename, write session header + state, update pointer
- `list` — Scan sessions dir, parse headers, display table
- `resume [file]` — Validate file exists, update `current-session.md` pointer
- `archive [file]` — Rename `file` → `file.archived`, clear pointer if needed
- `summary [file]` — Parse session state header, print turn_count/mode/summary

### Session file format (follows SESSION-CONVENTION.md — NOT inventing new)
Reuses the existing session file convention exactly.

## Subtasks
- [x] Requirements interrogation
- [x] Design before code
- [x] Write echo-session.py with argparse subcommands
- [x] Write pytest tests (14 tests — all passing)
- [x] Run tests, verify — 14 passed
- [x] Self-review (below)

## Self-review

**Code quality:** Tested (14/14), documented (module docstring + --help), comments on path resolution and state parsing.

**Security:** No hardcoded secrets, input validation via regex on filenames, no external dependencies.

**Testing:** All 14 tests pass. Edge cases: missing sessions, empty dirs, no sessions dir, no current session, stdin prompt fallback.

**Deployment:** Pure Python 3.12+, stdlib only, `--base-dir` for config.

## Confidence: 90%

14 tests covering all 5 commands + edge cases. Limitation: no concurrency handling (acceptable for single-user ECHO). Untested on live ECHO memory — no real session files exist yet to test against.
