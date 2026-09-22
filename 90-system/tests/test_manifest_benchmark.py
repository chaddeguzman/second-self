from __future__ import annotations

from pathlib import Path

import second_self.reads.manifest as manifest_module
from second_self.core.paths import SecondSelfPaths
from second_self.reads.manifest import build_manifest


def test_second_manifest_pass_reuses_unchanged_file_content(tmp_path: Path, monkeypatch):
    paths = SecondSelfPaths(tmp_path / "repo", tmp_path / "data")
    note = paths.layer1 / "04 References" / "note.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        "---\ntype: note\ncreated: 2026-09-22\nupdated: 2026-09-22\n"
        "tags: []\n---\n# Note\nBody\n",
        encoding="utf-8",
    )
    calls = 0
    original = manifest_module._digest

    def counted(path: Path) -> str:
        nonlocal calls
        calls += 1
        return original(path)

    monkeypatch.setattr(manifest_module, "_digest", counted)
    first = build_manifest(paths)
    second = build_manifest(paths, previous=first)

    assert calls == 1
    assert second.by_relative_path("01-strategy-storage/04 References/note.md") is first.by_relative_path(
        "01-strategy-storage/04 References/note.md"
    )
