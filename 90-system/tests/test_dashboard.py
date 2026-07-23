from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from second_self.dashboard import scan_dashboard
from second_self.paths import SecondSelfPaths


def _note(path: Path, metadata: str, title: str = "Example") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\n{metadata.strip()}\n---\n\n# {title}\n",
        encoding="utf-8",
    )


def test_dashboard_queue_rules(second_self: SecondSelfPaths) -> None:
    layer1 = second_self.layer1
    _note(
        layer1 / "00-inbox/Capture.md",
        "type: capture\ncreated: 2026-07-22\nstatus: inbox",
        "Captured thought",
    )
    _note(
        layer1 / "75-imports/extracted/Recent.md",
        "type: import\ncreated: 2026-06-24\nstatus: proposed",
        "Recent import",
    )
    _note(
        layer1 / "20-notes/Memory.md",
        "type: note\ncreated: 2026-07-21\nstatus: proposed",
        "Proposed memory",
    )
    _note(
        layer1 / "55-conflicts/Conflict.md",
        "type: conflict\ncreated: 2026-07-20\nstatus: active",
        "Open conflict",
    )
    _note(
        layer1 / "60-decisions/Commitment.md",
        "type: decision\ncreated: 2026-06-01\ndue: 2026-07-01\nstatus: active",
        "Overdue commitment",
    )
    _note(
        layer1 / "00-inbox/Handoff.md",
        "type: handoff\ncreated: 2026-07-23\nstatus: inbox",
        "Pending writeback",
    )
    snapshot = scan_dashboard(second_self, today=date(2026, 7, 23))
    assert [item.title for item in snapshot.queues["captures"].items] == ["Captured thought"]
    assert [item.title for item in snapshot.queues["imports"].items] == ["Recent import"]
    assert "Proposed memory" in {
        item.title for item in snapshot.queues["memories"].items
    }
    assert [item.title for item in snapshot.queues["conflicts"].items] == ["Open conflict"]
    assert [item.title for item in snapshot.queues["overdue"].items] == ["Overdue commitment"]
    assert [item.title for item in snapshot.queues["writebacks"].items] == ["Pending writeback"]


def test_recent_import_cutoff_is_inclusive(second_self: SecondSelfPaths) -> None:
    _note(
        second_self.layer1 / "75-imports/extracted/Boundary.md",
        "type: import\ncreated: 2026-06-23\nstatus: proposed",
        "Boundary",
    )
    _note(
        second_self.layer1 / "75-imports/extracted/Too Old.md",
        "type: import\ncreated: 2026-06-22\nstatus: proposed",
        "Too old",
    )
    _note(
        second_self.layer1 / "75-imports/extracted/Future.md",
        "type: import\ncreated: 2026-07-24\nstatus: proposed",
        "Future",
    )
    items = scan_dashboard(second_self, today=date(2026, 7, 23)).queues["imports"].items
    assert [item.title for item in items] == ["Boundary"]


def test_legacy_vault_is_not_silently_classified(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    memory = data / "01-strategy-storage/00 Memory"
    memory.mkdir(parents=True)
    (memory / "Who I Am.md").write_text("# Who I Am\n\nLegacy prose.", encoding="utf-8")
    snapshot = scan_dashboard(SecondSelfPaths(repo, data), today=date(2026, 7, 23))
    assert snapshot.legacy_excluded == 1
    assert snapshot.queues["captures"].state == "configured-empty"
    assert snapshot.queues["imports"].state == "unavailable"
    assert snapshot.queues["memories"].state == "unavailable"
    assert all(not queue.items for queue in snapshot.queues.values())


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


def test_imported_originals_are_not_operational_records(
    second_self: SecondSelfPaths,
) -> None:
    _note(
        second_self.layer1 / "75-imports/originals/Original.md",
        "type: import\ncreated: 2026-07-23\nstatus: proposed",
        "Original must stay excluded",
    )

    snapshot = scan_dashboard(second_self, today=date(2026, 7, 23))

    assert not snapshot.queues["imports"].items


def test_malformed_and_oversized_notes_do_not_break_home(
    second_self: SecondSelfPaths
) -> None:
    malformed = second_self.layer1 / "20-notes/Malformed.md"
    malformed.write_text("---\nnot: [valid\n---\n", encoding="utf-8")
    oversized = second_self.layer1 / "20-notes/Oversized.md"
    oversized.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    snapshot = scan_dashboard(second_self)
    assert snapshot.scan_errors >= 2
    assert snapshot.queues["captures"].state == "scan-error"


def test_scan_bound_stops_safely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import second_self.dashboard as dashboard_module

    paths = SecondSelfPaths(tmp_path / "repo", tmp_path / "data")
    for index in range(3):
        _note(
            paths.layer1 / f"20-notes/{index}.md",
            f"type: note\ncreated: 2026-07-0{index + 1}\nstatus: active",
            f"Note {index}",
        )
    monkeypatch.setattr(dashboard_module, "MAX_SCAN_FILES", 2)

    snapshot = scan_dashboard(paths)

    assert snapshot.scanned_files == 2
    assert snapshot.scan_errors == 1


def test_file_symlink_cannot_escape_layer1(tmp_path: Path) -> None:
    paths = SecondSelfPaths(tmp_path / "repo", tmp_path / "data")
    paths.layer1.mkdir(parents=True)
    outside = tmp_path / "outside.md"
    outside.write_text(
        "---\ntype: capture\ncreated: 2026-07-23\nstatus: inbox\n---\n# Outside",
        encoding="utf-8",
    )
    linked = paths.layer1 / "linked.md"
    try:
        linked.symlink_to(outside)
    except OSError:
        pytest.skip("File symlinks are unavailable on this Windows configuration.")

    snapshot = scan_dashboard(paths)

    assert not snapshot.queues["captures"].items
    assert snapshot.scan_errors == 1
