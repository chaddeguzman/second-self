"""Gmail connector — PLACEHOLDER STUB ONLY.

FUTURE PROJECT — NOT part of the echo-google-calendar scope. Every
method raises NotImplementedError. No Gmail code exists or will exist
in this project (PLAN.md hard rule 5; PRD non-goals).

This stub exists so the future Gmail project inherits a stable import
surface and a documented interface shape — nothing more.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class GmailConnector:
    """Future read-only Gmail interface. ALL methods are stubs.

    Expected scope when actually built (separate project, separate
    phased plan): OAuth with gmail.readonly, digest-style fetching,
    and the same privacy staging-gate rules that govern all ECHO
    integrations. None of that is implemented here.
    """

    def authenticate(self, base_dir: Path) -> None:
        """Future: run OAuth flow for gmail.readonly. Not implemented."""
        raise NotImplementedError("Gmail connector is a future project (stub)")

    def fetch_recent(self, base_dir: Path, max_results: int = 20) -> list[dict[str, Any]]:
        """Future: fetch recent message headers. Not implemented."""
        raise NotImplementedError("Gmail connector is a future project (stub)")

    def search(self, base_dir: Path, query: str) -> list[dict[str, Any]]:
        """Future: search messages by query. Not implemented."""
        raise NotImplementedError("Gmail connector is a future project (stub)")