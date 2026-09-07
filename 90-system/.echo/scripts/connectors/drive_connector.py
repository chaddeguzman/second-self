"""Drive connector — PLACEHOLDER STUB ONLY.

FUTURE PROJECT — NOT part of the echo-google-calendar scope. Every
method raises NotImplementedError. No Drive code exists or will exist
in this project (PLAN.md hard rule 5; PRD non-goals). Drive was ruled
out in the 2026-09-07 brainstorm: it overlaps what the Second Self
vault already does; revisit only if a concrete need appears.

This stub exists so a future project inherits a stable import surface
and a documented interface shape — nothing more.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class DriveConnector:
    """Future read-only Drive interface. ALL methods are stubs.

    Expected scope when actually built (if ever): OAuth with
    drive.readonly, file-listing only (no sync engine). None of that
    is implemented here.
    """

    def authenticate(self, base_dir: Path) -> None:
        """Future: run OAuth flow for drive.readonly. Not implemented."""
        raise NotImplementedError("Drive connector is a future project (stub)")

    def list_files(self, base_dir: Path, folder_id: str | None = None) -> list[dict[str, Any]]:
        """Future: list file metadata. Not implemented."""
        raise NotImplementedError("Drive connector is a future project (stub)")

    def search(self, base_dir: Path, query: str) -> list[dict[str, Any]]:
        """Future: search files by name/metadata. Not implemented."""
        raise NotImplementedError("Drive connector is a future project (stub)")