from __future__ import annotations

from second_self.core.paths import SecondSelfPaths
from second_self.maintenance.link_check import check_wikilinks
from second_self.maintenance.validation import validate


def _note(root: SecondSelfPaths, relative: str, body: str = "") -> str:
    path = root.layer1 / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return str(path.relative_to(root.data_root).as_posix())


def test_broken_link_detected(second_self: SecondSelfPaths) -> None:
    _note(second_self, "02 Journal/Diary.md", "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n# Diary\n\nSee [[Nonexistent Note]].\n")
    result = check_wikilinks(second_self)
    assert result.scanned_files >= 1
    assert any(link.target == "Nonexistent Note" for link in result.broken)


def test_existing_absolute_link_resolves(second_self: SecondSelfPaths) -> None:
    _note(second_self, "00 Memory/Profile.md", "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n")
    _note(second_self, "02 Journal/Diary.md", "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n# Diary\n\nRef: [[00 Memory/Profile]]\n")
    result = check_wikilinks(second_self)
    assert result.valid


def test_existing_relative_link_resolves(second_self: SecondSelfPaths) -> None:
    _note(second_self, "02 Journal/Sibling.md", "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n")
    _note(second_self, "02 Journal/Diary.md", "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n# Diary\n\nSee [[Sibling]] for context.\n")
    result = check_wikilinks(second_self)
    assert result.valid


def test_global_stem_fallback_resolves(second_self: SecondSelfPaths) -> None:
    _note(second_self, "00 Memory/Profile.md", "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n")
    _note(second_self, "02 Journal/Diary.md", "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n# Diary\n\nSee [[Profile]] from afar.\n")
    result = check_wikilinks(second_self)
    assert result.valid


def test_heading_and_block_fragments_are_stripped(second_self: SecondSelfPaths) -> None:
    _note(second_self, "00 Memory/Profile.md", "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n")
    _note(second_self, "02 Journal/Diary.md", "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n# Diary\n\nSee [[Profile#Section]] and [[Profile^block-id]].\n")
    result = check_wikilinks(second_self)
    assert result.valid


def test_code_block_wikilinks_are_skipped(second_self: SecondSelfPaths) -> None:
    _note(
        second_self,
        "02 Journal/Diary.md",
        "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n# Diary\n\n"
        "```\n[[Not a link]]\n```\n\n"
        "Inline: `[[Also not a link]]`.\n",
    )
    result = check_wikilinks(second_self)
    assert result.valid


def test_embed_links_are_checked(second_self: SecondSelfPaths) -> None:
    _note(second_self, "02 Journal/Diary.md", "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n# Diary\n\n![[Missing Image]]\n")
    result = check_wikilinks(second_self)
    assert any(link.target == "Missing Image" for link in result.broken)


def test_alias_is_stripped_before_resolution(second_self: SecondSelfPaths) -> None:
    _note(second_self, "00 Memory/Profile.md", "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n")
    _note(second_self, "02 Journal/Diary.md", "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n# Diary\n\nSee [[00 Memory/Profile | the profile]].\n")
    result = check_wikilinks(second_self)
    assert result.valid


def test_trash_files_are_skipped(second_self: SecondSelfPaths) -> None:
    _note(second_self, "98-trash/old.md", "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n# Old\n\n[[Broken]]\n")
    result = check_wikilinks(second_self)
    assert result.valid


def test_validate_link_check_reports_broken_links(second_self: SecondSelfPaths) -> None:
    _note(second_self, "02 Journal/Diary.md", "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n# Diary\n\nSee [[Missing Note]].\n")
    errors = validate(second_self, link_check=True)
    assert any("broken wikilink" in error for error in errors)
    assert any("Missing Note" in error for error in errors)


def test_validate_link_check_passes_when_all_links_resolve(second_self: SecondSelfPaths) -> None:
    _note(second_self, "00 Memory/Profile.md", "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n")
    _note(second_self, "02 Journal/Diary.md", "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n# Diary\n\nSee [[00 Memory/Profile]].\n")
    errors = validate(second_self, link_check=True)
    assert not any("broken wikilink" in error for error in errors)


def test_empty_layer1_has_no_broken_links(second_self: SecondSelfPaths) -> None:
    result = check_wikilinks(second_self)
    assert result.total_links == 0
    assert result.valid
