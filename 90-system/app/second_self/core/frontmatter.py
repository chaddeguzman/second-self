from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from datetime import date, datetime

from .frontmatter_contract import load_contract, profile_definition

_CONTRACT = load_contract()
REQUIRED = tuple(_CONTRACT["core_required"])
STATUSES = set(_CONTRACT["fields"]["status"]["enum"])
TYPES = set(_CONTRACT["fields"]["type"]["enum"])


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    marker = text.find("\n---\n", 4)
    if marker == -1:
        return {}, text
    raw = text[4:marker]
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML frontmatter: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Frontmatter must be a mapping.")
    return data, text[marker + 5 :]


def read_note(path: Path) -> tuple[dict[str, Any], str]:
    return split_frontmatter(path.read_text(encoding="utf-8-sig"))


def validate_metadata(data: dict[str, Any]) -> list[str]:
    errors = [f"missing required field: {key}" for key in REQUIRED if key not in data]
    record_type = data.get("type")
    if record_type not in TYPES:
        errors.append(f"invalid type: {record_type!r}")
    if data.get("status") not in STATUSES:
        errors.append(f"invalid status: {data.get('status')!r}")
    for name, definition in _CONTRACT["fields"].items():
        if name not in data:
            continue
        value = data[name]
        kind = definition["kind"]
        if kind == "string" and not isinstance(value, str):
            errors.append(f"{name} must be a string")
        elif kind == "date":
            if not isinstance(value, date):
                try:
                    date.fromisoformat(value)
                except (TypeError, ValueError):
                    errors.append(f"{name} must be an ISO date")
        elif kind == "datetime":
            if not isinstance(value, datetime):
                try:
                    datetime.fromisoformat(value)
                except (TypeError, ValueError):
                    errors.append(f"{name} must be an ISO datetime")
        elif kind == "list":
            if not isinstance(value, list):
                errors.append(f"{name} must be a list")
            elif not all(isinstance(item, str) for item in value):
                errors.append(f"{name} must contain only strings")
            elif definition.get("unique") and len(value) != len(set(value)):
                errors.append(f"{name} must contain unique values")
        elif kind == "string-or-list" and not (
            isinstance(value, str)
            or (isinstance(value, list) and all(isinstance(item, str) for item in value))
        ):
            errors.append(f"{name} must be a string or list of strings")
        if "enum" in definition and value not in definition["enum"]:
            if name == "verification":
                errors.append("verification must be derived")
            else:
                errors.append(f"invalid {name}: {value!r}")
    profile = profile_definition(str(record_type)) if record_type in TYPES else {}
    errors.extend(
        f"missing required field: {key}"
        for key in profile.get("required", [])
        if key not in data
    )
    for name, expected in profile.items():
        if name in {"required", "type"} or name not in data:
            continue
        if data[name] != expected and name != "verification":
            errors.append(f"{name} must be {expected!r}")
    return errors
