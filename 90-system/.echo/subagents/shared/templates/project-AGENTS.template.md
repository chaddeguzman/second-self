# AGENTS.md — [Project Name]

> Thin per-project agent rules. This file travels with the project so any
> agent session opened inside the project folder has the right context —
> sub-agent sessions receive no ECHO persona or vault context by design.
> Keep it thin: it POINTS, it never forks. System-level rules (privacy,
> evidence, protected changes) stay governed by Second Self's root
> AGENTS.md and are inherited, not duplicated here.

## Project documents (read in this order)

1. `ARCHITECTURE-ESSENTIALS.md` — critical decisions, load at boot
2. `PRD.md` — scope and "done" definition; consult before adding anything
3. `ARCHITECTURE.md` — full design; consult for deep work, not every turn

## Project conventions

- **Commands:** [build / run / test commands]
- **Test runner:** [e.g. pytest]
- **Code style:** [e.g. PEP 8, type hints required]
- **Commit style:** [e.g. conventional commits, what + why]

## Boundaries

- Follow the building agent's operating rules (e.g.
  `90-system/.echo/subagents/charlie/SKILL.md` in the Second Self repo).
- Never commit secrets; never hardcode private paths.
- Scope changes go through the PRD, not ad hoc edits.