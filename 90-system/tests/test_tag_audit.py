from __future__ import annotations

from second_self.core.paths import SecondSelfPaths
from second_self.maintenance.tag_audit import (
    audit_tags,
    build_tag_audit_proposal,
    load_registered_tags,
)


def _note(root: SecondSelfPaths, relative: str, tags: list[str] | None = None) -> str:
    path = root.layer1 / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    tag_line = f"tags: [{', '.join(tags)}]\n" if tags else ""
    path.write_text(
        f"---\ntype: note\ncreated: 2026-08-01\nstatus: active\n{tag_line}---\n\n# {path.stem}\n",
        encoding="utf-8",
    )
    return str(path.relative_to(root.data_root).as_posix())


def _registry(root: SecondSelfPaths, tags: list[str]) -> None:
    path = root.data_root / "01-strategy-storage/Tag Registry.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        "type: reference",
        "created: 2026-07-23",
        "status: active",
        "tags: []",
        "projects: []",
        "related: []",
        "---",
        "# Tag Registry",
        "",
        "Agents must propose additions during review instead of creating near-duplicate",
        "tags. Initial registered tags:",
        "",
    ]
    for tag in tags:
        lines.append(f"- {tag}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_load_registered_tags(second_self: SecondSelfPaths) -> None:
    _registry(second_self, ["weekly-review", "quarterly-review"])
    assert load_registered_tags(second_self) == ["weekly-review", "quarterly-review"]


def test_unused_tag_detected(second_self: SecondSelfPaths) -> None:
    _registry(second_self, ["weekly-review", "quarterly-review"])
    _note(second_self, "02 Journal/Diary.md", tags=["weekly-review"])
    result = audit_tags(second_self)
    assert any(item["tag"] == "quarterly-review" for item in result.unused)


def test_unregistered_tag_reported(second_self: SecondSelfPaths) -> None:
    _registry(second_self, ["weekly-review"])
    _note(second_self, "02 Journal/Diary.md", tags=["weekly-review", "new-tag"])
    result = audit_tags(second_self)
    assert any(item["tag"] == "new-tag" for item in result.unregistered)


def test_near_duplicate_detected(second_self: SecondSelfPaths) -> None:
    _registry(second_self, ["weekly-review"])
    _note(second_self, "02 Journal/Diary.md", tags=["weekly_review"])
    result = audit_tags(second_self)
    assert any(
        item["tag"] == "weekly_review" and item["canonical"] == "weekly-review"
        for item in result.near_duplicates
    )


def test_ambiguous_near_duplicate_no_suggestion(second_self: SecondSelfPaths) -> None:
    _registry(second_self, ["weekly-review", "weekly-reviews"])
    _note(second_self, "02 Journal/Diary.md", tags=["weekly-rev"])
    result = audit_tags(second_self)
    matches = [item for item in result.near_duplicates if item["tag"] == "weekly-rev"]
    assert matches
    assert not matches[0]["fixable"]
    assert matches[0]["canonical"] is None


def test_build_proposal_with_fixable_tags(second_self: SecondSelfPaths) -> None:
    _registry(second_self, ["weekly-review"])
    _note(second_self, "02 Journal/Diary.md", tags=["weekly_review"])
    spec = build_tag_audit_proposal(second_self)
    assert spec["operation"] == "edit"
    assert len(spec["changes"]) == 1
    assert "weekly-review" in spec["changes"][0]["content"]


def test_build_proposal_no_fixable(second_self: SecondSelfPaths) -> None:
    _registry(second_self, ["weekly-review"])
    _note(second_self, "02 Journal/Diary.md", tags=["weekly-review"])
    spec = build_tag_audit_proposal(second_self)
    assert spec["operation"] == "edit"
    assert spec["changes"] == []