# Shared Context — Sub-Agent Tasks

> Written by ECHO before delegating. Fresh per task; stale context is replaced,
> not accumulated. All sub-agents read this at task start.

## Current Task Queue: Two Projects for Charlie

Work them in order. Project 1 first; Project 2 starts after Project 1 is Done.

---

### Project 1 — `echo doctor` + recurring-task upgrades

**Source of ideas:** OpenJarvis comparison review (2026-09-04). Borrowing
`jarvis doctor` and their scheduler's pause/resume/run-history concepts,
adapted to ECHO's file-convention philosophy — no daemon, no machinery.

#### Part A: `echo doctor` (new CLI, sibling to echo-session)

Create `90-system/.echo/scripts/echo-doctor.py` — a health check for
ECHO's file convention. Same style as echo-session.py: standalone,
stdlib-only argparse, `--base-dir` override, module docstring with usage,
file header comment per Charlie's commenting convention.

Checks (each reports OK / WARN / FAIL with a one-line reason):

1. **Stable-block files present** — `IDENTITY.md`, `STABLE_BLOCK.md`,
   `RECALL.md`, `MEMORY-TOOLS.md`, `CAPABILITIES.md`, `CAPABILITY-LIST.md`,
   `subagents/README.md` exist under `90-system/.echo/`
2. **Session pointer valid** — `memory/current-session.md` either absent,
   or points at an existing session file
3. **Staging queue size** — count files in `memory/staging/`; WARN if > 10
4. **Log status lines well-formed** — each `subagents/*/log.md` starts with
   `# [Name] — Status: [value]`
5. **Stale wip.md detection** — any `subagents/*/wip.md` whose log.md shows
   the latest task Done is stale (per the self-healing rule); WARN and
   offer deletion with `--fix`
6. **Session filename sanity** — files in `memory/sessions/` match
   `YYYY-MM-DDTHHMM.md` (flag `.archived` files separately as OK)

Flags: `--fix` (apply safe fixes: delete stale wip.md files),
`--strict` (exit 1 on any WARN or FAIL — for pre-commit gating),
`--json` (machine-readable output, paths redacted by default).

Tests in `90-system/tests/test_echo_doctor.py`, mirroring
test_echo_session.py's subprocess style. Cover: all-OK case, each WARN/FAIL
case, `--fix` behavior, `--strict` exit codes, `--json` output.

Document it: add rows to CAPABILITY-LIST.md's "CLI Tools" section and a
"CLI tools" bullet in CAPABILITIES.md (toolset changes → regenerate).

#### Part B: Recurring-task upgrades (convention changes, no code)

Update the recurring-task convention in
`90-system/.echo/subagents/README.md` and the matching section in
`02-skills-projects/skills/echo/SKILL.md`:

1. **Pause/resume** — `recurring.md` rows gain a `Status` column
   (`active` / `paused`). "Pause the weekly digest" sets `paused`; paused
   tasks are skipped by the due-check but never deleted. "Resume" sets
   `active` and recomputes next due from now.
2. **Next-due surfacing** — morning briefing and "run recurring tasks"
   report upcoming due dates ("weekly digest due tomorrow"), computed from
   Schedule + Last run.
3. **Run history** — each agent maintains `recurring-history.md`:
   append-only table (Date / Task / Outcome / Notes), last ~20 runs kept.
   "Has the digest been running?" is answered from this file, not memory.

Update the `recurring.md` example table in both files to show the new
Status column.

---

### Project 2 — Delegation presets + monthly pattern harvest

Starts after Project 1 is Done and merged.

#### Part A: Delegation presets (new convention)

Create `90-system/.echo/subagents/shared/presets.md` — named delegation
bundles ECHO applies when Chad uses the preset name:

| Preset | Bundle |
|--------|--------|
| `quick-build` | Charlie; size-gate docs skipped; single milestone |
| `full-build` | Charlie; PRD → Architecture → Essentials scaffold; incremental milestones; 25/50/75% checkpoints |
| `deep-dive` | Sherlock; handoff notes attached; 75% checkpoints; confidence ≥ 85% target |
| `research` | Walter; multi-source; confidence tagged; gaps listed |

Each preset lists: agent, task template, project-document requirements,
checkpoint expectations, and any confidence target. ECHO's SKILL.md
delegation section gets a short "Delegation presets" subsection pointing
at the file ("Chad says the preset name → apply the bundle; Chad can
override any part").

#### Part B: Monthly pattern harvest (upgrades monthly agent review)

Add a "Pattern harvest" step to the monthly agent review flow in
`02-skills-projects/skills/echo/SKILL.md` (after compiling activity,
before writing the review file):

1. Scan the month's sub-agent logs + lessons learned
2. Propose 1–2 concrete updates: a patterns.md addition, an anti-pattern,
   or a small SKILL.md edit — each as a proposal with evidence (which
   tasks, what kept going wrong or right)
3. Present to Chad for approval — same staging-gate pattern as memory
   (agents propose, ECHO brokers, Chad approves)
4. On approval, apply the update and note it in the review file

This turns patterns.md from write-once into a compounding, reviewed loop.

---

### Constraints (both projects)

- Pure Python stdlib only (match echo-session.py); no new dependencies
- No vault writes outside `90-system/.echo/`; no secrets handling
- Follow Charlie's SKILL.md: size gate applies — Project 1 Part A is a
  real build (write a brief PRD + ARCHITECTURE-ESSENTIALS in the task
  entry or wip.md while working; delete wip.md on completion per the new
  rule); Part B and Project 2 are convention edits (no project docs needed)
- Tests must pass: `python -m pytest` from repo root
- Update log.md at 25/50/75% checkpoints for Project 1 Part A

### Related files

- `90-system/.echo/scripts/echo-session.py` — style reference for echo-doctor
- `90-system/tests/test_echo_session.py` — test style reference
- `90-system/.echo/subagents/README.md` — conventions to update (recurring, presets)
- `02-skills-projects/skills/echo/SKILL.md` — ECHO-side flow updates
- `90-system/.echo/CAPABILITY-LIST.md` + `CAPABILITIES.md` — doc updates for new CLI