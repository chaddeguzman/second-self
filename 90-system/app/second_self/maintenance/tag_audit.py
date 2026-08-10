"""Tag vocabulary audit for Layer 1 and project notes.

Detects unused registered tags, unregistered tags in use, and near-duplicate
tags against the canonical vocabulary in ``01-strategy-storage/Tag Registry.md``.

The audit is read-only by default.  When fixable near-duplicates are found,
:func:`build_tag_audit_proposal` generates a single broker ``edit`` proposal
so the user reviews the exact diff and answers Y/N once (same contract as
``link-fix``).
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.paths import SecondSelfPaths
from ..reads.dashboard import scan_dashboard

TAG_REGISTRY_RELATIVE = "01-strategy-storage/Tag Registry.md"
SIMILARITY_CUTOFF = 0.8
MAX_AUDIT_FILES = 10_000


@dataclass
class TagAuditResult:
    unused: list[dict[str, Any]] = field(default_factory=list)
    unregistered: list[dict[str, Any]] = field(default_factory=list)
    near_duplicates: list[dict[str, Any]] = field(default_factory=list)
    scanned_files: int = 0

    @property
    def valid(self) -> bool:
        return not (self.unused or self.near_duplicates)


def _normalize(tag: str) -> str:
    """Lowercase and strip non-alphanumeric characters for comparison."""
    return re.sub(r"[^a-z0-9]", "", tag.casefold())


def load_registered_tags(paths: SecondSelfPaths) -> list[str]:
    """Parse the canonical tag list from ``Tag Registry.md``.

    Tags are the bullet-list items following the line that contains
    ``Initial registered tags:`` (case-insensitive).  Each line matching
    ``- tagname`` is collected until the next heading or the end of file.
    """
    registry = paths.data_root / TAG_REGISTRY_RELATIVE
    if not registry.is_file():
        return []
    try:
        text = registry.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return []
    tags: list[str] = []
    in_section = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            in_section = False
            continue
        if "initial registered tags" in stripped.casefold():
            in_section = True
            continue
        if not in_section:
            continue
        if stripped.startswith("- "):
            tag = stripped[2:].strip()
            if tag and tag not in tags:
                tags.append(tag)
    return tags


def _scan_tags(paths: SecondSelfPaths) -> dict[str, list[dict[str, Any]]]:
    """Return a mapping of tag -> list of note descriptors using it."""
    snapshot = scan_dashboard(paths)
    result: dict[str, list[dict[str, Any]]] = {}
    for item in [*snapshot.layer1, *snapshot.projects]:
        for tag in item.tags:
            result.setdefault(tag, []).append(
                {
                    "path": item.relative_path,
                    "title": item.title,
                    "scope": item.scope,
                }
            )
    return result


def _resolve_note_path(paths: SecondSelfPaths, note: dict[str, Any]) -> Path:
    """Resolve a note descriptor to an absolute path."""
    if note["scope"] == "layer1":
        return paths.layer1 / note["path"]
    return paths.projects / note["path"]


def audit_tags(paths: SecondSelfPaths) -> TagAuditResult:
    """Run the tag vocabulary audit."""
    registered = load_registered_tags(paths)
    registered_set = {tag.casefold() for tag in registered}
    tag_usage = _scan_tags(paths)
    result = TagAuditResult(scanned_files=len(tag_usage))

    # Unused registered tags.
    for tag in registered:
        if tag.casefold() not in {key.casefold() for key in tag_usage}:
            result.unused.append({"tag": tag, "count": 0})

    # Unregistered tags in use.
    for tag, notes in sorted(tag_usage.items(), key=lambda pair: pair[0].casefold()):
        if tag.casefold() in registered_set:
            continue
        result.unregistered.append(
            {
                "tag": tag,
                "count": len(notes),
                "notes": notes[:5],
            }
        )

    # Near-duplicate detection against registered tags.
    normalized_registered = {_normalize(tag): tag for tag in registered}
    for tag, notes in sorted(tag_usage.items(), key=lambda pair: pair[0].casefold()):
        if tag.casefold() in registered_set:
            continue
        normalized = _normalize(tag)
        if normalized in normalized_registered:
            canonical = normalized_registered[normalized]
            result.near_duplicates.append(
                {
                    "tag": tag,
                    "canonical": canonical,
                    "count": len(notes),
                    "notes": notes[:5],
                    "fixable": True,
                }
            )
            continue
        matches = difflib.get_close_matches(
            normalized,
            list(normalized_registered.keys()),
            n=3,
            cutoff=SIMILARITY_CUTOFF,
        )
        if len(matches) == 1:
            canonical = normalized_registered[matches[0]]
            result.near_duplicates.append(
                {
                    "tag": tag,
                    "canonical": canonical,
                    "count": len(notes),
                    "notes": notes[:5],
                    "fixable": True,
                }
            )
        elif len(matches) > 1:
            result.near_duplicates.append(
                {
                    "tag": tag,
                    "canonical": None,
                    "candidates": [normalized_registered[m] for m in matches],
                    "count": len(notes),
                    "notes": notes[:5],
                    "fixable": False,
                }
            )
    return result


def _replace_tag_in_frontmatter(content: str, old_tag: str, new_tag: str) -> tuple[str, bool]:
    """Replace a tag in YAML frontmatter, preserving other fields."""
    if not content.startswith("---\n"):
        return content, False
    marker = content.find("\n---\n", 4)
    if marker == -1:
        return content, False
    body = content[marker + 5 :]
    # Reuse the same logic as tag_rename by parsing frontmatter directly.
    from ..core.frontmatter import split_frontmatter

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
    # Deduplicate preserving order.
    seen: set[str] = set()  # type: ignore[type-arg]
    deduped: list[str] = []
    for tag in new_tags:
        key = tag.strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(key)
    # Rebuild frontmatter preserving other fields.
    lines: list[str] = []
    for key, value in metadata.items():
        if key == "tags":
            lines.append(f"{key}: [{', '.join(deduped)}]")
        else:
            lines.append(f"{key}: {value}")
    new_content = "---\n" + "\n".join(lines) + "\n---\n" + body
    return new_content, replaced


def build_tag_audit_proposal(paths: SecondSelfPaths) -> dict[str, Any]:
    """Build a broker ``edit`` proposal for fixable near-duplicate tags.

    Returns a specification with ``operation: "edit"`` and ``changes`` entries
    (path + content) for every note that needs a tag replacement.  If no
    fixable near-duplicates exist, returns ``{"operation": "edit", "changes": []}``.
    """
    result = audit_tags(paths)
    fixable = [item for item in result.near_duplicates if item.get("fixable")]
    if not fixable:
        return {"operation": "edit", "changes": []}

    changes: list[dict[str, Any]] = []
    for item in fixable:
        old_tag = item["tag"]
        new_tag = item["canonical"]
        for note in item.get("notes", []):
            path = _resolve_note_path(paths, note)
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            new_text, replaced = _replace_tag_in_frontmatter(text, old_tag, new_tag)
            if not replaced:
                continue
            relative = path.relative_to(paths.data_root).as_posix()
            # Merge changes for the same file.
            existing = next((c for c in changes if c["path"] == relative), None)
            if existing:
                existing["content"] = new_text
            else:
                changes.append({"path": relative, "content": new_text})

    return {
        "operation": "edit",
        "changes": changes,
        "note": (
            f"Fix {len(fixable)} near-duplicate tag(s) across {len(changes)} note(s)."
        ),
    }