import json
import subprocess
import sys
from pathlib import Path

from main_brain.paths import BrainPaths
from main_brain.projects import LOCAL_PATHS, register_project
from main_brain.validation import validate


def test_project_registration_is_local_and_ignored(
    brain: BrainPaths, tmp_path: Path
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", str(project)], check=True, capture_output=True)
    created = register_project(brain, project, "Example", "https://example.test/repo")
    assert brain.projects / "example.md" in created
    assert (project / ".agents/skills/main-brain/SKILL.md").exists()
    assert (project / "CLAUDE.local.md").exists()
    exclude = (project / ".git/info/exclude").read_text(encoding="utf-8")
    for local_path in LOCAL_PATHS:
        assert local_path in exclude
    assert validate(brain) == []
    record = brain.projects / "example.md"
    malformed = record.read_text(encoding="utf-8").replace(
        r"C:\\", "C:\\"
    )
    record.write_text(malformed, encoding="utf-8")
    register_project(brain, project, "Example", "https://example.test/repo")
    assert validate(brain) == []
    status = subprocess.check_output(
        ["git", "-C", str(project), "status", "--short"], text=True
    )
    assert status == ""


def test_hook_blocks_protected_edit(monkeypatch, tmp_path: Path) -> None:
    script = (
        Path(__file__).parents[1] / "automation" / "hooks" / "pre_tool_use.py"
    )
    event = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Update File: 01-strategy-storage/10-current/Current Identity.md"
        },
    }
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(result.stdout)["decision"] == "block"


def test_hook_allows_unrelated_command() -> None:
    script = (
        Path(__file__).parents[1] / "automation" / "hooks" / "pre_tool_use.py"
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps({"tool_input": {"command": "git status"}}),
        text=True,
        capture_output=True,
        check=True,
    )
    assert result.stdout == ""
