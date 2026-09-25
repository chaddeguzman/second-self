from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from second_self.core.paths import SecondSelfPaths
from second_self.reads.manifest import DocumentManifest, build_manifest


def _paths(tmp_path: Path) -> SecondSelfPaths:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    layer1 = data / "01-strategy-storage"
    projects = data / "02-skills-projects" / "projects"
    raw = layer1 / "01 Capture" / "00 Raw"
    wiki = data / "03-wiki"
    layer1.mkdir(parents=True)
    projects.mkdir(parents=True)
    raw.mkdir(parents=True)
    wiki.mkdir(parents=True)
    return SecondSelfPaths(repo_root=repo, data_root=data)


def _note(title: str, created: str = "2026-09-22") -> str:
    return f"---\ntype: note\ncreated: {created}\nupdated: {created}\ntags: [test]\n---\n# {title}\nBody\n"


def test_manifest_reuses_unchanged_note_and_detects_same_size_replacement(tmp_path: Path):
    paths = _paths(tmp_path)
    note = paths.layer1 / "04 References" / "note.md"
    note.parent.mkdir()
    note.write_text(_note("Alpha"), encoding="utf-8")

    first = build_manifest(paths)
    second = build_manifest(paths, previous=first)
    first_entry = first.by_relative_path("01-strategy-storage/04 References/note.md")
    second_entry = second.by_relative_path("01-strategy-storage/04 References/note.md")

    assert first_entry is not None
    assert second_entry is first_entry
    assert second_entry.metadata is not None
    assert second_entry.metadata["created"] == date(2026, 9, 22)

    note.write_text(_note("Bravo"), encoding="utf-8")
    stat = note.stat()
    os.utime(note, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    third = build_manifest(paths, previous=second)
    third_entry = third.by_relative_path("01-strategy-storage/04 References/note.md")
    assert third_entry is not None
    assert third_entry is not second_entry
    assert third_entry.body is not None and "Bravo" in third_entry.body


def test_manifest_removes_deleted_files_and_skips_excluded_directories(tmp_path: Path):
    paths = _paths(tmp_path)
    note = paths.layer1 / "04 References" / "note.md"
    note.parent.mkdir()
    note.write_text(_note("Alpha"), encoding="utf-8")
    trash = paths.layer1 / "98-trash" / "hidden.md"
    trash.parent.mkdir()
    trash.write_text(_note("Hidden"), encoding="utf-8")

    first = build_manifest(paths)
    note.unlink()
    second = build_manifest(paths, previous=first)

    assert second.by_relative_path("01-strategy-storage/04 References/note.md") is None
    assert second.by_relative_path("01-strategy-storage/98-trash/hidden.md") is None


def test_manifest_isolated_between_different_roots(tmp_path: Path):
    first_paths = _paths(tmp_path / "one")
    second_paths = _paths(tmp_path / "two")
    first_note = first_paths.layer1 / "04 References" / "note.md"
    second_note = second_paths.layer1 / "04 References" / "note.md"
    first_note.parent.mkdir()
    second_note.parent.mkdir()
    first_note.write_text(_note("One"), encoding="utf-8")
    second_note.write_text(_note("Two"), encoding="utf-8")

    first = build_manifest(first_paths)
    second = build_manifest(second_paths, previous=first)

    assert isinstance(second, DocumentManifest)
    entry = second.by_relative_path("01-strategy-storage/04 References/note.md")
    assert entry is not None and entry.body is not None and "Two" in entry.body
