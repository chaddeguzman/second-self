from __future__ import annotations

from datetime import date
from pathlib import Path

from .paths import SecondSelfPaths


DIRECTORIES = [
    "01-strategy-storage/00-inbox",
    "01-strategy-storage/10-current",
    "01-strategy-storage/20-notes",
    "01-strategy-storage/30-journal",
    "01-strategy-storage/40-knowledge/books",
    "01-strategy-storage/40-knowledge/references",
    "01-strategy-storage/40-knowledge/quotes",
    "01-strategy-storage/40-knowledge/lessons",
    "01-strategy-storage/50-reviews/weekly",
    "01-strategy-storage/50-reviews/quarterly",
    "01-strategy-storage/55-conflicts",
    "01-strategy-storage/60-decisions",
    "01-strategy-storage/70-history",
    "01-strategy-storage/75-imports/originals",
    "01-strategy-storage/75-imports/extracted",
    "01-strategy-storage/80-assets",
    "01-strategy-storage/90-indexes",
    "01-strategy-storage/98-trash",
    "01-strategy-storage/99-audit/proposals",
    "02-skills-projects/projects",
]


CURRENT_FILES = {
    "01-strategy-storage/10-current/Current Identity.md": """---
type: identity
created: {today}
status: proposed
tags: []
projects: []
related: []
---

# Current Identity

## Purpose

## Values

## Principles

## Roles

## Preferences
""",
    "01-strategy-storage/10-current/Current Strategy.md": """---
type: strategy
created: {today}
status: proposed
tags: []
projects: []
related: []
---

# Current Strategy

## Direction

## Goals

## Current Priorities

## Commitments
""",
    "01-strategy-storage/55-conflicts/Conflicts Index.md": """---
type: conflict
created: {today}
status: active
tags: []
projects: []
related: []
---

# Conflicts Index

<!-- BEGIN GENERATED -->
No unresolved conflicts indexed.
<!-- END GENERATED -->
""",
    "01-strategy-storage/90-indexes/Content Index.md": """---
type: note
created: {today}
status: active
tags: []
projects: []
related: []
---

# Content Index

<!-- BEGIN GENERATED -->
Run `second-self indexes` to generate this section.
<!-- END GENERATED -->
""",
    "01-strategy-storage/Tag Registry.md": """---
type: reference
created: {today}
status: active
tags: []
projects: []
related: []
---

# Tag Registry

Agents must propose additions during review instead of creating near-duplicate
tags. Initial registered tags:

- weekly-review
- quarterly-review
""",
    "02-skills-projects/projects/Projects Index.md": """---
type: project
created: {today}
status: active
project_state: active
repository: ""
tags: []
projects: []
related: []
---

# Projects Index

<!-- BEGIN GENERATED -->
No projects registered.
<!-- END GENERATED -->
""",
}


def scaffold(paths: SecondSelfPaths) -> list[Path]:
    created: list[Path] = []
    for relative in DIRECTORIES:
        path = paths.data_root / relative
        if not path.exists():
            path.mkdir(parents=True)
            created.append(path)
    today = date.today().isoformat()
    for relative, template in CURRENT_FILES.items():
        path = paths.data_root / relative
        if not path.exists():
            path.write_text(template.format(today=today), encoding="utf-8")
            created.append(path)
    schema = paths.data_root / ".second-self-schema"
    if not schema.exists():
        schema.write_text("1\n", encoding="ascii")
        created.append(schema)
    return created
