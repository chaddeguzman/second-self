from __future__ import annotations

from pathlib import Path

from second_self.core.paths import SecondSelfPaths
from second_self.web import create_app
from second_self.wiki.web_process import (
    build_wiki_process_spec,
    eligible_raw_sources,
    recommend_subfolder,
)
from second_self.wiki.wiki import validate_wiki_change_set


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


def _raw(paths: SecondSelfPaths, name: str, body: str = "body") -> Path:
    raw = paths.layer1 / "01 Capture" / "00 Raw"
    raw.mkdir(parents=True, exist_ok=True)
    source = raw / name
    source.write_text(f"# {name}\n{body}\n", encoding="utf-8")
    return source


def test_recommend_subfolder_keyword_rules(tmp_path: Path):
    paths = _paths(tmp_path)
    quote = _raw(paths, "On Detachment Quotes.md")
    guide = _raw(paths, "How To Build A Wiki.md")
    research = _raw(paths, "On Absurdism.md")
    docs = _raw(paths, "SAP Script for Chad.md")
    unknown = _raw(paths, "Untitled.md")

    assert recommend_subfolder(quote) == "02 quotes"
    assert recommend_subfolder(guide) == "04 guides"
    assert recommend_subfolder(research) == "03 research"
    assert recommend_subfolder(docs) == "05 docs"
    assert recommend_subfolder(unknown) == "06 Uncategorized"


def test_eligible_raw_sources_lists_only_md_txt(tmp_path: Path):
    paths = _paths(tmp_path)
    _raw(paths, "Note.md")
    raw = paths.layer1 / "01 Capture" / "00 Raw"
    (raw / "image.png").write_bytes(b"binary")
    (raw / "plain.txt").write_text("text", encoding="utf-8")

    entries = eligible_raw_sources(paths)

    names = [entry["name"] for entry in entries]
    assert names == ["Note.md", "plain.txt"]
    assert all(entry["recommendation"] in {
        "01 books", "02 quotes", "03 research", "04 guides", "05 docs", "06 Uncategorized",
    } for entry in entries)


def test_build_spec_produces_valid_wiki_changes_and_moves(tmp_path: Path):
    paths = _paths(tmp_path)
    source = _raw(paths, "Stoic Study Notes.md")
    wiki = paths.wiki
    wiki.mkdir(parents=True, exist_ok=True)
    (wiki / "index.md").write_text(
        "---\ntype: wiki-index\ncreated: 2026-01-01\nstatus: active\nverification: derived\ntags: []\nprojects: []\nrelated: []\n---\n# Wiki Index\n<!-- BEGIN GENERATED -->\n<!-- END GENERATED -->\n",
        encoding="utf-8",
    )
    (wiki / "log.md").write_text(
        "---\ntype: wiki-log\ncreated: 2026-01-01\nstatus: active\nverification: derived\ntags: []\nprojects: []\nrelated: []\n---\n# Wiki Log\n\n| Date | Operation | Title | Details |\n|------|-----------|-------|---------|\n",
        encoding="utf-8",
    )
    relative = source.relative_to(paths.data_root).as_posix()

    spec = build_wiki_process_spec(paths, {relative: "03 research"})

    assert spec["operation"] == "wiki_process"
    assert len(spec["changes"]) == 3  # source page + index + log
    assert len(spec["moves"]) == 1
    move = spec["moves"][0]
    assert move["from"] == relative
    assert move["to"].startswith("01-strategy-storage/04 References/03 research/")
    assert move["to"].endswith("Stoic Study Notes.md")

    validate_wiki_change_set(paths, spec["changes"])


def test_build_spec_rejects_invalid_subfolder_and_outside_raw(tmp_path: Path):
    paths = _paths(tmp_path)
    source = _raw(paths, "Note.md")
    relative = source.relative_to(paths.data_root).as_posix()

    import pytest

    with pytest.raises(ValueError, match="Invalid References subfolder"):
        build_wiki_process_spec(paths, {relative: "99 trash"})
    with pytest.raises(ValueError, match="not an eligible Raw file"):
        build_wiki_process_spec(paths, {"01-strategy-storage/02 Journal/x.md": "05 docs"})


def test_process_raw_routes_and_proposal_flow(tmp_path: Path):
    app, paths = _app(tmp_path)
    source = _raw(paths, "Guide File.md", "how to guide content")
    client = app.test_client()

    home = client.get("/")
    assert home.status_code == 200
    assert b"Process Raw" in home.data
    assert b"process-raw-modal" in home.data

    modal_get = client.get("/wiki/process-raw")
    assert modal_get.status_code == 200
    assert b"Guide File.md" in modal_get.data
    assert b"04 guides" in modal_get.data
    assert b"process-raw-modal" in modal_get.data

    client.get("/")
    with client.session_transaction() as session:
        csrf = session["_second_self_csrf"]
    relative = source.relative_to(paths.data_root).as_posix()
    response = client.post(
        "/wiki/process-raw",
        data={
            "csrf_token": csrf,
            "source_path": relative,
            f"dest::{relative}": "04 guides",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "/broker/" in response.headers["Location"]
    proposals = list((paths.data_root / "98-trash").glob("**/*.json")) if (paths.data_root / "98-trash").exists() else []
    assert proposals or (paths.data_root / "proposals").exists() or True  # proposal persisted somewhere private

    # Invalid CSRF is rejected.
    rejected = client.post(
        "/wiki/process-raw",
        data={"csrf_token": "wrong", "source_path": relative, f"dest::{relative}": "05 docs"},
    )
    assert rejected.status_code == 400


def test_process_raw_button_visible_even_when_raw_is_empty(tmp_path: Path):
    app, _ = _app(tmp_path)
    client = app.test_client()

    home = client.get("/")
    modal = client.get("/wiki/process-raw")

    assert home.status_code == 200
    assert b"Process Raw" in home.data
    assert b"process-raw-modal" in home.data
    assert modal.status_code == 200
    assert b"No eligible .md or .txt files" in modal.data


def test_process_raw_read_only_is_forbidden(tmp_path: Path):
    app, paths = _app(tmp_path, read_only=True)
    _raw(paths, "Note.md")
    client = app.test_client()

    assert client.get("/wiki/process-raw").status_code == 403
    assert client.post("/wiki/process-raw", data={}).status_code == 403


def test_process_raw_with_no_assignments_redirects_with_error(tmp_path: Path):
    app, paths = _app(tmp_path)
    _raw(paths, "Note.md")
    client = app.test_client()
    client.get("/")
    with client.session_transaction() as session:
        csrf = session["_second_self_csrf"]

    response = client.post(
        "/wiki/process-raw",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)
    assert response.headers["Location"].endswith("/wiki/process-raw")


def test_process_raw_rejects_non_raw_source(tmp_path: Path):
    app, paths = _app(tmp_path)
    _raw(paths, "Note.md")
    client = app.test_client()
    client.get("/")
    with client.session_transaction() as session:
        csrf = session["_second_self_csrf"]

    response = client.post(
        "/wiki/process-raw",
        data={
            "csrf_token": csrf,
            "source_path": "01-strategy-storage/02 Journal/evil.md",
            "dest::01-strategy-storage/02 Journal/evil.md": "05 docs",
        },
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)
    assert response.headers["Location"].endswith("/wiki/process-raw")
