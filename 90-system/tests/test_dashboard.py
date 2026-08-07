from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from second_self.reads.dashboard import scan_dashboard
from second_self.core.paths import SecondSelfPaths


def _note(path: Path, metadata: str, title: str = "Example") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\n{metadata.strip()}\n---\n\n# {title}\n",
        encoding="utf-8",
    )


def test_dashboard_has_only_the_captures_queue(second_self: SecondSelfPaths) -> None:
    snapshot = scan_dashboard(second_self)
    assert set(snapshot.queues) == {"captures"}


def test_dashboard_lists_every_raw_file_and_bundle(second_self: SecondSelfPaths) -> None:
    layer1 = second_self.layer1
    _note(
        layer1 / "01 Capture/00 Raw/Capture.md",
        "type: capture\ncreated: 2026-07-22\nstatus: inbox",
        "Captured thought",
    )
    (layer1 / "01 Capture/00 Raw/Plain.txt").write_text("plain", encoding="utf-8")
    bundle = layer1 / "01 Capture/00 Raw/Article"
    bundle.mkdir()
    (bundle / "article.md").write_text("# Article\n", encoding="utf-8")

    snapshot = scan_dashboard(second_self, today=date(2026, 7, 23))

    items = snapshot.queues["captures"].items
    by_title = {item.title: item for item in items}
    assert set(by_title) == {"Captured thought", "Plain.txt", "Article"}
    assert by_title["Captured thought"].record_type == "md"
    assert by_title["Captured thought"].status == "inbox"
    assert by_title["Captured thought"].preview_eligible is True
    assert by_title["Plain.txt"].record_type == "txt"
    assert by_title["Plain.txt"].status == "pending"
    assert by_title["Plain.txt"].preview_eligible is False
    assert by_title["Plain.txt"].size_bytes == 5
    assert by_title["Article"].record_type == "bundle"
    assert by_title["Article"].preview_eligible is False


def test_raw_dotfiles_are_excluded(second_self: SecondSelfPaths) -> None:
    (second_self.raw / ".gitkeep").write_text("keep", encoding="utf-8")
    snapshot = scan_dashboard(second_self)
    assert not snapshot.queues["captures"].items
    assert snapshot.queues["captures"].state == "configured-empty"


def test_raw_markdown_uses_frontmatter_metadata(second_self: SecondSelfPaths) -> None:
    _note(
        second_self.layer1 / "01 Capture/00 Raw/Inbox Capture.md",
        "type: capture\ncreated: 2026-07-22\nstatus: inbox",
        "Inbox capture",
    )
    snapshot = scan_dashboard(second_self, today=date(2026, 7, 23))
    item = snapshot.queues["captures"].items[0]
    assert item.title == "Inbox capture"
    assert item.created == date(2026, 7, 22)
    assert item.age_days == 1
    assert item.age_label == "1d"


def test_raw_markdown_without_frontmatter_is_still_listed(second_self: SecondSelfPaths) -> None:
    note = second_self.raw / "No Frontmatter.md"
    note.write_text("# Just a heading\n", encoding="utf-8")
    snapshot = scan_dashboard(second_self)
    item = snapshot.queues["captures"].items[0]
    assert item.title == "Just a heading"
    assert item.status == "pending"
    assert item.preview_eligible is True


def test_legacy_vault_is_not_silently_classified(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    notes = data / "01-strategy-storage/01 Capture/02 Notes"
    notes.mkdir(parents=True)
    (notes / "Who I Am.md").write_text("# Who I Am\n\nLegacy prose.", encoding="utf-8")
    snapshot = scan_dashboard(SecondSelfPaths(repo, data), today=date(2026, 7, 23))
    assert snapshot.legacy_excluded == 1
    assert snapshot.queues["captures"].state == "unavailable"
    assert not snapshot.queues["captures"].items


def test_tag_index_normalizes_and_aggregates(second_self: SecondSelfPaths) -> None:
    _note(
        second_self.layer1 / "01 Capture/02 Notes/Alpha.md",
        "type: note\ncreated: 2026-07-01\nstatus: active\ntags: [health, work, health]",
        "Alpha",
    )
    _note(
        second_self.layer1 / "01 Capture/02 Notes/Beta.md",
        "type: note\ncreated: 2026-07-02\nstatus: active\ntags: [health]",
        "Beta",
    )
    _note(
        second_self.layer1 / "01 Capture/02 Notes/Gamma.md",
        "type: note\ncreated: 2026-07-03\nstatus: active",
        "Gamma",
    )
    _note(
        second_self.projects / "Project.md",
        "type: project\ncreated: 2026-07-01\nstatus: active\ntags: [work]",
        "Tagged project",
    )
    snapshot = scan_dashboard(second_self)
    assert set(snapshot.tag_index) == {"health", "work"}
    assert {item.title for item in snapshot.tag_index["health"]} == {"Alpha", "Beta"}
    assert {item.title for item in snapshot.tag_index["work"]} == {"Alpha", "Tagged project"}


def test_tag_index_ignores_non_list_and_untagged(second_self: SecondSelfPaths) -> None:
    _note(
        second_self.layer1 / "01 Capture/02 Notes/Weird.md",
        "type: note\ncreated: 2026-07-01\nstatus: active\ntags: not-a-list",
        "Weird tags",
    )
    snapshot = scan_dashboard(second_self)
    assert snapshot.tag_index == {}


def test_projects_scan_only_direct_records(second_self: SecondSelfPaths) -> None:
    _note(
        second_self.projects / "active.md",
        "type: project\ncreated: 2026-07-01\nstatus: active\nproject_state: active",
        "Active project",
    )
    _note(
        second_self.projects / "Nested Repo/README.md",
        "type: project\ncreated: 2026-07-01\nstatus: active\nproject_state: active",
        "Nested project file",
    )
    snapshot = scan_dashboard(second_self)
    assert [item.title for item in snapshot.active_projects] == ["Active project"]


def test_malformed_and_oversized_notes_do_not_break_home(
    second_self: SecondSelfPaths,
) -> None:
    malformed = second_self.layer1 / "01 Capture/02 Notes/Malformed.md"
    malformed.parent.mkdir(parents=True, exist_ok=True)
    malformed.write_text("---\nnot: [valid\n---\n", encoding="utf-8")
    oversized = second_self.layer1 / "01 Capture/02 Notes/Oversized.md"
    oversized.parent.mkdir(parents=True, exist_ok=True)
    oversized.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    snapshot = scan_dashboard(second_self)
    assert snapshot.scan_errors >= 2
    assert snapshot.queues["captures"].state == "scan-error"


def test_scan_bound_stops_safely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import second_self.reads.dashboard as dashboard_module

    paths = SecondSelfPaths(tmp_path / "repo", tmp_path / "data")
    for index in range(3):
        _note(
            paths.layer1 / f"01 Capture/02 Notes/{index}.md",
            f"type: note\ncreated: 2026-07-0{index + 1}\nstatus: active",
            f"Note {index}",
        )
    monkeypatch.setattr(dashboard_module, "MAX_SCAN_FILES", 2)

    snapshot = scan_dashboard(paths)

    assert snapshot.scanned_files == 2
    assert snapshot.scan_errors == 1
