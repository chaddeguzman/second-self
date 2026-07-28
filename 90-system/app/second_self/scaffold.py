from __future__ import annotations

from datetime import date
from pathlib import Path

from .paths import SecondSelfPaths


DIRECTORIES = [
    "01-strategy-storage/00 Memory",
    "01-strategy-storage/01 Notes/00 Raw",
    "01-strategy-storage/01 Notes/01 Current",
    "01-strategy-storage/01 Notes/02 Notes",
    "01-strategy-storage/01 Notes/03 History",
    "01-strategy-storage/01 Notes/04 Imports/extracted",
    "01-strategy-storage/01 Notes/04 Imports/originals",
    "01-strategy-storage/01 Notes/05 Assets",
    "01-strategy-storage/01 Notes/99 Processed",
    "01-strategy-storage/02 Journal",
    "01-strategy-storage/03 Strategy/01 Conflicts",
    "01-strategy-storage/03 Strategy/02 Decisions",
    "01-strategy-storage/04 References/00 books",
    "01-strategy-storage/04 References/01 quotes",
    "01-strategy-storage/04 References/02 research",
    "01-strategy-storage/04 References/03 guides",
    "01-strategy-storage/04 References/04 docs",
    "01-strategy-storage/04 References/05 uncategorized",
    "01-strategy-storage/05 Reviews",
    "01-strategy-storage/98-trash",
    "01-strategy-storage/99-audit/indexes",
    "01-strategy-storage/99-audit/proposals",
    "02-skills-projects/projects",
    "03-wiki/sources",
    "03-wiki/topics",
    "03-wiki/entities",
    "03-wiki/analyses",
]


CURRENT_FILES = {
    "01-strategy-storage/01 Notes/01 Current/Current Identity.md": """---
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
    "01-strategy-storage/01 Notes/01 Current/Current Strategy.md": """---
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
    "01-strategy-storage/03 Strategy/01 Conflicts/Conflicts Index.md": """---
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
    "01-strategy-storage/99-audit/indexes/Content Index.md": """---
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
    "03-wiki/index.md": """---
type: wiki-index
created: {today}
status: active
verification: derived
tags: []
projects: []
related: []
---

# Wiki Index

<!-- BEGIN GENERATED -->
No wiki pages have been processed.
<!-- END GENERATED -->
""",
    "03-wiki/log.md": """---
type: wiki-log
created: {today}
status: active
verification: derived
tags: []
projects: []
related: []
---

# Wiki Log
""",
    "03-wiki/open-questions.md": """---
type: wiki-open-questions
created: {today}
status: active
verification: derived
tags: []
projects: []
related: []
---

# Open Questions

No open questions recorded.
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
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(template.format(today=today), encoding="utf-8")
            created.append(path)
    schema = paths.data_root / ".second-self-schema"
    if not schema.exists():
        schema.write_text("1\n", encoding="ascii")
        created.append(schema)
    return created


def scaffold_wiki(paths: SecondSelfPaths) -> list[Path]:
    created: list[Path] = []
    directories = [
        paths.raw,
        paths.processed,
        paths.wiki / "sources",
        paths.wiki / "topics",
        paths.wiki / "entities",
        paths.wiki / "analyses",
    ]
    for path in directories:
        if not path.exists():
            path.mkdir(parents=True)
            created.append(path)
    return created
