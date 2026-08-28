"""Dashboard helpers for the Process Raw button.

Lists eligible Raw sources, recommends an 04 References subfolder with
simple keyword rules, and builds a full ``wiki_process`` broker
specification (source page per file, one batch log entry, index rows,
and Raw -> References moves).
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.paths import SecondSelfPaths
from .wiki import (
    REFERENCES_SUBFOLDERS,
    raw_units,
    references_destination,
    source_id,
    source_hash,
)

MAX_SOURCES = 10
_TEXT_SUFFIXES = {".md", ".txt"}

_RECOMMENDATION_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("quote", "one-liner", "oneliner", "saying", "aphorism"), "02 quotes"),
    (("how to", "guide", "step-by-step", "tutorial", "walkthrough"), "04 guides"),
    (("book", "chapter", "meditations", "reading list"), "01 books"),
    (("research", "study", "paper", "analysis", "essay", "on "), "03 research"),
    (("doc", "script", "notes for", "manual", "reference"), "05 docs"),
)


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")
    return slug or "source"


def recommend_subfolder(path: Path) -> str:
    """Return a best-guess 04 References subfolder for *path*.

    Simple keyword rules over the filename (then, for text sources, the
    first 2 KB of content). Anything unmatched defaults to the
    Uncategorized subfolder.
    """
    haystacks = [path.name.casefold()]
    if path.is_file() and path.suffix.casefold() in _TEXT_SUFFIXES:
        try:
            haystacks.append(path.read_text(encoding="utf-8", errors="ignore")[:2048].casefold())
        except OSError:
            pass
    for keywords, subfolder in _RECOMMENDATION_RULES:
        for haystack in haystacks:
            if any(keyword in haystack for keyword in keywords):
                return subfolder
    return "06 Uncategorized"


def eligible_raw_sources(paths: SecondSelfPaths) -> list[dict[str, Any]]:
    """Return dashboard-ready entries for eligible .md/.txt Raw files."""
    entries: list[dict[str, Any]] = []
    for unit in raw_units(paths):
        if not unit.path.is_file():
            continue
        if unit.path.suffix.casefold() not in _TEXT_SUFFIXES:
            continue
        digest = source_hash(unit.path)
        entries.append(
            {
                "relative_path": unit.path.relative_to(paths.data_root).as_posix(),
                "name": unit.path.name,
                "source_id": source_id(digest),
                "sha256": digest,
                "recommendation": recommend_subfolder(unit.path),
            }
        )
        if len(entries) >= MAX_SOURCES:
            break
    return entries


def _source_page(
    entry: dict[str, Any],
    destination_relative: str,
    now: datetime,
) -> str:
    iso_now = now.isoformat(timespec="seconds")
    today = now.date().isoformat()
    title = Path(entry["name"]).stem
    return (
        "---\n"
        "type: wiki-source\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        "status: active\n"
        "verification: derived\n"
        f"source_id: {entry['source_id']}\n"
        f"source_path: {destination_relative}\n"
        f"source_sha256: {entry['sha256']}\n"
        "source_kind: md\n"
        f"processed_at: {iso_now}\n"
        'duplicate_of: ""\n'
        'supersedes: ""\n'
        "tags: []\n"
        "projects: []\n"
        "related: []\n"
        "---\n"
        f"# {title}\n"
        "\n"
        "## Summary\n"
        "\n"
        f"Archived Raw source moved to `04 References` via the dashboard "
        "Process Raw workflow. Content has not yet been deeply synthesized; "
        "this page records provenance and location.\n"
        "\n"
        "## Key Evidence\n"
        "\n"
        "- Not yet synthesized. See the archived source for the full text.\n"
        "\n"
        "## Connections\n"
        "\n"
        "- No derived connections recorded yet.\n"
        "\n"
        "## Uncertainties\n"
        "\n"
        "Agent-generated provenance page; deep synthesis is pending.\n"
        "\n"
        "## Source\n"
        "\n"
        f"- Archived source: `{destination_relative}`\n"
    )


def _update_index(index_content: str, rows: list[str]) -> str:
    marker = "<!-- END GENERATED -->"
    additions = "\n".join(rows) + "\n\n"
    if marker in index_content:
        return index_content.replace(marker, additions + marker)
    return index_content + "\n" + additions


def _update_log(log_content: str, entry_row: str) -> str:
    lines = log_content.splitlines()
    for position, line in enumerate(lines):
        if line.startswith("|") and "--" in line:
            return "\n".join(
                lines[:position] + [entry_row] + lines[position:]
            ) + "\n"
    return log_content + "\n" + entry_row + "\n"


def build_wiki_process_spec(
    paths: SecondSelfPaths,
    assignments: dict[str, str],
) -> dict[str, Any]:
    """Build a wiki_process specification from filename -> subfolder choices.

    *assignments* maps the Raw file's data-root-relative path to a valid
    ``04 References`` subfolder name. Returns the full broker
    specification with schema-compliant source pages, one batch log
    entry, index rows, and move entries.
    """
    if not assignments:
        raise ValueError("No sources were selected for processing.")
    if len(assignments) > MAX_SOURCES:
        raise ValueError(f"At most {MAX_SOURCES} sources can be processed at once.")

    now = datetime.now().astimezone()
    today = now.date().isoformat()
    wiki_dir = paths.wiki

    changes: list[dict[str, str]] = []
    moves: list[dict[str, str]] = []
    index_rows: list[str] = []
    log_details: list[str] = []

    for relative_path, subfolder in sorted(assignments.items()):
        if subfolder not in REFERENCES_SUBFOLDERS:
            raise ValueError(f"Invalid References subfolder: {subfolder!r}")
        source = paths.data_root / relative_path
        if not source.is_file() or not _inside(source, paths.raw):
            raise ValueError(f"Source is not an eligible Raw file: {relative_path}")
        digest = source_hash(source)
        entry = {
            "name": source.name,
            "source_id": source_id(digest),
            "sha256": digest,
        }
        destination = references_destination(paths, source, subfolder)
        destination_relative = destination.relative_to(paths.data_root).as_posix()

        page_relative = (
            f"sources/{entry['source_id']}-{_slug(Path(source.name).stem)}.md"
        )
        changes.append(
            {"path": f"03-wiki/{page_relative}", "content": _source_page(entry, destination_relative, now)}
        )
        moves.append(
            {
                "from": source.relative_to(paths.data_root).as_posix(),
                "to": destination_relative,
                "source_id": entry["source_id"],
            }
        )
        index_rows.append(
            f"| Source | [{Path(source.name).stem}]({page_relative.replace(' ', '%20')}) "
            f"| Dashboard-processed source moved to 04 References/{subfolder}. | — |"
        )
        log_details.append(
            f"[{Path(source.name).stem}]({page_relative.replace(' ', '%20')}) "
            f"moved to 04 References/{subfolder}."
        )

    index_path = wiki_dir / "index.md"
    if index_path.exists():
        changes.append(
            {"path": "03-wiki/index.md", "content": _update_index(index_path.read_text(encoding="utf-8"), index_rows)}
        )

    log_title = (
        f"Dashboard Process Raw: {len(assignments)} source"
        + ("s" if len(assignments) != 1 else "")
    )
    if (wiki_dir / "log.md").exists():
        log_row = (
            f"| {today} | ingest | {log_title} | " + "<br>".join(log_details) + " |"
        )
        changes.append(
            {"path": "03-wiki/log.md", "content": _update_log((wiki_dir / "log.md").read_text(encoding="utf-8"), log_row)}
        )

    return {
        "operation": "wiki_process",
        "changes": changes,
        "moves": moves,
    }


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def raw_content_fingerprint(paths: SecondSelfPaths) -> str:
    """Stable fingerprint of eligible Raw files, for staleness detection."""
    digest = hashlib.sha256()
    for entry in eligible_raw_sources(paths):
        digest.update(entry["relative_path"].encode("utf-8"))
        digest.update(entry["sha256"].encode("ascii"))
    return digest.hexdigest()