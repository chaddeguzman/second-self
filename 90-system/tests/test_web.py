from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from second_self.core.paths import SecondSelfPaths
from second_self.reads.dashboard import MAX_NOTE_BYTES
from second_self.web import (
    _select_port,
    create_app,
)


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


def _token(app, scope: str, relative_path: str) -> str:
    return app.extensions["second_self_preview_serializer"].dumps(
        {"scope": scope, "path": relative_path}
    )


def _tag_token(app, tag: str) -> str:
    return app.extensions["second_self_preview_serializer"].dumps({"tag": tag})


def _note(path: Path, metadata: str, title: str = "Example") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\n{metadata.strip()}\n---\n\n# {title}\n",
        encoding="utf-8",
    )


def test_home_is_local_private_and_honest_about_unavailable_queues(tmp_path: Path):
    app, paths = _app(tmp_path)
    legacy = paths.layer1 / "00 Memory" / "private legacy.md"
    legacy.parent.mkdir()
    legacy.write_text("# Private legacy title\nprivate body", encoding="utf-8")

    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"Second Self Home" in response.data
    assert b"Not configured yet" in response.data
    assert b"private legacy title" not in response.data
    assert str(paths.data_root).encode() not in response.data
    assert response.headers["Cache-Control"] == "no-store"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_health_is_content_free_and_bad_host_is_rejected(tmp_path: Path):
    app, _ = _app(tmp_path)
    client = app.test_client()

    health = client.get("/healthz")
    rejected = client.get("/", headers={"Host": "second-self.example"})

    assert health.status_code == 200
    assert health.get_json() == {"status": "ready"}
    assert rejected.status_code == 400
    assert b"second-self.example" not in rejected.data


def test_capture_requires_csrf_and_redirects_to_verified_preview(tmp_path: Path):
    app, paths = _app(tmp_path)
    client = app.test_client()
    client.get("/capture")
    with client.session_transaction() as session:
        csrf = session["_second_self_csrf"]

    rejected = client.post(
        "/capture",
        data={"csrf_token": "wrong", "title": "Secret", "body": "Never logged"},
    )
    response = client.post(
        "/capture",
        data={
            "csrf_token": csrf,
            "title": "First dashboard note",
            "body": "Body preserved exactly.\n",
        },
        follow_redirects=False,
    )

    assert rejected.status_code == 400
    assert b"Never logged" not in rejected.data
    assert response.status_code == 303
    assert response.headers["Location"].startswith("/view/")
    notes = list(paths.raw.glob("*.md"))
    assert len(notes) == 1
    assert "Body preserved exactly.\n" in notes[0].read_text(encoding="utf-8")

    preview = client.get(response.headers["Location"])
    assert preview.status_code == 200
    assert b"First dashboard note" in preview.data
    assert b"Body preserved exactly." in preview.data
    assert str(paths.data_root).encode() not in preview.data


def test_read_only_mode_has_no_write_route(tmp_path: Path):
    app, paths = _app(tmp_path, read_only=True)
    client = app.test_client()
    response = client.get("/capture")
    posted = client.post(
        "/capture",
        data={"csrf_token": "unused", "title": "Blocked", "body": "Blocked"},
    )

    assert response.status_code == 403
    assert posted.status_code == 403
    assert not (paths.layer1 / "00 Memory").exists()


def test_tag_pages_list_tags_and_notes_without_private_content(tmp_path: Path):
    app, paths = _app(tmp_path)
    note = paths.layer1 / "01 Capture" / "02 Notes" / "Tagged.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        "\n".join(
            [
                "---",
                "type: note",
                "created: 2026-07-23",
                "status: active",
                "tags: [health]",
                "---",
                "# Tagged",
                "private body text",
            ]
        ),
        encoding="utf-8",
    )
    client = app.test_client()

    tags = client.get("/tags")
    assert tags.status_code == 200
    assert b"health" in tags.data
    assert b"private body text" not in tags.data
    assert str(paths.data_root).encode() not in tags.data

    tag_page = client.get(f"/tags/{_tag_token(app, 'health')}")
    assert tag_page.status_code == 200
    assert b"Tagged" in tag_page.data
    assert b"private body text" not in tag_page.data
    assert str(paths.data_root).encode() not in tag_page.data


def test_tampered_tag_tokens_fail_safely(tmp_path: Path):
    app, paths = _app(tmp_path)
    client = app.test_client()
    valid = _tag_token(app, "health")

    tampered = client.get(f"/tags/{valid}changed")
    missing = client.get(f"/tags/{_tag_token(app, 'missing')}")

    assert tampered.status_code == 404
    assert missing.status_code == 404
    assert str(paths.data_root).encode() not in tampered.data + missing.data


def test_preview_escapes_html_and_rewrites_only_safe_links(tmp_path: Path):
    app, paths = _app(tmp_path)
    note = paths.layer1 / "00 Memory" / "note.md"
    target = paths.layer1 / "00 Memory" / "target.md"
    note.parent.mkdir()
    note.write_text(
        "\n".join(
            [
                "---",
                "type: capture",
                "status: inbox",
                "created: 2026-07-23",
                "---",
                "# Safety",
                "<script>alert('private')</script>",
                "[unsafe](javascript:alert(1))",
                "[external](https://example.com/path)",
                "[internal](target.md)",
                "![image](https://example.com/private.png)",
            ]
        ),
        encoding="utf-8",
    )
    target.write_text("# Target", encoding="utf-8")
    token = _token(app, "layer1", "00 Memory/note.md")

    response = app.test_client().get(f"/view/{token}")

    assert response.status_code == 200
    assert b"<script>" not in response.data
    assert b"javascript:" not in response.data
    assert b"<img" not in response.data
    assert b'rel="noopener noreferrer"' in response.data
    assert b'target="_blank"' in response.data
    assert b"/view/" in response.data
    assert b"target.md" not in response.data


@pytest.mark.parametrize(
    ("scope", "relative_path"),
    [
        ("layer1", "../outside.md"),
        ("layer1", "99-audit/entry.md"),
        ("layer1", r"99-audit\entry.md"),
        ("layer1", "01 Capture/04 Imports/originals/source.md"),
        ("layer1", r"01 Capture\04 Imports\originals\source.md"),
        ("projects", "nested/repository/note.md"),
        ("unknown", "note.md"),
    ],
)
def test_signed_but_ineligible_preview_paths_fail_safely(
    tmp_path: Path, scope: str, relative_path: str
):
    app, paths = _app(tmp_path)
    candidate = paths.data_root / "outside.md"
    candidate.write_text("# Must not render", encoding="utf-8")
    token = _token(app, scope, relative_path)

    response = app.test_client().get(f"/view/{token}")

    assert response.status_code == 404
    assert b"Must not render" not in response.data
    assert str(paths.data_root).encode() not in response.data


def test_tampered_and_oversized_previews_fail_safely(tmp_path: Path):
    app, paths = _app(tmp_path)
    large = paths.layer1 / "00 Memory" / "large.md"
    large.parent.mkdir()
    large.write_bytes(b"x" * (MAX_NOTE_BYTES + 1))
    oversized_token = _token(app, "layer1", "00 Memory/large.md")
    valid = _token(app, "layer1", "00 Memory/missing.md")

    client = app.test_client()
    oversized = client.get(f"/view/{oversized_token}")
    tampered = client.get(f"/view/{valid}changed")

    assert oversized.status_code == 404
    assert tampered.status_code == 404
    assert str(paths.data_root).encode() not in oversized.data + tampered.data


def test_request_limit_and_route_surface(tmp_path: Path):
    app, _ = _app(tmp_path)
    client = app.test_client()
    client.get("/capture")
    with client.session_transaction() as session:
        csrf = session["_second_self_csrf"]

    response = client.post(
        "/capture",
        data={"csrf_token": csrf, "title": "Large", "body": "x" * (140 * 1024)},
    )
    rules = {(rule.rule, tuple(sorted(rule.methods or ()))) for rule in app.url_map.iter_rules()}
    paths = {rule for rule, _ in rules}

    assert response.status_code == 413
    assert paths == {
        "/",
        "/broker/<proposal_id>",
        "/broker/<proposal_id>/approve",
        "/capture",
        "/due",
        "/healthz",
        "/journal",
        "/queue/<queue_key>",
        "/recent",
        "/search",
        "/static/<path:filename>",
        "/stats",
        "/legacy",
        "/tags",
        "/tags/<token>",
        "/tags/rename",
        "/view/<token>",
        "/wiki/process-raw",
    }
    assert not any(
        fragment in rule
        for rule in paths
        for fragment in ("edit", "delete", "apply", "resolve", "status")
    )


def test_search_page_finds_matches_without_exposing_private_root(tmp_path: Path):
    app, paths = _app(tmp_path)
    note = paths.layer1 / "01 Capture" / "02 Notes" / "Searchable.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        "\n".join(
            [
                "---",
                "type: note",
                "created: 2026-07-23",
                "status: active",
                "---",
                "# Searchable",
                "unique searchable content here",
            ]
        ),
        encoding="utf-8",
    )
    client = app.test_client()

    response = client.get("/search?q=unique%20searchable")

    assert response.status_code == 200
    assert b"<mark>unique searchable</mark> content" in response.data
    assert b"Searchable.md" in response.data
    assert str(paths.data_root).encode() not in response.data


def test_search_get_works_without_csrf(tmp_path: Path):
    app, _ = _app(tmp_path)
    client = app.test_client()

    response = client.get("/search?q=test")

    assert response.status_code == 200
    assert b"Search" in response.data


def test_journal_requires_csrf_and_redirects_to_verified_preview(tmp_path: Path):
    app, paths = _app(tmp_path)
    client = app.test_client()
    client.get("/journal")
    with client.session_transaction() as session:
        csrf = session["_second_self_csrf"]

    rejected = client.post(
        "/journal",
        data={"csrf_token": "wrong", "body": "Never logged"},
    )
    response = client.post(
        "/journal",
        data={
            "csrf_token": csrf,
            "title": "Morning",
            "body": "Journal body preserved.\n",
        },
        follow_redirects=False,
    )

    assert rejected.status_code == 400
    assert b"Never logged" not in rejected.data
    assert response.status_code == 303
    assert response.headers["Location"].startswith("/view/")
    journals = list((paths.layer1 / "02 Journal").glob("*.md"))
    assert len(journals) == 1
    assert "Journal body preserved." in journals[0].read_text(encoding="utf-8")

    preview = client.get(response.headers["Location"])
    assert preview.status_code == 200
    assert b"Journal body preserved." in preview.data
    assert str(paths.data_root).encode() not in preview.data


def test_journal_read_only_mode_returns_403(tmp_path: Path):
    app, paths = _app(tmp_path, read_only=True)
    client = app.test_client()
    response = client.get("/journal")
    posted = client.post(
        "/journal",
        data={"csrf_token": "unused", "body": "Blocked"},
    )

    assert response.status_code == 403
    assert posted.status_code == 403
    assert not list((paths.layer1 / "02 Journal").glob("*.md"))


def test_due_page_lists_overdue_and_upcoming_without_private_root(tmp_path: Path):
    app, paths = _app(tmp_path)
    layer1 = paths.layer1
    today = date.today()
    _note(
        layer1 / "03 Strategy/02 Decisions/Overdue.md",
        f"type: decision\ncreated: {(today - timedelta(days=30)).isoformat()}\nstatus: active\ndue: {(today - timedelta(days=3)).isoformat()}",
        "Overdue task",
    )
    _note(
        layer1 / "03 Strategy/02 Decisions/Upcoming.md",
        f"type: decision\ncreated: {(today - timedelta(days=30)).isoformat()}\nstatus: active\ndue: {(today + timedelta(days=6)).isoformat()}",
        "Upcoming task",
    )

    response = app.test_client().get("/due")

    assert response.status_code == 200
    assert b"Overdue task" in response.data
    assert b"Upcoming task" in response.data
    assert b"Overdue" in response.data
    assert b"Upcoming" in response.data
    assert str(paths.data_root).encode() not in response.data


def test_due_page_empty_state_when_no_due_dates(tmp_path: Path):
    app, _ = _app(tmp_path)
    response = app.test_client().get("/due")
    assert response.status_code == 200
    assert b"No due dates found" in response.data


def test_recent_page_lists_recent_items_without_private_root(tmp_path: Path):
    app, paths = _app(tmp_path)
    layer1 = paths.layer1
    today = date.today()
    _note(
        layer1 / "01 Capture/02 Notes/Recent.md",
        f"type: note\ncreated: {(today - timedelta(days=1)).isoformat()}\nstatus: active",
        "Recent note",
    )

    response = app.test_client().get("/recent?days=7")

    assert response.status_code == 200
    assert b"Recent note" in response.data
    assert str(paths.data_root).encode() not in response.data


def test_recent_page_respects_days_parameter(tmp_path: Path):
    app, paths = _app(tmp_path)
    layer1 = paths.layer1
    today = date.today()
    _note(
        layer1 / "01 Capture/02 Notes/Recent.md",
        f"type: note\ncreated: {(today - timedelta(days=1)).isoformat()}\nstatus: active",
        "Recent note",
    )
    _note(
        layer1 / "01 Capture/02 Notes/Old.md",
        f"type: note\ncreated: {(today - timedelta(days=10)).isoformat()}\nstatus: active",
        "Old note",
    )

    short = app.test_client().get("/recent?days=7")
    long_window = app.test_client().get("/recent?days=30")

    assert b"Recent note" in short.data
    assert b"Old note" not in short.data
    assert b"Recent note" in long_window.data
    assert b"Old note" in long_window.data


def test_port_selection_uses_requested_port_or_first_available(monkeypatch):
    monkeypatch.setattr(
        "second_self.web._port_available",
        lambda port: port in {8767, 9000},
    )

    assert _select_port(None) == 8767
    assert _select_port(9000) == 9000
    with pytest.raises(RuntimeError, match="already in use"):
        _select_port(8765)
