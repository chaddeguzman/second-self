from __future__ import annotations

from pathlib import Path

import pytest

from second_self.cli import main
from second_self.core.paths import SecondSelfPaths


def _note(path: Path, metadata: str, title: str = "Example") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\n{metadata.strip()}\n---\n\n# {title}\n",
        encoding="utf-8",
    )


def test_stats_command_reports_counts_and_wiki(
    second_self: SecondSelfPaths,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    layer1 = second_self.layer1
    _note(
        layer1 / "01 Notes/00 Raw/Capture One.md",
        "type: capture\ncreated: 2026-07-10\nstatus: inbox",
        "Capture one",
    )
    _note(
        layer1 / "01 Notes/00 Raw/Capture Two.md",
        "type: capture\ncreated: 2026-07-20\nstatus: inbox",
        "Capture two",
    )
    _note(
        layer1 / "01 Notes/02 Notes/Note.md",
        "type: note\ncreated: 2026-07-15\nstatus: active",
        "Note",
    )
    _note(
        second_self.projects / "Project.md",
        "type: project\ncreated: 2026-07-01\nstatus: active\nproject_state: active",
        "Project",
    )
    monkeypatch.setattr(
        "second_self.cli.load_paths", lambda require_config=True: second_self
    )

    result = main(["stats"])

    assert result == 0
    output = capsys.readouterr().out
    assert '"counts_by_type"' in output
    assert '"capture": 2' in output
    assert '"note": 1' in output
    assert '"project": 1' in output
    assert '"counts_by_status"' in output
    assert '"inbox": 2' in output
    assert '"active": 3' in output
    assert '"captures_per_month"' in output
    assert '"2026-07": 2' in output
    assert '"project_counts"' in output
    assert '"total": 1' in output
    assert '"active": 1' in output
    assert '"raw_files": 2' in output
    assert '"wiki"' in output


def test_stats_command_reports_empty_vault(
    second_self: SecondSelfPaths,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "second_self.cli.load_paths", lambda require_config=True: second_self
    )

    result = main(["stats"])

    assert result == 0
    output = capsys.readouterr().out
    assert '"counts_by_type"' in output
    assert '"reference": 1' in output
    assert '"identity": 1' in output
    assert '"strategy": 1' in output
    assert '"counts_by_status"' in output
    assert '"proposed": 2' in output
    assert '"active": 1' in output
    assert '"captures_per_month": {}' in output
    assert '"total": 0' in output
    assert '"active": 0' in output
    assert '"raw_files": 0' in output
