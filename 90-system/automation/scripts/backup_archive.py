#!/usr/bin/env python3
"""Pure archive policy helpers used by backup and restore operations."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tarfile
from pathlib import Path, PurePosixPath

MANIFEST_VERSION = 1


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_member(name: str) -> bool:
    member = PurePosixPath(name)
    return (
        not member.is_absolute()
        and not member.drive
        and not re.match(r"^[A-Za-z]:", name)
        and ".." not in member.parts
    )


def validate_archive(path: Path) -> None:
    with tarfile.open(path, "r:*") as source:
        for member in source.getmembers():
            if not _safe_member(member.name):
                raise ValueError("unsafe archive member")
            if member.issym() or member.islnk():
                raise ValueError("link member is not allowed")
            if member.isdev():
                raise ValueError("device member is not allowed")


def _inventory(root: Path) -> list[dict[str, str]]:
    return [
        {"path": path.relative_to(root).as_posix(), "sha256": _digest(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def build_manifest(root: Path, archive: str, archive_sha256: str) -> dict[str, object]:
    inventory = _inventory(root)
    inventory_digest = hashlib.sha256(
        json.dumps(inventory, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "format": MANIFEST_VERSION,
        "archive": archive,
        "archive_sha256": archive_sha256,
        "inventory": inventory,
        "inventory_sha256": inventory_digest,
    }


def verify_inventory(root: Path, manifest: dict[str, object]) -> None:
    if manifest.get("format") != MANIFEST_VERSION:
        raise ValueError("unsupported manifest schema")
    inventory = _inventory(root)
    digest = hashlib.sha256(
        json.dumps(inventory, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    if digest != manifest.get("inventory_sha256") or inventory != manifest.get("inventory"):
        raise ValueError("inventory digest mismatch")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--validate":
        try:
            validate_archive(Path(sys.argv[2]))
        except (OSError, tarfile.TarError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(1)
        raise SystemExit(0)
    raise SystemExit("usage: backup_archive.py --validate <tar>")
