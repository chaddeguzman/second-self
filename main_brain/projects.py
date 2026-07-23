from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from pathlib import Path

from .paths import BrainPaths


LOCAL_PATHS = [
    ".agents/skills/main-brain/",
    ".codex/hooks.json",
    ".codex/main-brain-hook.py",
    "CLAUDE.local.md",
]


def _slug(value: str) -> str:
    return "-".join(part.lower() for part in "".join(
        character if character.isalnum() else " " for character in value
    ).split())


def registration_preview(paths: BrainPaths, project_path: Path, name: str) -> list[str]:
    project_path = project_path.resolve()
    return [
        f"Create private project record: {paths.projects / (_slug(name) + '.md')}",
        f"Create local Codex skill: {project_path / '.agents/skills/main-brain/SKILL.md'}",
        f"Create local Codex hooks: {project_path / '.codex/hooks.json'}",
        f"Create local Claude adapter: {project_path / 'CLAUDE.local.md'}",
        f"Add {len(LOCAL_PATHS)} entries to local .git/info/exclude",
    ]


def register_project(
    paths: BrainPaths, project_path: Path, name: str, repository: str = ""
) -> list[Path]:
    project_path = project_path.resolve()
    git_root_raw = subprocess.check_output(
        ["git", "-C", str(project_path), "rev-parse", "--show-toplevel"],
        text=True,
    ).strip()
    git_root = Path(git_root_raw).resolve()
    if git_root != project_path:
        raise ValueError(
            f"Project path must be a Git root. Detected Git root: {git_root}"
        )

    created: list[Path] = []
    today = date.today().isoformat()
    record = paths.projects / f"{_slug(name)}.md"
    repository_yaml = json.dumps(repository)
    local_path_yaml = json.dumps(str(project_path))
    if not record.exists():
        record.write_text(
            f"""---
type: project
created: {today}
status: active
project_state: active
repository: {repository_yaml}
local_path: {local_path_yaml}
tags: []
projects: []
related: []
---

# {name}

## Outcome

## Current Status

## Priorities

## Next Actions

## Decisions

## Lessons And Writeback
""",
            encoding="utf-8",
        )
        created.append(record)
    else:
        existing = record.read_text(encoding="utf-8")
        repaired = re.sub(
            r"^repository:.*$",
            lambda _: f"repository: {repository_yaml}",
            existing,
            flags=re.MULTILINE,
        )
        repaired = re.sub(
            r"^local_path:.*$",
            lambda _: f"local_path: {local_path_yaml}",
            repaired,
            flags=re.MULTILINE,
        )
        if repaired != existing:
            record.write_text(repaired, encoding="utf-8")
            created.append(record)

    skill = project_path / ".agents" / "skills" / "main-brain" / "SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text(
        f"""---
name: main-brain
description: Use the private Main Brain for personal context, project decisions, recall, and project writeback in this registered local repository.
---

# Main Brain

Read `{paths.repo_root / 'AGENTS.md'}` before using brain context.
Private data root: `{paths.data_root}`.
Project record: `{record}`.

Search private context only when relevant. Cite consequential claims. Update this
project record directly and send broader lessons to the Layer 1 inbox. Route
protected changes through the Main Brain edit broker.
""",
        encoding="utf-8",
    )
    created.append(skill)

    claude = project_path / "CLAUDE.local.md"
    claude.write_text(
        f"""# Main Brain Local Adapter

Read `{paths.repo_root / 'AGENTS.md'}` and use `{record}` as this project's
private brain record. Full private context at `{paths.data_root}` is available
for relevant local searches. Protected edits require the Main Brain broker.
""",
        encoding="utf-8",
    )
    created.append(claude)

    hook_source = paths.repo_root / "hooks" / "pre_tool_use.py"
    local_hook = project_path / ".codex" / "main-brain-hook.py"
    local_hook.parent.mkdir(parents=True, exist_ok=True)
    local_hook.write_text(
        f"import runpy\nrunpy.run_path({str(hook_source)!r}, run_name='__main__')\n",
        encoding="utf-8",
    )
    created.append(local_hook)
    hooks_json = project_path / ".codex" / "hooks.json"
    hooks_json.write_text(
        """{
  "description": "Main Brain protected-edit policy.",
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash|apply_patch|Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "python .codex/main-brain-hook.py",
        "commandWindows": "python .codex/main-brain-hook.py",
        "timeout": 10,
        "statusMessage": "Checking Main Brain edit policy"
      }]
    }]
  }
}
""",
        encoding="utf-8",
    )
    created.append(hooks_json)

    exclude = git_root / ".git" / "info" / "exclude"
    existing = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    additions = [value for value in LOCAL_PATHS if value not in existing.splitlines()]
    if additions:
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open("a", encoding="utf-8") as stream:
            if existing and not existing.endswith("\n"):
                stream.write("\n")
            stream.write("# Main Brain local adapters\n")
            stream.write("\n".join(additions) + "\n")
    return created
