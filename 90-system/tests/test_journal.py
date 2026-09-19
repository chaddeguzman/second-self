from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pytest

from second_self.cli import main
from second_self.core.frontmatter import read_note
from second_self.writes.journal import journal_entry
from second_self.core.paths import SecondSelfPaths


def test_journal_creates_new_daily_note(second_self: SecondSelfPaths) -> None:
    entry = journal_entry(
        second_self,
        "First journal body.",
        now=datetime(2026, 8, 4, 9, 30, tzinfo=timezone.utc),
    )
    assert entry.appended is False
    assert entry.path.name == "2026-08-04 - Journal.md"
    assert entry.path.parent == second_self.layer1 / "02 Journal"
    metadata, content = read_note(entry.path)
    assert metadata["type"] == "journal"
    assert metadata["status"] == "active"
    assert "## Notes" in content
    assert "First journal body." in content
    assert "## Decisions" in content
    assert "## Lessons" in content


def test_journal_appends_to_existing_note(second_self: SecondSelfPaths) -> None:
    now = datetime(2026, 8, 4, 9, 30, tzinfo=timezone.utc)
    first = journal_entry(second_self, "First body.", now=now)
    second = journal_entry(second_self, "Second body.", now=now)
    assert second.appended is True
    assert second.path == first.path
    _, content = read_note(second.path)
    assert "First body." in content
    assert "Second body." in content
    assert content.count("## Notes") == 1
    assert content.count("## Decisions") == 1
    assert content.count("## Lessons") == 1


def test_failed_verification_preserves_existing_journal(
    second_self: SecondSelfPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    import second_self.writes.journal as journal_module

    now = datetime(2026, 8, 4, 9, 30, tzinfo=timezone.utc)
    journal_entry(second_self, "Original body.", now=now)
    target = second_self.layer1 / "02 Journal" / "2026-08-04 - Journal.md"
    original = target.read_text(encoding="utf-8")
    monkeypatch.setattr(
        journal_module,
        "validate_metadata",
        lambda metadata: ["simulated verification failure"],
    )

    with pytest.raises(RuntimeError, match="verification failed"):
        journal_entry(second_self, "Replacement body.", now=now)

    assert target.read_text(encoding="utf-8") == original


def test_concurrent_journal_appends_are_serialized(
    second_self: SecondSelfPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    import second_self.writes.journal as journal_module

    now = datetime(2026, 8, 4, 9, 30, tzinfo=timezone.utc)
    journal_entry(second_self, "Initial body.", now=now)
    original_append = journal_module._append_under_notes

    def delayed_append(text: str, body: str, title: str) -> str:
        import time

        time.sleep(0.01)
        return original_append(text, body, title)

    monkeypatch.setattr(journal_module, "_append_under_notes", delayed_append)

    def append(index: int) -> Path:
        return journal_entry(second_self, f"Body {index}.", now=now).path

    with ThreadPoolExecutor(max_workers=8) as pool:
        paths = list(pool.map(append, range(12)))

    assert len(set(paths)) == 1
    content = paths[0].read_text(encoding="utf-8")
    assert all(f"Body {index}." in content for index in range(12))


def test_journal_title_becomes_heading(second_self: SecondSelfPaths) -> None:
    entry = journal_entry(
        second_self,
        "Body text.",
        title="Morning reflection",
        now=datetime(2026, 8, 4, 9, 30, tzinfo=timezone.utc),
    )
    _, content = read_note(entry.path)
    assert "### Morning reflection" in content
    assert "Body text." in content


def test_journal_rejects_empty_body(second_self: SecondSelfPaths) -> None:
    with pytest.raises(ValueError, match="Body is required"):
        journal_entry(second_self, "   ")


def test_journal_rejects_multiline_title(second_self: SecondSelfPaths) -> None:
    with pytest.raises(ValueError, match="single line"):
        journal_entry(second_self, "Body", title="Bad\nTitle")


def test_journal_cli_prints_relative_path(
    second_self: SecondSelfPaths,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("second_self.cli.load_paths", lambda require_config=True: second_self)

    result = main(["journal", "--body", "CLI journal body"])

    output = capsys.readouterr().out.strip()
    assert result == 0
    assert output.startswith("01-strategy-storage")
    assert str(second_self.data_root) not in output
    note = second_self.data_root / output
    assert read_note(note)[0]["type"] == "journal"
