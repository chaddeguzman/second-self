from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from second_self.cli import main
from second_self.paths import SecondSelfPaths
from second_self.recent import recent_items


def _note(path: Path, metadata: str, title: str = "Example") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\n{metadata.strip()}\n---\n\n# {title}\n",
        encoding="utf-8",
    )


def test_recent_finds_items_within_window(second_self: SecondSelfPaths) -> None:
    layer1 = second_self.layer1
    _note(
        layer1 / "01 Notes/02 Notes/Recent.md",
        "type: note\ncreated: 2026-08-02\nstatus: active",
        "Recent note",
    )
    _note(
        layer1 / "01 Notes/02 Notes/Older.md",
        "type: note\ncreated: 2026-07-30\nstatus: active",
        "Older note",
    )
    results = recent_items(second_self, days=7, today=date(2026, 8, 4))
    titles = [r["title"] for r in results]
    assert "Recent note" in titles
    assert "Older note" in titles
    recent = next(r for r in results if r["title"] == "Recent note")
    older = next(r for r in results if r["title"] == "Older note")
    assert recent["created"] == "2026-08-02"
    assert recent["age_days"] == 2
    assert older["age_days"] == 5
    assert results.index(recent) < results.index(older)


def test_recent_excludes_items_outside_window(second_self: SecondSelfPaths) -> None:
    layer1 = second_self.layer1
    _note(
        layer1 / "01 Notes/02 Notes/Recent.md",
        "type: note\ncreated: 2026-08-02\nstatus: active",
        "Recent note",
    )
    _note(
        layer1 / "01 Notes/02 Notes/Old.md",
        "type: note\ncreated: 2026-07-01\nstatus: active",
        "Old note",
    )
    results = recent_items(second_self, days=7, today=date(2026, 8, 4))
    titles = [r["title"] for r in results]
    assert "Recent note" in titles
    assert "Old note" not in titles


def test_recent_custom_days_window(second_self: SecondSelfPaths) -> None:
    layer1 = second_self.layer1
    _note(
        layer1 / "01 Notes/02 Notes/TenDaysOld.md",
        "type: note\ncreated: 2026-07-25\nstatus: active",
        "Ten days old",
    )
    short = recent_items(second_self, days=7, today=date(2026, 8, 4))
    long = recent_items(second_self, days=14, today=date(2026, 8, 4))
    assert all(r["title"] != "Ten days old" for r in short)
    assert any(r["title"] == "Ten days old" for r in long)


def test_recent_cli_returns_json(
    second_self: SecondSelfPaths,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    layer1 = second_self.layer1
    _note(
        layer1 / "01 Notes/02 Notes/Recent.md",
        "type: note\ncreated: 2026-08-02\nstatus: active",
        "Recent note",
    )
    monkeypatch.setattr("second_self.cli.load_paths", lambda require_config=True: second_self)

    result = main(["recent", "--days", "7"])

    assert result == 0
    output = capsys.readouterr().out
    assert '"results"' in output
    assert "2026-08-02" in output
    assert str(second_self.data_root) not in output