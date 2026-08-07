from __future__ import annotations

import pytest

from second_self.cli import main
from second_self.core.paths import SecondSelfPaths


def test_tags_command_lists_tags_with_counts(
    second_self: SecondSelfPaths,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    note = second_self.layer1 / "01 Capture/02 Notes" / "Tagged.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(
        "---\n"
        "type: note\n"
        "created: 2026-07-23\n"
        "status: active\n"
        "tags: [health, work]\n"
        "---\n\n"
        "# Tagged\n",
        encoding="utf-8",
    )
    second = second_self.layer1 / "01 Capture/02 Notes" / "Second.md"
    second.write_text(
        "---\n"
        "type: note\n"
        "created: 2026-07-23\n"
        "status: active\n"
        "tags: [health]\n"
        "---\n\n"
        "# Second\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "second_self.cli.load_paths", lambda require_config=True: second_self
    )

    result = main(["tags"])

    assert result == 0
    output = capsys.readouterr().out
    assert '"tag": "health"' in output
    assert '"tag": "work"' in output
    assert '"count": 2' in output
    assert '"count": 1' in output


def test_tags_command_reports_empty_index(
    second_self: SecondSelfPaths,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "second_self.cli.load_paths", lambda require_config=True: second_self
    )

    result = main(["tags"])

    assert result == 0
    output = capsys.readouterr().out
    assert '"tags": []' in output
