"""Generate front-matter schemas and runtime accessors from one contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "90-system" / "docs" / "frontmatter-contract.json"
SCHEMA_DIR = ROOT / "90-system" / "docs" / "schemas"
RUNTIME_MODULE = ROOT / "90-system" / "app" / "second_self" / "core" / "frontmatter_contract.py"


def _load_contract() -> dict[str, Any]:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if payload.get("contract") != "second-self-frontmatter":
        raise ValueError("unsupported front-matter contract")
    if not isinstance(payload.get("version"), int):
        raise ValueError("front-matter contract version must be an integer")
    return payload


def _json_property(definition: dict[str, Any]) -> dict[str, Any]:
    kind = definition["kind"]
    if kind == "string":
        result: dict[str, Any] = {"type": "string"}
        if "enum" in definition:
            result["enum"] = definition["enum"]
        return result
    if kind == "date":
        return {"type": "string", "format": "date"}
    if kind == "datetime":
        return {"type": "string", "format": "date-time"}
    if kind == "list":
        result = {"type": "array", "items": {"type": definition["items"]}}
        if definition.get("unique"):
            result["uniqueItems"] = True
        return result
    if kind == "string-or-list":
        return {"type": ["string", "array"], "items": {"type": "string"}}
    raise ValueError(f"unsupported front-matter field kind: {kind}")


def _schema(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    fields = payload["fields"]
    core_fields = {
        name: _json_property(definition)
        for name, definition in fields.items()
        if name in {
            "type", "created", "status", "updated", "tags", "projects", "related", "source"
        }
    }
    note = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://github.com/chaddeguzman/second-self/note.schema.json",
        "title": "Second Self Note",
        "type": "object",
        "required": payload["core_required"],
        "properties": core_fields,
        "additionalProperties": True,
    }
    project = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://github.com/chaddeguzman/second-self/project.schema.json",
        "title": "Second Self Project",
        "allOf": [{"$ref": "note.schema.json"}],
        "type": "object",
        "required": payload["core_required"] + payload["profiles"]["project"]["required"],
        "properties": {
            "type": {"const": "project"},
            "project_state": _json_property(fields["project_state"]),
            "repository": _json_property(fields["repository"]),
            "local_path": _json_property(fields["local_path"]),
        },
    }
    return note, project


def _runtime_module() -> str:
    return '''"""Generated front-matter contract accessors."""\n\nfrom __future__ import annotations\n\nimport json\nfrom copy import deepcopy\nfrom pathlib import Path\nfrom typing import Any\n\n\n_CONTRACT_PATH = Path(__file__).resolve().parents[3] / "docs" / "frontmatter-contract.json"\n_CONTRACT: dict[str, Any] | None = None\n\n\ndef load_contract() -> dict[str, Any]:\n    global _CONTRACT\n    if _CONTRACT is None:\n        payload = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))\n        if payload.get("contract") != "second-self-frontmatter":\n            raise RuntimeError("Unsupported front-matter contract")\n        if payload.get("version") != 1:\n            raise RuntimeError("Unsupported front-matter contract version")\n        _CONTRACT = payload\n    return deepcopy(_CONTRACT)\n\n\ndef field_definition(name: str) -> dict[str, Any]:\n    return dict(load_contract()["fields"].get(name, {}))\n\n\ndef profile_definition(record_type: str) -> dict[str, Any]:\n    contract = load_contract()\n    profile = dict(contract["profiles"].get(record_type, {}))\n    if record_type == "project":\n        profile = {**profile, **contract["profiles"]["project"]}\n    if record_type.startswith("wiki-"):\n        profile = {**contract["profiles"]["wiki-derived"], **profile}\n    return profile\n'''


def _render(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.check == args.write:
        parser.error("choose exactly one of --check or --write")
    payload = _load_contract()
    note, project = _schema(payload)
    outputs = {
        SCHEMA_DIR / "note.schema.json": _render(note),
        SCHEMA_DIR / "project.schema.json": _render(project),
        RUNTIME_MODULE: _runtime_module(),
    }
    drift = [path for path, content in outputs.items() if not path.exists() or path.read_text(encoding="utf-8") != content]
    if args.check:
        if drift:
            for path in drift:
                print(f"front-matter contract drift: {path.relative_to(ROOT).as_posix()}")
            return 1
        return 0
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
