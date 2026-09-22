"""Dependency-profile and workflow pinning policy tests."""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
PROFILES = ROOT / "requirements/profiles.json"
VERIFIER = ROOT / "90-system/automation/scripts/verify-dependency-lock.py"


def test_profiles_keep_optional_integrations_out_of_core():
    profiles = json.loads(PROFILES.read_text(encoding="utf-8"))
    assert set(profiles) == {"core", "semantic", "calendar", "dev"}
    assert "fastembed" not in profiles["core"]
    assert "google-api-python-client" not in profiles["core"]
    assert "fastembed" in profiles["semantic"]
    assert "google-api-python-client" in profiles["calendar"]
    assert "calendar =" in PYPROJECT


def test_lock_verifier_rejects_a_tampered_lock_copy(tmp_path):
    copied = tmp_path / "requirements.lock"
    copied.write_text(
        (ROOT / "requirements.lock").read_text(encoding="utf-8") + "\n# tampered\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(VERIFIER), "--lock", str(copied)], capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "digest mismatch" in result.stderr


def test_workflow_actions_are_immutable_sha_pins_with_version_comments():
    matches = re.findall(r"uses: ([\w/-]+)@([^\s#]+)(?:\s+#\s*(v\d+[^\r\n]*))?", WORKFLOW)
    assert matches
    for _name, reference, comment in matches:
        assert re.fullmatch(r"[0-9a-f]{40}", reference)
        assert comment
