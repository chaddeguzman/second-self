from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REQUIRED = ("type", "created", "status")
STATUSES = {"inbox", "proposed", "active", "superseded", "archived"}


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    marker = text.find("\n---\n", 4)
    if marker == -1:
        return {}, text
    raw = text[4:marker]
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ValueError("Frontmatter must be a mapping.")
    return data, text[marker + 5 :]


def read_note(path: Path) -> tuple[dict[str, Any], str]:
    return split_frontmatter(path.read_text(encoding="utf-8-sig"))


def validate_metadata(data: dict[str, Any]) -> list[str]:
    errors = [f"missing required field: {key}" for key in REQUIRED if key not in data]
    if data.get("status") not in STATUSES:
        errors.append(f"invalid status: {data.get('status')!r}")
    return errors

