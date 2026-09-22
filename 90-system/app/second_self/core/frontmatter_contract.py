"""Generated front-matter contract accessors."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


_CONTRACT_PATH = Path(__file__).resolve().parents[3] / "docs" / "frontmatter-contract.json"
_CONTRACT: dict[str, Any] | None = None


def load_contract() -> dict[str, Any]:
    global _CONTRACT
    if _CONTRACT is None:
        payload = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
        if payload.get("contract") != "second-self-frontmatter":
            raise RuntimeError("Unsupported front-matter contract")
        if payload.get("version") != 1:
            raise RuntimeError("Unsupported front-matter contract version")
        _CONTRACT = payload
    return deepcopy(_CONTRACT)


def field_definition(name: str) -> dict[str, Any]:
    return dict(load_contract()["fields"].get(name, {}))


def profile_definition(record_type: str) -> dict[str, Any]:
    contract = load_contract()
    profile = dict(contract["profiles"].get(record_type, {}))
    if record_type == "project":
        profile = {**profile, **contract["profiles"]["project"]}
    if record_type.startswith("wiki-"):
        profile = {**contract["profiles"]["wiki-derived"], **profile}
    return profile
