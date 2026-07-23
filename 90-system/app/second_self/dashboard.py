from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from .frontmatter import read_note
from .paths import SecondSelfPaths


MAX_SCAN_FILES = 10_000
MAX_NOTE_BYTES = 2 * 1024 * 1024
SKIPPED_LAYER1_DIRECTORIES = {"98-trash", "99-audit"}
PERSONAL_CONFIRMATION_TYPES = {
    "identity",
    "strategy",
    "note",
    "lesson",
    "reference",
    "quote",
    "book",
    "journal",
    "decision",
}
OPEN_STATUSES = {"inbox", "proposed", "active"}
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
    project_state: str = ""
    writeback_status: str = ""


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
    legacy_excluded: int
    scan_errors: int
    scanned_files: int


@dataclass
class _ScanResult:
    layer1: list[DashboardItem]
    projects: list[DashboardItem]
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


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def _item(path: Path, root: Path, scope: Literal["layer1", "projects"]) -> tuple[DashboardItem | None, bool, bool]:
    if not _inside(path, root):
        return None, False, True
    try:
        if path.stat().st_size > MAX_NOTE_BYTES:
            return None, False, True
        metadata, body = read_note(path)
    except (OSError, UnicodeError, ValueError):
        return None, False, True
    if not metadata:
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
            project_state=str(metadata.get("project_state", "")),
            writeback_status=str(metadata.get("writeback_status", "")),
        ),
        False,
        False,
    )


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
            elif (
                len(relative.parts) == 1
                and relative.parts[0].casefold() == "75-imports"
            ):
                directories[:] = [
                    name for name in directories if name.casefold() != "originals"
                ]
            for name in files:
                if not name.lower().endswith(".md"):
                    continue
                if Path(name).stem.casefold().endswith(" index"):
                    continue
                if result.scanned >= MAX_SCAN_FILES:
                    result.errors += 1
                    return
                path = current / name
                result.scanned += 1
                item, legacy, error = _item(path, root, "layer1")
                result.legacy_excluded += int(legacy)
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
        item, legacy, error = _item(path, root, "projects")
        result.legacy_excluded += int(legacy)
        result.errors += int(error)
        if item is not None:
            result.projects.append(item)


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
    result = _ScanResult([], [])
    _scan_layer1(paths, result)
    _scan_projects(paths, result)
    layer1 = result.layer1

    captures = _newest(
        [item for item in layer1 if item.record_type == "capture" and item.status == "inbox"]
    )
    imports = _newest(
        [
            item
            for item in layer1
            if item.record_type == "import"
            and item.created is not None
            and item.created >= today - timedelta(days=30)
            and item.created <= today
        ]
    )
    memories = _newest(
        [
            item
            for item in layer1
            if item.status == "proposed"
            and item.record_type in PERSONAL_CONFIRMATION_TYPES
        ]
    )
    conflicts = _newest(
        [
            item
            for item in layer1
            if item.record_type == "conflict" and item.status in OPEN_STATUSES
        ]
    )
    overdue = tuple(
        sorted(
            [
                item
                for item in layer1
                if item.due is not None
                and item.due < today
                and item.status in OPEN_STATUSES
            ],
            key=lambda item: (item.due or date.max, item.title.casefold()),
        )
    )
    writebacks = tuple(
        sorted(
            [
            item
            for item in [*layer1, *result.projects]
            if (
                item.record_type == "handoff" and item.status in {"inbox", "proposed"}
            )
            or (
                item.record_type == "project"
                and item.writeback_status.casefold() == "pending"
            )
            ],
            key=lambda item: item.title.casefold(),
        )
    )

    import_configured = (paths.layer1 / "75-imports").exists() or any(
        item.record_type == "import" for item in layer1
    )
    memory_configured = any(
        item.record_type in PERSONAL_CONFIRMATION_TYPES for item in layer1
    )
    conflict_configured = (paths.layer1 / "55-conflicts").exists() or any(
        item.record_type == "conflict" for item in layer1
    )
    writeback_configured = any(
        item.record_type in {"project", "handoff"}
        for item in [*layer1, *result.projects]
    )
    root_error = result.root_error
    scan_problem = root_error or result.errors > 0
    queues = {
        "captures": _queue(
            "captures",
            "Unprocessed captures",
            "Structured capture records with status inbox.",
            list(captures),
            True,
            "",
            scan_problem,
        ),
        "imports": _queue(
            "imports",
            "Recently imported documents",
            "Structured import records created within the previous 30 calendar days.",
            list(imports),
            import_configured,
            "No structured import folder or records exist yet.",
            scan_problem,
        ),
        "memories": _queue(
            "memories",
            "Memories awaiting confirmation",
            "Proposed personal records; imports, conflicts, projects, and handoffs are excluded.",
            list(memories),
            memory_configured,
            "No structured personal records exist yet.",
            scan_problem,
        ),
        "conflicts": _queue(
            "conflicts",
            "Detected conflicts",
            "Structured conflict records with inbox, proposed, or active status.",
            list(conflicts),
            conflict_configured,
            "No structured conflict folder or records exist yet.",
            scan_problem,
        ),
        "overdue": _queue(
            "overdue",
            "Overdue commitments",
            "Open structured records with a valid due date before today.",
            list(overdue),
            result.saw_due_field,
            "No structured due-date metadata exists yet.",
            scan_problem,
        ),
        "writebacks": _queue(
            "writebacks",
            "Project updates awaiting writeback",
            "Pending handoff records or projects explicitly marked writeback pending.",
            list(writebacks),
            writeback_configured,
            "No structured project or handoff records exist yet.",
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
    return DashboardSnapshot(
        queues=queues,
        active_projects=active_projects,
        legacy_excluded=result.legacy_excluded,
        scan_errors=result.errors + int(root_error),
        scanned_files=result.scanned,
    )
