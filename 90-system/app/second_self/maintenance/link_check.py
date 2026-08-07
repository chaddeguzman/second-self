"""Wikilink integrity checker for Layer 1 Markdown notes.

Verifies that every ``[[wikilink]]`` inside private Layer 1 notes resolves to
an existing target note.  Unlike the wiki lint (which only checks
``03-wiki``), this module covers the entire ``01-strategy-storage`` tree.

Resolution rules mirror Obsidian behaviour:

* ``[[01 Capture/00 Raw/Idea]]`` — absolute (data-root-relative) path.
* ``[[Sibling Note]]`` — resolve relative to the linking note's directory,
  then fall back to a global stem match across Layer 1.
* ``[[page#heading]]`` and ``[[page^block]]`` — the heading/block fragment
  is stripped before resolution.
* ``[[page|alias]]`` — the alias is stripped; only ``page`` is resolved.
* ``![[embed]]`` — embeds are checked as links because they reference files.

Wikilinks inside fenced code blocks and inline ``code`` spans are skipped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.paths import SecondSelfPaths

# A wikilink target is everything between [[ and ]].
# Group 1 = target (before any | alias), with optional #heading or ^block suffix.
# Group 2 = optional alias.
_WIKILINK_RE = re.compile(r"\[\[([^\]\|]+)(?:\|([^\]]*))?\]\]")

# Strips a trailing #heading or ^blockid from a target.
_FRAGMENT_RE = re.compile(r"(?:#|\^).*$")

# Fenced code block delimiter (``` or ~~~).
_CODE_FENCE_RE = re.compile(r"(```+|~~~+)")

# Inline code span.
_INLINE_CODE_RE = re.compile(r"(`)")


@dataclass
class BrokenLink:
    source: str
    line: int
    column: int
    target: str
    message: str


@dataclass
class LinkCheckResult:
    total_links: int = 0
    broken: list[BrokenLink] = field(default_factory=list)
    scanned_files: int = 0

    @property
    def valid(self) -> bool:
        return not self.broken


def _strip_fragments(target: str) -> str:
    return _FRAGMENT_RE.sub("", target).strip()


def _strip_code_spans(text: str) -> str:
    """Remove fenced code blocks and inline code spans before scanning."""
    result: list[str] = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        fence = _CODE_FENCE_RE.search(line)
        if fence:
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # Remove inline code spans from this line.
        cleaned = re.sub(r"`[^`]*`", "", line)
        result.append(cleaned)
    return "".join(result)


def _iter_layer1_notes(paths: SecondSelfPaths) -> list[Path]:
    if not paths.layer1.exists():
        return []
    notes: list[Path] = []
    for item in paths.layer1.rglob("*.md"):
        # Skip trash and audit directories.
        parts = item.relative_to(paths.layer1).parts
        if parts and parts[0].casefold() in {"98-trash", "99-audit"}:
            continue
        notes.append(item)
    return sorted(notes, key=lambda p: p.as_posix())


def _resolve_target(note_path: Path, target: str, paths: SecondSelfPaths) -> Path | None:
    target = _strip_fragments(target)
    if not target:
        return None

    data_root = paths.data_root

    # Absolute path — try layer1-relative first (e.g. "00 Memory/Profile"),
    # then fall back to data-root-relative.
    if "/" in target:
        cleaned = target.replace("\\", "/").strip("/")
        for base in (paths.layer1, data_root):
            candidate = (base / cleaned).with_suffix(".md")
            if candidate.is_file():
                return candidate
            candidate_raw = base / cleaned
            if candidate_raw.is_file():
                return candidate_raw
        return None

    # Bare name: try relative resolution first, then global stem match.
    # Relative: same directory as the note.
    candidate = (note_path.parent / target).with_suffix(".md")
    if candidate.is_file():
        return candidate
    candidate_raw = note_path.parent / target
    if candidate_raw.is_file():
        return candidate_raw

    # Global stem match across all Layer 1 notes.
    for other in _iter_layer1_notes(paths):
        if other.stem.casefold() == target.casefold():
            return other

    return None


def check_wikilinks(paths: SecondSelfPaths, max_files: int = 5_000) -> LinkCheckResult:
    result = LinkCheckResult()
    notes = _iter_layer1_notes(paths)
    for note in notes[:max_files]:
        result.scanned_files += 1
        try:
            text = note.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            continue
        cleaned = _strip_code_spans(text)
        for lineno, line in enumerate(cleaned.splitlines(), start=1):
            for match in _WIKILINK_RE.finditer(line):
                # Skip embed links (prefixed with !).
                start = match.start()
                if start > 0 and cleaned[start - 1] == "!":
                    continue
                target = match.group(1)
                resolved = _resolve_target(note, target, paths)
                if resolved is None:
                    result.total_links += 1
                    result.broken.append(
                        BrokenLink(
                            source=note.relative_to(paths.data_root).as_posix(),
                            line=lineno,
                            column=match.start() + 1,
                            target=target,
                            message=f"wikilink target '{target}' does not resolve to an existing note",
                        )
                    )
                else:
                    result.total_links += 1
    return result


def format_errors(errors: list[str]) -> str:
    return "\n".join(errors)


def as_error_strings(result: LinkCheckResult) -> list[str]:
    """Convert a LinkCheckResult into error strings for validate()."""
    return [
        f"{item.source}:{item.line}: broken wikilink [[{item.target}]]"
        for item in result.broken
    ]


def build_link_fix_proposal(
    paths: SecondSelfPaths,
    corrections: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a ``link_fix`` broker proposal for broken wikilinks.

    If *corrections* is given, it maps ``source_path>wikilink_target`` to the
    replacement wikilink text.  Otherwise the module attempts automatic
    resolution using case-insensitive stem substring matching and
    :func:`difflib.get_close_matches`.
    """
    import difflib

    result = check_wikilinks(paths)
    all_notes = _iter_layer1_notes(paths)
    stems = [note.stem for note in all_notes]

    fixes: list[dict[str, Any]] = []
    for broken in result.broken:
        key = f"{broken.source}>{broken.target}"
        if corrections and key in corrections:
            new_target = corrections[key]
        else:
            cleaned = _strip_fragments(broken.target)
            matches = difflib.get_close_matches(
                cleaned.casefold(), [s.casefold() for s in stems], n=1, cutoff=0.6
            )
            if not matches:
                continue
            best_stem = stems[[s.casefold() for s in stems].index(matches[0])]
            best_note = next(n for n in all_notes if n.stem == best_stem)
            new_target = best_note.relative_to(paths.layer1).as_posix()

        old_link = f"[[{broken.target}]]"
        new_link = f"[[{new_target}]]"
        # Merge replacements for the same file.
        existing = next(
            (fix for fix in fixes if fix["path"] == broken.source), None
        )
        if existing:
            existing["replacements"].append({"old": old_link, "new": new_link})
        else:
            fixes.append(
                {
                    "path": broken.source,
                    "replacements": [{"old": old_link, "new": new_link}],
                }
            )
    return {"operation": "link_fix", "fixes": fixes}
