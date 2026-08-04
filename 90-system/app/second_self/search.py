from __future__ import annotations

import os
from pathlib import Path

from .paths import SecondSelfPaths


MAX_FILE_BYTES = 2 * 1024 * 1024
SNIPPET_RADIUS = 60
SKIPPED_DIRECTORIES = {"98-trash", "99-audit"}


def _snippet(text: str, match_start: int, match_end: int) -> str:
    start = max(0, match_start - SNIPPET_RADIUS)
    end = min(len(text), match_end + SNIPPET_RADIUS)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


def search_layer1(
    paths: SecondSelfPaths, query: str, *, max_results: int = 50
) -> list[dict[str, str]]:
    query = query.strip()
    if not query:
        return []
    needle = query.casefold()
    results: list[dict[str, str]] = []
    root = paths.layer1
    if not root.is_dir():
        return results
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
                if len(results) >= max_results:
                    return results
                path = current / name
                try:
                    if path.stat().st_size > MAX_FILE_BYTES:
                        continue
                    text = path.read_text(encoding="utf-8")
                except (OSError, UnicodeError):
                    continue
                index = text.casefold().find(needle)
                if index == -1:
                    continue
                results.append(
                    {
                        "path": path.relative_to(paths.data_root).as_posix(),
                        "snippet": _snippet(text, index, index + len(query)),
                        "matched": text[index : index + len(query)],
                    }
                )
    except OSError:
        return results
    return results