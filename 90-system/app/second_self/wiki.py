from __future__ import annotations

import hashlib
import os
import re
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .frontmatter import read_note, split_frontmatter, validate_metadata
from .paths import SecondSelfPaths, resolve_private_path
from .scaffold import scaffold_wiki


SUPPORTED = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".txt",
    ".md",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}
REQUIRED_WIKI_FILES = ("index.md", "log.md", "open-questions.md")
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)")
LOG_HEADING = re.compile(r"^## \[\d{4}-\d{2}-\d{2}\] (?:ingest|query|lint|refresh|duplicate) \| .+$")


@dataclass(frozen=True)
class SourceUnit:
    path: Path
    source_id: str
    kind: str
    supported: bool


def source_hash(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_dir():
        for child in sorted(
            (item for item in path.rglob("*") if item.is_file()),
            key=lambda item: item.as_posix().casefold(),
        ):
            relative = child.relative_to(path).as_posix()
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            with child.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            digest.update(b"\0")
        return digest.hexdigest()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _supported(path: Path) -> bool:
    if path.is_file():
        return path.suffix.casefold() in SUPPORTED
    files = [item for item in path.rglob("*") if item.is_file()]
    return bool(files) and all(item.suffix.casefold() in SUPPORTED for item in files)


def raw_units(paths: SecondSelfPaths) -> list[SourceUnit]:
    if not paths.raw.exists():
        return []
    units: list[SourceUnit] = []
    for item in sorted(paths.raw.iterdir(), key=lambda value: value.name.casefold()):
        if item.name.startswith("."):
            continue
        if not item.is_file() and not item.is_dir():
            continue
        digest = source_hash(item)
        units.append(
            SourceUnit(
                item,
                digest,
                "bundle" if item.is_dir() else item.suffix.casefold().lstrip("."),
                _supported(item),
            )
        )
    return units


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _collision_safe(destination: Path) -> Path:
    if not destination.exists():
        return destination
    counter = 2
    while True:
        candidate = destination.with_name(f"{destination.stem}-{counter}{destination.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def add_source(paths: SecondSelfPaths, source: Path) -> dict[str, Any]:
    source = source.expanduser().resolve()
    if not source.exists() or not (source.is_file() or source.is_dir()):
        raise FileNotFoundError(source)
    paths.raw.mkdir(parents=True, exist_ok=True)
    if _inside(source, paths.raw):
        unit = source
        copied = False
    else:
        unit = _collision_safe(paths.raw / source.name)
        if source.is_dir():
            shutil.copytree(source, unit)
        else:
            shutil.copy2(source, unit)
        copied = True
    digest = source_hash(unit)
    duplicates = digest in _source_records(paths)
    return {
        "source_id": digest,
        "path": unit.relative_to(paths.data_root).as_posix(),
        "kind": "bundle" if unit.is_dir() else unit.suffix.casefold().lstrip("."),
        "supported": _supported(unit),
        "copied": copied,
        "duplicate": duplicates,
    }


def _source_records(paths: SecondSelfPaths) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    source_dir = paths.wiki / "sources"
    if not source_dir.exists():
        return records
    for page in source_dir.glob("*.md"):
        try:
            metadata, _ = read_note(page)
        except (OSError, UnicodeError, ValueError):
            continue
        source_id = str(metadata.get("source_id", ""))
        if source_id:
            records[source_id] = metadata
    return records


def wiki_status(paths: SecondSelfPaths) -> dict[str, Any]:
    records = _source_records(paths)
    records_by_path = {
        str(metadata.get("source_path", "")): metadata
        for metadata in records.values()
        if metadata.get("source_path")
    }
    pending = []
    unsupported = []
    duplicates = []
    for unit in raw_units(paths):
        value = {
            "path": unit.path.relative_to(paths.data_root).as_posix(),
            "source_id": unit.source_id,
            "kind": unit.kind,
        }
        if not unit.supported:
            unsupported.append(value)
        elif unit.source_id in records:
            duplicates.append(value)
        else:
            pending.append(value)
    interrupted = []
    if paths.wiki_transactions.exists():
        for journal in paths.wiki_transactions.glob("*/journal.json"):
            try:
                import json

                payload = json.loads(journal.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValueError):
                continue
            if payload.get("status") in {"staging", "applying"}:
                interrupted.append(str(payload.get("id", journal.parent.name)))
    unprocessed_curated = []
    changed_curated = []
    curated_roots = [
        paths.layer1 / name
        for name in ("00 Memory", "01 Notes", "02 Journal", "03 Strategy", "04 References", "05 Reviews")
    ]
    candidates: list[Path] = []
    for root in curated_roots:
        if root.exists():
            candidates.extend(
                item
                for item in root.rglob("*")
                if item.is_file() and item.suffix.casefold() in SUPPORTED
            )
    if paths.projects.exists():
        candidates.extend(paths.projects.glob("*.md"))
    for path in sorted(set(candidates), key=lambda item: item.as_posix().casefold())[:10_000]:
        if _inside(path, paths.raw) or _inside(path, paths.processed):
            continue
        relative = path.relative_to(paths.data_root).as_posix()
        digest = source_hash(path)
        record = records_by_path.get(relative)
        value = {
            "path": relative,
            "source_id": digest,
            "kind": path.suffix.casefold().lstrip("."),
        }
        if record and record.get("source_sha256") != digest:
            changed_curated.append(value)
        elif not record and digest not in records:
            unprocessed_curated.append(value)
    return {
        "enabled": all((paths.wiki / name).exists() for name in REQUIRED_WIKI_FILES),
        "pending": pending,
        "unsupported": unsupported,
        "duplicates": duplicates,
        "processed_sources": len(records),
        "unprocessed_curated": unprocessed_curated,
        "changed_curated": changed_curated,
        "interrupted_transactions": interrupted,
    }


def initialize_wiki(paths: SecondSelfPaths) -> dict[str, Any]:
    before = {
        path.resolve()
        for root in (paths.raw, paths.processed, paths.wiki)
        if root.exists()
        for path in [root, *root.rglob("*")]
    }
    scaffold_wiki(paths)
    created = []
    for root in (paths.raw, paths.processed, paths.wiki):
        for path in [root, *root.rglob("*")]:
            if path.resolve() not in before:
                created.append(path.relative_to(paths.data_root).as_posix())
    schema = paths.data_root / ".second-self-schema"
    schema.write_text("2\n", encoding="ascii")
    return {"schema_version": 2, "created": sorted(created)}


def _change_map(
    paths: SecondSelfPaths, changes: list[dict[str, Any]]
) -> dict[Path, str]:
    result: dict[Path, str] = {}
    for item in changes:
        target = resolve_private_path(paths, item["path"])
        result[target.resolve()] = str(item["content"])
    return result


def validate_wiki_change_set(
    paths: SecondSelfPaths, changes: list[dict[str, Any]]
) -> None:
    mapped = _change_map(paths, changes)
    errors: list[str] = []
    for target, content in mapped.items():
        try:
            target.relative_to(paths.wiki.resolve())
        except ValueError:
            errors.append(f"change outside 03-wiki: {target.name}")
            continue
        metadata, body = split_frontmatter(content)
        errors.extend(f"{target.name}: {error}" for error in validate_metadata(metadata))
        if metadata.get("verification") != "derived":
            errors.append(f"{target.name}: verification must be derived")
        if target.parent.name == "sources":
            for field in ("source_id", "source_path", "source_sha256"):
                if not metadata.get(field):
                    errors.append(f"{target.name}: missing {field}")
        for raw_link in LINK.findall(body):
            decoded = raw_link.replace("%20", " ")
            linked = (target.parent / decoded).resolve()
            if _inside(linked, paths.wiki) and linked not in mapped and not linked.exists():
                errors.append(f"{target.name}: broken wiki link {raw_link}")
    if errors:
        raise ValueError("Invalid wiki change set: " + "; ".join(errors))


def lint_wiki(paths: SecondSelfPaths) -> list[str]:
    errors: list[str] = []
    if not paths.wiki.exists():
        return ["03-wiki is not initialized"]
    pages = sorted(
        page for page in paths.wiki.rglob("*.md") if page.name.casefold() != "readme.md"
    )
    for name in REQUIRED_WIKI_FILES:
        if not (paths.wiki / name).exists():
            errors.append(f"missing wiki file: {name}")
    incoming: dict[Path, int] = {page.resolve(): 0 for page in pages}
    for page in pages:
        try:
            metadata, body = read_note(page)
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{page.relative_to(paths.wiki).as_posix()}: {exc}")
            continue
        for error in validate_metadata(metadata):
            errors.append(f"{page.relative_to(paths.wiki).as_posix()}: {error}")
        if metadata.get("verification") != "derived":
            errors.append(
                f"{page.relative_to(paths.wiki).as_posix()}: verification must be derived"
            )
        for raw_link in LINK.findall(body):
            decoded = raw_link.replace("%20", " ")
            target = (page.parent / decoded).resolve()
            if not target.exists():
                errors.append(
                    f"{page.relative_to(paths.wiki).as_posix()}: broken link {raw_link}"
                )
            if target in incoming:
                incoming[target] += 1
        if page.name == "log.md":
            for line in body.splitlines():
                if line.startswith("## ") and not LOG_HEADING.match(line):
                    errors.append(f"log.md: malformed entry heading: {line}")
    special = {str((paths.wiki / name).resolve()) for name in REQUIRED_WIKI_FILES}
    for page, count in incoming.items():
        if count == 0 and str(page) not in special:
            errors.append(f"orphan page: {page.relative_to(paths.wiki).as_posix()}")
    return errors


def archive_destination(
    paths: SecondSelfPaths,
    source: Path,
    source_id: str,
    processed_on: date | None = None,
) -> Path:
    processed_on = processed_on or date.today()
    destination = (
        paths.processed
        / f"{processed_on:%Y}"
        / processed_on.isoformat()
        / f"{source_id[:12]}-{source.name}"
    )
    if not destination.exists():
        return destination
    counter = 2
    while True:
        candidate = destination.with_name(f"{destination.name}-duplicate-{counter}")
        if not candidate.exists():
            return candidate
        counter += 1


def processing_move(
    paths: SecondSelfPaths, source: Path, processed_on: date | None = None
) -> dict[str, str]:
    source = source.resolve()
    if not _inside(source, paths.raw):
        raise ValueError("Processing source must be inside 00 Raw")
    digest = source_hash(source)
    destination = archive_destination(paths, source, digest, processed_on)
    return {
        "from": source.relative_to(paths.data_root).as_posix(),
        "to": destination.relative_to(paths.data_root).as_posix(),
        "source_id": digest,
    }
