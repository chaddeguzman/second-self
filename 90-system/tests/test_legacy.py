from __future__ import annotations

from pathlib import Path

import pytest

from second_self.reads.dashboard import legacy_items, scan_dashboard
from second_self.core.paths import SecondSelfPaths


def _note(path: Path, metadata: str, title: str = "Example") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\n{metadata.strip()}\n---\n\n# {title}\n",
        encoding="utf-8",
    )


def test_legacy_lists_unparseable_note(second_self: SecondSelfPaths) -> None:
    malformed = second_self.layer1 / "01 Notes/02 Notes/Malformed.md"
    malformed.write_text("---\nnot: [valid\n---\n", encoding="utf-8")
    snapshot = scan_dashboard(second_self)
    assert snapshot.legacy_excluded == 1
    legacy = legacy_items(second_self)
    assert any(item["path"] == "01 Notes/02 Notes/Malformed.md" for item in legacy)


def test_legacy_lists_oversized_note(second_self: SecondSelfPaths) -> None:
    oversized = second_self.layer1 / "01 Notes/02 Notes/Oversized.md"
    oversized.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    legacy = legacy_items(second_self)
    assert any(item["path"] == "01 Notes/02 Notes/Oversized.md" and item["reason"] == "oversized" for item in legacy)


def test_legacy_ignores_valid_note(second_self: SecondSelfPaths) -> None:
    _note(
        second_self.layer1 / "01 Notes/02 Notes/Valid.md",
        "type: note\ncreated: 2026-07-01\nstatus: active",
        "Valid",
    )
    legacy = legacy_items(second_self)
    assert not legacy


def test_legacy_cli_returns_json(second_self: SecondSelfPaths, monkeypatch: pytest.MonkeyPatch) -> None:
    malformed = second_self.layer1 / "01 Notes/02 Notes/Malformed.md"
    malformed.write_text("---\nnot: [valid\n---\n", encoding="utf-8")
    from second_self.cli import build_parser, _command_legacy
    import io
    import sys

    monkeypatch.setattr("second_self.cli.load_paths", lambda require_config=True: second_self)
    parser = build_parser()
    args = parser.parse_args(["legacy", "--json"])
    captured = io.StringIO()
    sys.stdout = captured
    try:
        _command_legacy(args)
    finally:
        sys.stdout = sys.__stdout__
    output = captured.getvalue()
    assert "Malformed.md" in output


def test_legacy_respects_scope_filter(second_self: SecondSelfPaths) -> None:
    layer1_legacy = second_self.layer1 / "01 Notes/02 Notes/LegacyNote.md"
    layer1_legacy.write_text("bad", encoding="utf-8")
    projects_legacy = second_self.projects / "LegacyProject.md"
    projects_legacy.write_text("bad", encoding="utf-8")
    legacy = legacy_items(second_self)
    layer1_paths = [item["path"] for item in legacy if item["scope"] == "layer1"]
    projects_paths = [item["path"] for item in legacy if item["scope"] == "projects"]
    assert "01 Notes/02 Notes/LegacyNote.md" in layer1_paths
    assert "LegacyProject.md" in projects_paths