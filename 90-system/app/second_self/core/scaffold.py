from __future__ import annotations

import json
from datetime import date
from importlib.resources import files
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

from .paths import SecondSelfPaths


def _load_public_scaffold_files() -> dict[str, tuple[str, ...]]:
    payload: Any = json.loads(
        files("second_self").joinpath("public_scaffold.json").read_text(encoding="utf-8")
    )
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != "second-self-public-scaffold"
        or payload.get("version") != 1
        or not isinstance(payload.get("roots"), list)
    ):
        raise ValueError("invalid public scaffold manifest")
    manifest: dict[str, tuple[str, ...]] = {}
    for entry in payload["roots"]:
        if not isinstance(entry, dict):
            raise ValueError("invalid public scaffold root")
        root = entry.get("path")
        raw_files = entry.get("files")
        if not isinstance(root, str) or not isinstance(raw_files, list):
            raise ValueError("invalid public scaffold root")
        root_path = PurePosixPath(root)
        if root_path.is_absolute() or ".." in root_path.parts or root in manifest:
            raise ValueError("invalid public scaffold root")
        public_files: list[str] = []
        for relative in raw_files:
            if not isinstance(relative, str):
                raise ValueError("invalid public scaffold file")
            relative_path = PurePosixPath(relative)
            if (
                relative_path.is_absolute()
                or ".." in relative_path.parts
                or relative in public_files
            ):
                raise ValueError("invalid public scaffold file")
            public_files.append(relative)
        manifest[root] = tuple(public_files)
    return manifest


PUBLIC_SCAFFOLD_FILES = _load_public_scaffold_files()
PUBLIC_SCAFFOLD_PATHS = frozenset(
    f"{root}/{relative}"
    for root, public_files in PUBLIC_SCAFFOLD_FILES.items()
    for relative in public_files
)


DIRECTORIES = [
    "01-strategy-storage/00 Memory",
    "01-strategy-storage/01 Capture/00 Raw",
    "01-strategy-storage/02 Journal",
    "01-strategy-storage/03 Strategy/01 Conflicts",
    "01-strategy-storage/03 Strategy/02 Decisions",
    "01-strategy-storage/04 References/01 books",
    "01-strategy-storage/04 References/02 quotes",
    "01-strategy-storage/04 References/03 research",
    "01-strategy-storage/04 References/04 guides",
    "01-strategy-storage/04 References/05 docs",
    "01-strategy-storage/04 References/06 Uncategorized",
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

| Type | Page | Description | Sources |
|------|------|-------------|---------|

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

| Date | Operation | Title | Details |
|------|-----------|-------|---------|
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
