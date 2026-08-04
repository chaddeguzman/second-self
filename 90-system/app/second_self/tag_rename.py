from __future__ import annotations

from pathlib import Path
from typing import Any

from .frontmatter import split_frontmatter
from .paths import SecondSelfPaths


MAX_WARN_NOTES = 100


def _replace_tag_in_frontmatter(content: str, old_tag: str, new_tag: str) -> tuple[str, bool]:
    if not content.startswith("---\n"):
        return content, False
    marker = content.find("\n---\n", 4)
    if marker == -1:
        return content, False
    body = content[marker + 5 :]
    try:
        metadata, _ = split_frontmatter(content)
    except ValueError:
        return content, False
    tags = metadata.get("tags")
    if not isinstance(tags, list) or not tags:
        return content, False
    typed_tags: list[Any] = tags  # type: ignore[assignment]
    new_tags: list[str] = []
    replaced = False
    for tag in typed_tags:
        if not isinstance(tag, str):
            continue
        current = tag.strip()
        if current == old_tag:
            new_tags.append(new_tag)
            replaced = True
        else:
            new_tags.append(current)
    if not replaced:
        return content, False
    # deduplicate preserving order
    seen: set[str] = set()  # type: ignore[type-arg]
    deduped: list[str] = []
    for tag in new_tags:
        key = tag.strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(key)
    # Replace the tag in the YAML frontmatter while preserving other fields.
    lines: list[str] = []
    for key, value in metadata.items():
        if key == "tags":
            lines.append(f"{key}: [{', '.join(deduped)}]")
        else:
            lines.append(f"{key}: {value}")
    new_content = "---\n" + "\n".join(lines) + "\n---\n" + body
    return new_content, replaced


def build_tag_rename_proposal(
    paths: SecondSelfPaths, old_tag: str, new_tag: str
) -> dict[str, Any]:
    if old_tag == new_tag:
        raise ValueError("old_tag and new_tag must differ")
    snapshot_paths = [paths.layer1, paths.projects]
    affected: list[Path] = []
    changes: list[dict[str, Any]] = []
    for root in snapshot_paths:
        if not root.is_dir():
            continue
        for path in root.rglob("*.md"):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            new_text, replaced = _replace_tag_in_frontmatter(text, old_tag, new_tag)
            if not replaced:
                continue
            relative = path.relative_to(paths.data_root).as_posix()
            affected.append(path)
            changes.append(
                {
                    "path": relative,
                    "content": new_text,
                }
            )
    if not changes:
        raise ValueError(f"No notes contain tag: {old_tag}")
    if len(changes) > MAX_WARN_NOTES:
        raise ValueError(
            f"Refusing to rename tag across {len(changes)} notes; "
            f"limit is {MAX_WARN_NOTES} to avoid accidental bulk edits."
        )
    return {
        "operation": "edit",
        "changes": changes,
        "note": f"Rename tag {old_tag!r} to {new_tag!r} across {len(changes)} notes.",
    }