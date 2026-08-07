from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, cast

from ..core.frontmatter import read_note
from ..core.paths import SecondSelfPaths
from ..wiki.wiki import wiki_status


MAX_SCAN_FILES = 10_000
MAX_NOTE_BYTES = 2 * 1024 * 1024
SKIPPED_LAYER1_DIRECTORIES = {"98-trash", "99-audit"}
QueueState = Literal["populated", "configured-empty", "unavailable", "scan-error"]


@dataclass(frozen=True)
class DashboardItem:
    scope: Literal["layer1", "projects"]
    relative_path: str
    title: str
    record_type: str
    status: str
    created: date | None
    due: date | None
    preview_eligible: bool
    tags: tuple[str, ...] = ()
    project_state: str = ""
    writeback_status: str = ""
    age_days: int | None = None
    age_label: str = ""
    size_bytes: int | None = None


@dataclass(frozen=True)
class QueueResult:
    key: str
    label: str
    rule: str
    state: QueueState
    items: tuple[DashboardItem, ...]
    unavailable_reason: str = ""


@dataclass(frozen=True)
class DashboardSnapshot:
    queues: dict[str, QueueResult]
    active_projects: tuple[DashboardItem, ...]
    tag_index: dict[str, tuple[DashboardItem, ...]]
    legacy_excluded: int
    scan_errors: int
    scanned_files: int
    wiki: dict[str, Any]
    legacy: tuple[dict[str, str], ...] = ()
    layer1: tuple[DashboardItem, ...] = ()
    projects: tuple[DashboardItem, ...] = ()


@dataclass
class _ScanResult:
    layer1: list[DashboardItem]
    projects: list[DashboardItem]
    legacy: list[dict[str, str]]
    legacy_excluded: int = 0
    errors: int = 0
    scanned: int = 0
    root_error: bool = False
    saw_due_field: bool = False


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _title(body: str, path: Path) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            value = "".join(
                character
                for character in line[2:].strip()
                if ord(character) >= 32 and ord(character) != 127
            )[:240]
            if value:
                return value
    return path.stem


def _tags(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    source = cast(list[object], value)
    normalized: list[str] = []
    for entry in source:
        if isinstance(entry, str):
            tag = entry.strip()
            if tag and tag not in normalized:
                normalized.append(tag)
    return tuple(sorted(normalized))


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def _item(path: Path, root: Path, scope: Literal["layer1", "projects"], legacy: list[dict[str, str]]) -> tuple[DashboardItem | None, bool, bool]:
    if not _inside(path, root):
        return None, False, True
    try:
        if path.stat().st_size > MAX_NOTE_BYTES:
            legacy.append({"path": path.relative_to(root).as_posix(), "scope": scope, "reason": "oversized"})
            return None, True, True
        metadata, body = read_note(path)
    except (OSError, UnicodeError, ValueError) as exc:
        legacy.append({"path": path.relative_to(root).as_posix(), "scope": scope, "reason": f"read error: {type(exc).__name__}"})
        return None, True, True
    if not metadata:
        legacy.append({"path": path.relative_to(root).as_posix(), "scope": scope, "reason": "empty metadata"})
        return None, True, False
    record_type = str(metadata.get("type", ""))
    status = str(metadata.get("status", ""))
    return (
        DashboardItem(
            scope=scope,
            relative_path=path.relative_to(root).as_posix(),
            title=_title(body, path),
            record_type=record_type,
            status=status,
            created=_parse_date(metadata.get("created")),
            due=_parse_date(metadata.get("due")),
            preview_eligible=True,
            tags=_tags(metadata.get("tags")),
            project_state=str(metadata.get("project_state", "")),
            writeback_status=str(metadata.get("writeback_status", "")),
        ),
        False,
        False,
    )


def _raw_file_items(root: Path, layer1_root: Path) -> tuple[list[DashboardItem], int]:
    """List every direct entry in 01 Capture/00 Raw (files and bundles).

    Mirrors the wiki's raw_units enumeration (top-level files plus
    top-level directories treated as bundles, dotfiles excluded) but uses
    lightweight stat/schema reads only, so the dashboard never hashes the
    full content of large sources.
    """
    if not root.is_dir():
        return [], 0
    items: list[DashboardItem] = []
    errors = 0
    try:
        entries = sorted(root.iterdir(), key=lambda value: value.name.casefold())
    except OSError:
        return [], 1
    for entry in entries:
        if entry.name.startswith("."):
            continue
        if not entry.is_file() and not entry.is_dir():
            continue
        try:
            relative = entry.relative_to(layer1_root).as_posix()
            if entry.is_dir():
                items.append(
                    DashboardItem(
                        scope="layer1",
                        relative_path=relative,
                        title=entry.name,
                        record_type="bundle",
                        status="pending",
                        created=None,
                        due=None,
                        preview_eligible=False,
                        size_bytes=None,
                    )
                )
                continue
            size = entry.stat().st_size
            metadata: dict[str, Any] | None = None
            body = ""
            preview_eligible = entry.suffix.casefold() == ".md"
            if preview_eligible and size <= MAX_NOTE_BYTES:
                try:
                    metadata, body = read_note(entry)
                except (OSError, UnicodeError, ValueError):
                    metadata, body = None, ""
                    preview_eligible = False
            items.append(
                DashboardItem(
                    scope="layer1",
                    relative_path=relative,
                    title=_title(body, entry) if body else entry.name,
                    record_type=entry.suffix.casefold().lstrip(".") or "file",
                    status=str(metadata.get("status", "pending"))
                    if metadata
                    else "pending",
                    created=_parse_date(metadata.get("created"))
                    if metadata
                    else None,
                    due=None,
                    preview_eligible=preview_eligible,
                    size_bytes=size,
                )
            )
        except OSError:
            errors += 1
    return items, errors


def _scan_layer1(paths: SecondSelfPaths, result: _ScanResult) -> None:
    root = paths.layer1
    if not root.is_dir():
        result.root_error = True
        return
    try:
        walker = os.walk(root, followlinks=False)
        for directory, directories, files in walker:
            current = Path(directory)
            relative = current.relative_to(root)
            if relative == Path("."):
                directories[:] = [
                    name
                    for name in directories
                    if name.casefold() not in SKIPPED_LAYER1_DIRECTORIES
                ]
            elif tuple(part.casefold() for part in relative.parts) == (
                "01 capture",
                "04 imports",
            ):
                directories[:] = [
                    name for name in directories if name.casefold() != "originals"
                ]
            for name in files:
                if not name.lower().endswith(".md"):
                    continue
                if Path(name).stem.casefold().endswith(" index"):
                    continue
                if relative.parts and relative.parts[0].casefold() == "00 memory":
                    continue
                if result.scanned >= MAX_SCAN_FILES:
                    result.errors += 1
                    return
                path = current / name
                result.scanned += 1
                item, is_legacy, error = _item(path, root, "layer1", result.legacy)
                result.legacy_excluded += int(is_legacy)
                result.errors += int(error)
                if item is not None:
                    result.layer1.append(item)
                    result.saw_due_field = result.saw_due_field or item.due is not None
    except OSError:
        result.root_error = True


def _scan_projects(paths: SecondSelfPaths, result: _ScanResult) -> None:
    root = paths.projects
    if not root.is_dir():
        return
    try:
        files = sorted(root.glob("*.md"), key=lambda value: value.name.lower())
    except OSError:
        result.errors += 1
        return
    for path in files:
        if path.name.casefold() == "projects index.md":
            continue
        if result.scanned >= MAX_SCAN_FILES:
            result.errors += 1
            return
        result.scanned += 1
        item, is_legacy, error = _item(path, root, "projects", result.legacy)
        result.legacy_excluded += int(is_legacy)
        result.errors += int(error)
        if item is not None:
            result.projects.append(item)


def _humanize_age(days: int) -> str:
    if days <= 0:
        return "today"
    if days == 1:
        return "1d"
    if days < 7:
        return f"{days}d"
    if days < 30:
        return f"{round(days / 7)}w"
    if days < 365:
        return f"{round(days / 30)}mo"
    return f"{round(days / 365)}y"


def _newest(items: list[DashboardItem]) -> tuple[DashboardItem, ...]:
    return tuple(
        sorted(
            items,
            key=lambda item: (item.created or date.min, item.title.casefold()),
            reverse=True,
        )
    )


def _queue(
    key: str,
    label: str,
    rule: str,
    items: list[DashboardItem],
    configured: bool,
    unavailable_reason: str,
    scan_error: bool = False,
) -> QueueResult:
    state: QueueState
    if items:
        state = "populated"
    elif scan_error:
        state = "scan-error"
    elif not configured:
        state = "unavailable"
    else:
        state = "configured-empty"
    return QueueResult(
        key,
        label,
        rule,
        state,
        tuple(items),
        unavailable_reason if state == "unavailable" else "",
    )


def scan_dashboard(paths: SecondSelfPaths, today: date | None = None) -> DashboardSnapshot:
    today = today or date.today()
    result = _ScanResult([], [], [])
    _scan_layer1(paths, result)
    _scan_projects(paths, result)
    layer1 = result.layer1
    raw_items, raw_scan_errors = _raw_file_items(paths.raw, paths.layer1)
    raw_items = tuple(
        dataclasses.replace(
            item,
            age_days=(today - item.created).days
            if item.created is not None
            else None,
            age_label=_humanize_age((today - item.created).days)
            if item.created is not None
            else "",
        )
        for item in _newest(raw_items)
    )

    root_error = result.root_error
    scan_problem = root_error or result.errors > 0 or raw_scan_errors > 0
    queues = {
        "captures": _queue(
            "captures",
            "Unprocessed captures",
            "Every file and bundle waiting in 01 Capture/00 Raw.",
            list(raw_items),
            paths.raw.is_dir(),
            "The 01 Capture/00 Raw inbox does not exist yet.",
            scan_problem,
        ),
    }
    active_projects = tuple(
        sorted(
            [
                item
                for item in result.projects
                if item.record_type == "project"
                and item.project_state.casefold() == "active"
            ],
            key=lambda item: item.title.casefold(),
        )
    )
    tag_entries: dict[str, list[DashboardItem]] = {}
    for item in [*layer1, *result.projects]:
        for tag in item.tags:
            tag_entries.setdefault(tag, []).append(item)
    tag_index = {
        tag: tuple(
            sorted(items, key=lambda value: value.title.casefold())
        )
        for tag, items in sorted(
            tag_entries.items(), key=lambda pair: pair[0].casefold()
        )
    }
    return DashboardSnapshot(
        queues=queues,
        active_projects=active_projects,
        tag_index=tag_index,
        legacy_excluded=result.legacy_excluded,
        legacy=tuple(result.legacy),
        scan_errors=result.errors + int(root_error) + raw_scan_errors,
        scanned_files=result.scanned,
        wiki=wiki_status(paths),
        layer1=tuple(layer1),
        projects=tuple(result.projects),
    )


def legacy_items(paths: SecondSelfPaths, today: date | None = None) -> tuple[dict[str, str], ...]:
    snapshot = scan_dashboard(paths, today)
    return tuple(snapshot.legacy)