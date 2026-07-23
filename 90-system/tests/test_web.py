from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from second_self.paths import SecondSelfPaths
from second_self.dashboard import MAX_NOTE_BYTES
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
    notes = list((paths.layer1 / "00-inbox").glob("*.md"))
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
    assert not (paths.layer1 / "00-inbox").exists()


def test_preview_escapes_html_and_rewrites_only_safe_links(tmp_path: Path):
    app, paths = _app(tmp_path)
    note = paths.layer1 / "00-inbox" / "note.md"
    target = paths.layer1 / "00-inbox" / "target.md"
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
    token = _token(app, "layer1", "00-inbox/note.md")

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
        ("layer1", "75-imports/originals/source.md"),
        ("layer1", r"75-imports\originals\source.md"),
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
    large = paths.layer1 / "00-inbox" / "large.md"
    large.parent.mkdir()
    large.write_bytes(b"x" * (MAX_NOTE_BYTES + 1))
    oversized_token = _token(app, "layer1", "00-inbox/large.md")
    valid = _token(app, "layer1", "00-inbox/missing.md")

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
        "/capture",
        "/healthz",
        "/queue/<queue_key>",
        "/static/<path:filename>",
        "/view/<token>",
    }
    assert not any(
        fragment in rule
        for rule in paths
        for fragment in ("edit", "delete", "apply", "resolve", "status")
    )


def test_port_selection_uses_requested_port_or_first_available(monkeypatch):
    monkeypatch.setattr(
        "second_self.web._port_available",
        lambda port: port in {8767, 9000},
    )

    assert _select_port(None) == 8767
    assert _select_port(9000) == 9000
    with pytest.raises(RuntimeError, match="already in use"):
        _select_port(8765)
