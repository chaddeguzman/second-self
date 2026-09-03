# Architecture — [Project Name]

> Complete technical design. Created at project start, before any code.
> Source of truth for HOW the product is built. Update whenever the design
> changes; regenerate ARCHITECTURE-ESSENTIALS.md at the same time.
> Maintained by the building agent (e.g. Charlie).

## Overview

[One paragraph: what this system is and its shape at a high level.]

## Tech stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language | [e.g. Python 3.12] | [reason] |
| Framework | [e.g. FastAPI] | [reason] |
| Storage | [e.g. SQLite] | [reason] |
| Runtime | [e.g. local CLI] | [reason] |

[Stack choice is an "Ask Chad" decision — irreversible and expensive to
undo. Flag it in the task output, don't just record it.]

## Data models

### [Model name]

[Purpose in one line.]

```
[field: type — constraint/note]
```

## Components

### [Component name]

- **Responsibility:** [one thing it does well]
- **Interfaces:** [what it exposes, what it consumes]

## Data flow

```
input → [transformation] → output
```

[Describe the flow in one or two sentences. For multiple flows, one
diagram-ish line each.]

## Key decisions

| Decision | Alternatives considered | Why this one |
|----------|------------------------|--------------|
| [decision] | [what else was on the table] | [reasoning] |

## Project structure

```
[folder tree as scaffolded — see "Scaffold-first" in Charlie's SKILL.md;
structure exists before features, even if files are stubs]
```

## Deployment considerations

- **Environment:** [where this runs]
- **Configuration:** [env vars / config files — never hardcoded]
- **Dependencies:** [external services or packages]
- **Rollback:** [how to revert if it breaks]

## Open items

- [Design items still unresolved. Anything blocking goes through the
  questions protocol before build starts.]