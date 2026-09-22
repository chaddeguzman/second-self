"""Canonical Obsidian wikilink formatting, parsing, and resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from ..core.paths import SecondSelfPaths


_WIKILINK_RE = re.compile(
    r"(?P<embed>!)?\[\[(?P<target>[^\]|]+)(?:\|(?P<alias>[^\]]*))?\]\]"
)
_FENCE_RE = re.compile(r"(```+|~~~+)")
_FRAGMENT_RE = re.compile(r"(?:#|\^).*$")


@dataclass(frozen=True)
class WikiLink:
    target: str
    alias: str | None
    is_embed: bool
    line: int
    column: int


def format_wikilink(target: str, alias: str | None = None) -> str:
    target = target.replace("\\", "/").strip()
    if not target or any(char in target for char in "[]\r\n"):
        raise ValueError("wikilink target is invalid")
    if alias is None:
        return f"[[{target}]]"
    alias = alias.replace("\r", " ").replace("\n", " ").replace("]", "").strip()
    if not alias:
        raise ValueError("wikilink alias is empty")
    return f"[[{target}|{alias}]]"


def parse_wikilinks(text: str) -> list[WikiLink]:
    links: list[WikiLink] = []
    in_fence = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        if _FENCE_RE.search(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for inline in re.finditer(r"`[^`]*`", line):
            line = line.replace(inline.group(0), " " * len(inline.group(0)), 1)
        for match in _WIKILINK_RE.finditer(line):
            links.append(
                WikiLink(
                    target=match.group("target").strip(),
                    alias=match.group("alias"),
                    is_embed=bool(match.group("embed")),
                    line=line_number,
                    column=match.start() + 1,
                )
            )
    return links


def iter_wiki_links(text: str) -> Iterator[WikiLink]:
    yield from parse_wikilinks(text)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _without_fragment(target: str) -> str:
    return _FRAGMENT_RE.sub("", target).strip()


def resolve_wiki_target(
    page: Path, target: str, paths: SecondSelfPaths
) -> Path | None:
    target = _without_fragment(target)
    if not target or "://" in target:
        return None
    target_path = Path(target.replace("\\", "/").lstrip("/"))
    candidates = [page.parent / target_path, paths.wiki / target_path]
    for candidate in candidates:
        for resolved in (candidate, candidate.with_suffix(".md")):
            if not _inside(resolved, paths.wiki):
                continue
            if resolved.is_file():
                return resolved.resolve()
    return None
