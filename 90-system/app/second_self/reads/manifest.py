"""Bounded, read-only document snapshots shared by Second Self readers."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.frontmatter import read_note
from ..core.paths import SecondSelfPaths

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_SCAN_FILES = 10_000
SKIPPED_DIRECTORIES = {"98-trash", "99-audit", ".second-self-cache"}
TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".json", ".yaml", ".yml"}


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    relative_path: str
    size_bytes: int
    mtime_ns: int
    digest: str
    metadata: dict[str, Any] | None = None
    body: str | None = None
    text: str | None = None
    readable: bool = True
    error: str = ""


@dataclass(frozen=True, slots=True)
class DocumentManifest:
    root_key: str
    entries: tuple[ManifestEntry, ...]
    scanned_files: int
    errors: int = 0

    def by_relative_path(self, relative_path: str) -> ManifestEntry | None:
        for entry in self.entries:
            if entry.relative_path == relative_path:
                return entry
        return None


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _roots(paths: SecondSelfPaths) -> tuple[Path, ...]:
    return tuple(root for root in (paths.layer1, paths.projects, paths.wiki) if root.is_dir())


def _relative(path: Path, data_root: Path) -> str:
    parts = Path(path).parts
    root_name = data_root.name.casefold()
    root_indexes = [index for index, part in enumerate(parts) if part.casefold() == root_name]
    if not root_indexes:
        raise ValueError("manifest path escaped data root")
    return Path(*parts[root_indexes[-1] + 1 :]).as_posix()


def _read_content(
    path: Path,
) -> tuple[dict[str, Any] | None, str | None, str | None, bool, str]:
    if path.suffix.casefold() not in TEXT_SUFFIXES:
        return None, None, None, False, "not-readable"
    if path.stat().st_size > MAX_FILE_BYTES:
        return None, None, None, False, "oversized"
    try:
        text = path.read_text(encoding="utf-8-sig")
        metadata = None
        body = text
        if path.suffix.casefold() in {".md", ".markdown"}:
            metadata, body = read_note(path)
        return metadata, body, text, True, ""
    except (OSError, UnicodeError, ValueError):
        return None, None, None, False, "read-error"


def build_manifest(
    paths: SecondSelfPaths, *, previous: DocumentManifest | None = None
) -> DocumentManifest:
    """Build a stable snapshot, reusing entries whose stat identity is unchanged."""
    data_root = paths.data_root.resolve()
    root_key = data_root.as_posix()
    previous_entries = (
        {entry.relative_path: entry for entry in previous.entries}
        if previous is not None and previous.root_key == root_key
        else {}
    )
    entries: list[ManifestEntry] = []
    errors = 0
    scanned = 0
    for root in _roots(paths):
        try:
            walker = os.walk(root, followlinks=False)
            for directory, directories, files in walker:
                current = Path(directory)
                directories[:] = [
                    name for name in directories if name.casefold() not in SKIPPED_DIRECTORIES
                ]
                for name in sorted(files, key=str.casefold):
                    if scanned >= MAX_SCAN_FILES:
                        errors += 1
                        break
                    path = current / name
                    try:
                        stat = path.stat()
                    except OSError:
                        errors += 1
                        continue
                    scanned += 1
                    relative = _relative(path, data_root)
                    prior = previous_entries.get(relative)
                    if prior and prior.size_bytes == stat.st_size and prior.mtime_ns == stat.st_mtime_ns:
                        entries.append(prior)
                        continue
                    try:
                        digest = _digest(path)
                        metadata, body, text, readable, error = _read_content(path)
                    except OSError:
                        digest = ""
                        metadata, body, text, readable, error = None, None, None, False, "read-error"
                    errors += int(error in {"read-error", "oversized"})
                    entries.append(
                        ManifestEntry(
                            relative_path=relative,
                            size_bytes=stat.st_size,
                            mtime_ns=stat.st_mtime_ns,
                            digest=digest,
                            metadata=metadata,
                            body=body,
                            text=text,
                            readable=readable,
                            error=error,
                        )
                    )
                if scanned >= MAX_SCAN_FILES:
                    break
        except OSError:
            errors += 1
    entries.sort(key=lambda item: item.relative_path.casefold())
    return DocumentManifest(root_key, tuple(entries), scanned, errors)
