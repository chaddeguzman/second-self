from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

from .frontmatter import read_note
from .paths import SecondSelfPaths


BEGIN = "<!-- BEGIN GENERATED -->"
END = "<!-- END GENERATED -->"


def _replace_generated(path: Path, lines: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    start = text.index(BEGIN) + len(BEGIN)
    finish = text.index(END)
    generated = "\n" + ("\n".join(lines) if lines else "No matching records.") + "\n"
    path.write_text(text[:start] + generated + text[finish:], encoding="utf-8")


def _link(from_file: Path, target: Path) -> str:
    relative = os.path.relpath(target, from_file.parent).replace("\\", "/")
    return f"[{target.stem}]({relative.replace(' ', '%20')})"


def generate_indexes(paths: SecondSelfPaths) -> dict[str, int]:
    notes: list[tuple[Path, dict]] = []
    for path in paths.data_root.rglob("*.md"):
        if "98-trash" in path.parts:
            continue
        try:
            metadata, _ = read_note(path)
        except (OSError, ValueError):
            continue
        if metadata:
            notes.append((path, metadata))

    content_index = paths.layer1 / "90-indexes" / "Content Index.md"
    grouped: dict[str, list[Path]] = defaultdict(list)
    for path, metadata in notes:
        grouped[str(metadata.get("type", "unknown"))].append(path)
    content_lines: list[str] = []
    for note_type in sorted(grouped):
        content_lines.append(f"## {note_type.title()}")
        for path in sorted(grouped[note_type], key=lambda value: value.name.lower()):
            if path != content_index:
                content_lines.append(f"- {_link(content_index, path)}")
        content_lines.append("")
    _replace_generated(content_index, content_lines)

    projects_index = paths.projects / "Projects Index.md"
    projects = [
        (path, meta)
        for path, meta in notes
        if meta.get("type") == "project" and path != projects_index
    ]
    project_lines = [
        f"- {_link(projects_index, path)} - `{meta.get('project_state', 'unknown')}`"
        for path, meta in sorted(projects, key=lambda item: item[0].name.lower())
    ]
    _replace_generated(projects_index, project_lines)

    conflicts_index = paths.layer1 / "55-conflicts" / "Conflicts Index.md"
    conflicts = [
        path
        for path, meta in notes
        if meta.get("type") == "conflict"
        and meta.get("status") in {"inbox", "proposed", "active"}
        and path != conflicts_index
    ]
    _replace_generated(
        conflicts_index,
        [f"- {_link(conflicts_index, path)}" for path in sorted(conflicts)],
    )
    return {"notes": len(notes), "projects": len(projects), "conflicts": len(conflicts)}

