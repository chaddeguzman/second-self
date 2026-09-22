from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from second_self.core.frontmatter import split_frontmatter, validate_metadata


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "90-system" / "docs" / "frontmatter-contract.json"


def test_core_note_metadata_is_valid_and_missing_fields_are_specific() -> None:
    valid = {"type": "note", "created": "2026-09-22", "status": "active"}

    assert validate_metadata(valid) == []
    assert validate_metadata({"type": "note", "status": "active"}) == [
        "missing required field: created"
    ]


def test_project_metadata_requires_project_profile_fields() -> None:
    metadata = {
        "type": "project",
        "created": "2026-09-22",
        "status": "active",
    }

    errors = validate_metadata(metadata)

    assert "missing required field: project_state" in errors
    assert "missing required field: repository" in errors


def test_contract_source_declares_versioned_type_and_status_sets() -> None:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert payload["contract"] == "second-self-frontmatter"
    assert payload["version"] == 1
    assert payload["fields"]["status"]["enum"] == [
        "inbox",
        "proposed",
        "active",
        "superseded",
        "archived",
    ]
    assert "project" in payload["fields"]["type"]["enum"]
    assert payload["profiles"]["project"]["required"] == [
        "project_state",
        "repository",
    ]


def test_contract_generator_check_has_no_drift() -> None:
    generator = REPO_ROOT / "90-system" / "automation" / "scripts" / "generate-frontmatter-contract.py"

    result = subprocess.run(
        [sys.executable, str(generator), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def test_runtime_validation_enforces_contract_types_and_derived_profiles() -> None:
    assert "invalid type: 'unknown'" in validate_metadata(
        {"type": "unknown", "created": "2026-09-22", "status": "active"}
    )
    assert "tags must be a list" in validate_metadata(
        {"type": "note", "created": "2026-09-22", "status": "active", "tags": "wrong"}
    )
    assert "verification must be derived" in validate_metadata(
        {
            "type": "wiki-source",
            "created": "2026-09-22",
            "status": "active",
            "verification": "confirmed",
        }
    )
    assert "created must be an ISO date" in validate_metadata(
        {"type": "note", "created": "not-a-date", "status": "active"}
    )


def test_all_public_templates_satisfy_runtime_contract() -> None:
    template_dir = REPO_ROOT / "90-system" / "docs" / "templates"

    for template in sorted(template_dir.glob("*.md")):
        content = template.read_text(encoding="utf-8").replace(
            "{{date}}", "2026-09-22"
        ).replace("{{title}}", "Contract fixture")
        metadata, _ = split_frontmatter(content)
        assert validate_metadata(metadata) == [], template.name
