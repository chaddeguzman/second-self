"""Ranked recall search across Layer 1 notes.

Scores results by folder priority, recency, tag strength (frontmatter tags
and body ``#tag`` mentions), and title match.  Higher score = more relevant.
"""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path
from typing import Any

from ..core.frontmatter import read_note
from ..core.paths import SecondSelfPaths

MAX_FILE_BYTES = 2 * 1024 * 1024
SNIPPET_RADIUS = 60
SKIPPED_DIRECTORIES = {"98-trash", "99-audit"}
EXCLUDED_FILES = {"tag registry.md"}

# Folder priority weights (higher = more important).
# 04 References ranks highest because most personal recall lives there;
# 00 Memory remains high for identity/values questions.
FOLDER_PRIORITY = {
    "04 references": 40,
    "00 memory": 30,
    "03 strategy": 25,
    "02 journal": 20,
    "05 reviews": 10,
    "01 capture": 5,
}

# Recency weights based on age in days.
RECENCY_BANDS = [
    (7, 30),
    (30, 20),
    (90, 10),
    (365, 5),
]

# Inline #tag mention in body text.
_INLINE_TAG_RE = re.compile(r"#([A-Za-z0-9_-]+)")


def _folder_priority(relative_path: str) -> int:
    """Return the folder priority weight for a Layer 1 note path."""
    first = relative_path.split("/", 1)[0].casefold()
    return FOLDER_PRIORITY.get(first, 0)


def _recency_score(created: date | None, today: date) -> int:
    """Return the recency weight based on note age."""
    if created is None:
        return 0
    age = (today - created).days
    if age < 0:
        return 0
    for days, weight in RECENCY_BANDS:
        if age <= days:
            return weight
    return 0


def _tag_score(tags: tuple[str, ...], body: str, query: str) -> int:
    """Return the tag strength weight.

    Exact frontmatter tag match = 20, partial frontmatter tag match = 10,
    body ``#tag`` mention = 5.
    """
    needle = query.casefold()
    for tag in tags:
        if tag.casefold() == needle:
            return 20
    for tag in tags:
        if needle in tag.casefold() or tag.casefold() in needle:
            return 10
    for match in _INLINE_TAG_RE.finditer(body):
        if match.group(1).casefold() == needle:
            return 5
    return 0


def _title_score(title: str, query: str) -> int:
    """Return 10 if the query appears in the title, else 0."""
    return 10 if query.casefold() in title.casefold() else 0


def _snippet(text: str, match_start: int, match_end: int) -> str:
    start = max(0, match_start - SNIPPET_RADIUS)
    end = min(len(text), match_end + SNIPPET_RADIUS)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


def _iter_layer1_notes(paths: SecondSelfPaths) -> list[tuple[Path, str]]:
    """Walk Layer 1 and return (path, relative_to_layer1) for each .md note."""
    root = paths.layer1
    if not root.is_dir():
        return []
    notes: list[tuple[Path, str]] = []
    try:
        walker = os.walk(root, followlinks=False)
        for directory, directories, files in walker:
            current = Path(directory)
            relative = current.relative_to(root)
            if relative == Path("."):
                directories[:] = [
                    name
                    for name in directories
                    if name.casefold() not in SKIPPED_DIRECTORIES
                ]
            for name in files:
                if not name.lower().endswith(".md"):
                    continue
                if name.casefold() in EXCLUDED_FILES:
                    continue
                path = current / name
                notes.append((path, path.relative_to(root).as_posix()))
    except OSError:
        return notes
    return notes


def recall_layer1(
    paths: SecondSelfPaths,
    query: str,
    *,
    max_results: int = 50,
    min_score: int = 0,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Ranked recall search across Layer 1 notes.

    Returns a list of result dicts sorted by score descending, then title.
    """
    query = query.strip()
    if not query:
        return []
    today = today or date.today()
    needle = query.casefold()

    results: list[dict[str, Any]] = []
    for path, relative in _iter_layer1_notes(paths):
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue

        # Parse frontmatter for tags and created date.
        tags: tuple[str, ...] = ()
        created: date | None = None
        try:
            metadata, body = read_note(path)
            raw_tags = metadata.get("tags")
            if isinstance(raw_tags, list):
                tags = tuple(
                    sorted(
                        {
                            str(tag).strip()
                            for tag in raw_tags
                            if isinstance(tag, str) and tag.strip()
                        }
                    )
                )
            created_raw = metadata.get("created")
            if isinstance(created_raw, date):
                created = created_raw
            elif isinstance(created_raw, str):
                try:
                    created = date.fromisoformat(created_raw[:10])
                except ValueError:
                    created = None
        except (OSError, UnicodeError, ValueError):
            body = text

        # Determine if the query matches anywhere.
        title_hit = needle in Path(relative).stem.casefold()
        tag_hit = _tag_score(tags, body, query) > 0
        body_index = body.casefold().find(needle)
        if not (title_hit or tag_hit or body_index != -1):
            continue

        folder = _folder_priority(relative)
        recency = _recency_score(created, today)
        tag = _tag_score(tags, body, query)
        title = _title_score(Path(relative).stem, query)
        score = folder + recency + tag + title

        if score < min_score:
            continue

        snippet = ""
        matched = ""
        if body_index != -1:
            snippet = _snippet(body, body_index, body_index + len(query))
            matched = body[body_index : body_index + len(query)]

        results.append(
            {
                "path": f"01-strategy-storage/{relative}",
                "title": Path(relative).stem,
                "score": score,
                "score_breakdown": {
                    "folder": folder,
                    "recency": recency,
                    "tag": tag,
                    "title": title,
                },
                "snippet": snippet,
                "matched": matched,
            }
        )

    results.sort(
        key=lambda entry: (entry["score"], str(entry["title"]).casefold()),
        reverse=True,
    )
    return results[:max_results]
