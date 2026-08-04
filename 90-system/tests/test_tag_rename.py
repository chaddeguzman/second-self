from __future__ import annotations

from pathlib import Path

import pytest

from second_self.cli import main
from second_self.dashboard import scan_dashboard
from second_self.frontmatter import split_frontmatter
from second_self.paths import SecondSelfPaths
from second_self.tag_rename import _replace_tag_in_frontmatter, build_tag_rename_proposal
from second_self.web import create_app


def _paths(tmp_path: Path) -> SecondSelfPaths:
    data_root = tmp_path / "private"
    layer1 = data_root / "01-strategy-storage"
    projects = data_root / "02-skills-projects" / "projects"
    for path in (layer1, projects):
        path.mkdir(parents=True)
    return SecondSelfPaths(repo_root=tmp_path / "repo", data_root=data_root)


def _app(tmp_path: Path, *, read_only: bool = False):
    paths = _paths(tmp_path)
    app = create_app(
        paths,
        read_only=read_only,
        secret_key=b"test-only-secret",
        testing=True,
    )
    return app, paths


def _note(path: Path, metadata: str, title: str = "Example", body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\n{metadata.strip()}\n---\n\n# {title}\n{body}\n",
        encoding="utf-8",
    )


def test_replace_tag_in_frontmatter_preserves_other_fields():
    content = (
        "---\n"
        "type: note\n"
        "created: 2026-01-01\n"
        "status: active\n"
        "tags: [health, work]\n"
        "---\n"
        "\n"
        "# Hello\n"
    )
    new_content, replaced = _replace_tag_in_frontmatter(content, "health", "wellness")
    assert replaced is True
    metadata, body = split_frontmatter(new_content)
    assert metadata["tags"] == ["wellness", "work"]
    assert metadata["type"] == "note"
    assert body.strip().startswith("# Hello")


def test_replace_tag_returns_false_when_no_frontmatter():
    content = "# Just a heading\n"
    assert _replace_tag_in_frontmatter(content, "a", "b") == (content, False)


def test_replace_tag_deduplicates():
    content = (
        "---\n"
        "type: note\n"
        "tags: [work, health, work]\n"
        "---\n"
        "\n"
        "# Duplicate\n"
    )
    new_content, replaced = _replace_tag_in_frontmatter(content, "work", "career")
    assert replaced is True
    metadata, _ = split_frontmatter(new_content)
    assert metadata["tags"] == ["career", "health"]


def test_build_tag_rename_proposal_requires_different_tags(tmp_path: Path):
    paths = _paths(tmp_path)
    with pytest.raises(ValueError):
        build_tag_rename_proposal(paths, "x", "x")


def test_build_tag_rename_proposal_raises_when_tag_missing(tmp_path: Path):
    paths = _paths(tmp_path)
    (paths.layer1 / "01 Notes/02 Notes").mkdir(parents=True)
    _note(
        paths.layer1 / "01 Notes/02 Notes/Alpha.md",
        "type: note\ncreated: 2026-07-01\nstatus: active\ntags: [work]",
        "Alpha",
    )
    with pytest.raises(ValueError, match="No notes contain tag: missing"):
        build_tag_rename_proposal(paths, "missing", "other")


def test_build_tag_rename_proposal_edits_affected_notes(tmp_path: Path):
    paths = _paths(tmp_path)
    (paths.layer1 / "01 Notes/02 Notes").mkdir(parents=True)
    _note(
        paths.layer1 / "01 Notes/02 Notes/Alpha.md",
        "type: note\ncreated: 2026-07-01\nstatus: active\ntags: [work, health]",
        "Alpha",
    )
    _note(
        paths.layer1 / "01 Notes/02 Notes/Beta.md",
        "type: note\ncreated: 2026-07-02\nstatus: active\ntags: [work]",
        "Beta",
    )
    proposal = build_tag_rename_proposal(paths, "work", "career")
    assert proposal["operation"] == "edit"
    assert len(proposal["changes"]) == 2
    by_path = {item["path"]: item["content"] for item in proposal["changes"]}
    alpha_metadata, _ = split_frontmatter(
        by_path["01-strategy-storage/01 Notes/02 Notes/Alpha.md"]
    )
    assert alpha_metadata["tags"] == ["career", "health"]
    beta_metadata, _ = split_frontmatter(
        by_path["01-strategy-storage/01 Notes/02 Notes/Beta.md"]
    )
    assert beta_metadata["tags"] == ["career"]


def test_tag_rename_web_form_creates_proposal(tmp_path: Path):
    app, paths = _app(tmp_path)
    (paths.layer1 / "01 Notes/02 Notes").mkdir(parents=True, exist_ok=True)
    _note(
        paths.layer1 / "01 Notes/02 Notes/Alpha.md",
        "type: note\ncreated: 2026-07-01\nstatus: active\ntags: [work]",
        "Alpha",
    )
    client = app.test_client()
    client.get("/tags")
    with client.session_transaction() as session:
        csrf = session["_second_self_csrf"]

    response = client.post(
        "/tags/rename",
        data={"old_tag": "work", "new_tag": "career", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    location = response.headers["Location"]
    assert "/broker/" in location
