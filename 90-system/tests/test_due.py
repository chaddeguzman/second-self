from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from second_self.cli import main
from second_self.due import due_items
from second_self.paths import SecondSelfPaths


def _note(path: Path, metadata: str, title: str = "Example") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\n{metadata.strip()}\n---\n\n# {title}\n",
        encoding="utf-8",
    )


def test_due_finds_items_with_due_dates(second_self: SecondSelfPaths) -> None:
    layer1 = second_self.layer1
    _note(
        layer1 / "03 Strategy/02 Decisions/Decision.md",
        "type: decision\ncreated: 2026-07-01\nstatus: active\ndue: 2026-08-10",
        "Review project X",
    )
    _note(
        layer1 / "01 Notes/02 Notes/Note.md",
        "type: note\ncreated: 2026-07-15\nstatus: active\ndue: 2026-08-05",
        "Follow up on Y",
    )
    results = due_items(second_self, today=date(2026, 8, 4))
    assert len(results) == 2
    assert results[0]["due"] == "2026-08-05"
    assert results[1]["due"] == "2026-08-10"
    assert results[0]["title"] == "Follow up on Y"
    assert results[0]["days_until_due"] == 1
    assert results[1]["days_until_due"] == 6


def test_due_overdue_only_filters_future(second_self: SecondSelfPaths) -> None:
    layer1 = second_self.layer1
    _note(
        layer1 / "03 Strategy/02 Decisions/Overdue.md",
        "type: decision\ncreated: 2026-07-01\nstatus: active\ndue: 2026-08-01",
        "Overdue item",
    )
    _note(
        layer1 / "01 Notes/02 Notes/Upcoming.md",
        "type: note\ncreated: 2026-07-15\nstatus: active\ndue: 2026-08-10",
        "Upcoming item",
    )
    results = due_items(second_self, overdue_only=True, today=date(2026, 8, 4))
    assert len(results) == 1
    assert results[0]["title"] == "Overdue item"
    assert results[0]["days_until_due"] == -3


def test_due_skips_items_without_due(second_self: SecondSelfPaths) -> None:
    layer1 = second_self.layer1
    _note(
        layer1 / "01 Notes/02 Notes/NoDue.md",
        "type: note\ncreated: 2026-07-15\nstatus: active",
        "No due date",
    )
    results = due_items(second_self, today=date(2026, 8, 4))
    assert all(r["title"] != "No due date" for r in results)


def test_due_cli_returns_json(
    second_self: SecondSelfPaths,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    layer1 = second_self.layer1
    _note(
        layer1 / "03 Strategy/02 Decisions/Decision.md",
        "type: decision\ncreated: 2026-07-01\nstatus: active\ndue: 2026-08-10",
        "Review project X",
    )
    monkeypatch.setattr("second_self.cli.load_paths", lambda require_config=True: second_self)

    result = main(["due"])

    assert result == 0
    output = capsys.readouterr().out
    assert '"results"' in output
    assert "2026-08-10" in output
    assert str(second_self.data_root) not in output