from __future__ import annotations

import html
import json
import re
import secrets
import socket
import threading
import webbrowser
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Callable
from urllib.parse import unquote, urlsplit

import markdown
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from itsdangerous import BadSignature, URLSafeSerializer
from markupsafe import Markup
from werkzeug.serving import WSGIRequestHandler, make_server
from werkzeug.exceptions import SecurityError

from .broker.broker import approve, load_proposal, propose
from .core.paths import SecondSelfPaths
from .reads.dashboard import (
    DashboardItem,
    MAX_NOTE_BYTES,
    legacy_items,
    scan_dashboard,
)
from .reads.due import due_items
from .reads.recent import recent_items
from .reads.search import search_layer1
from .writes.capture import capture_note
from .writes.journal import journal_entry
from .writes.tag_rename import build_tag_rename_proposal
from .core.frontmatter import read_note


DEFAULT_PORT = 8765
LAST_AUTOMATIC_PORT = 8774
PREVIEW_SALT = "second-self-preview-v1"
CSRF_SESSION_KEY = "_second_self_csrf"
DISALLOWED_LAYER1_PARTS = {"98-trash", "99-audit"}
ALLOWED_MARKDOWN_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "ul",
}
VOID_TAGS = {"br", "hr"}


class _SafeHTMLParser(HTMLParser):
    def __init__(self, rewrite_link: Callable[[str], str | None]) -> None:
        super().__init__(convert_charrefs=True)
        self._rewrite_link = rewrite_link
        self.output: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in ALLOWED_MARKDOWN_TAGS:
            return
        rendered: list[tuple[str, str]] = []
        if tag == "a":
            attributes = dict(attrs)
            href = self._rewrite_link(attributes.get("href", ""))
            if href:
                rendered.append(("href", href))
                if urlsplit(href).scheme in {"http", "https", "mailto"}:
                    rendered.extend(
                        [("rel", "noopener noreferrer"), ("target", "_blank")]
                    )
            if attributes.get("title"):
                rendered.append(("title", attributes["title"] or ""))
        suffix = "".join(
            f' {name}="{html.escape(value, quote=True)}"'
            for name, value in rendered
        )
        self.output.append(f"<{tag}{suffix}>")

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in ALLOWED_MARKDOWN_TAGS and tag not in VOID_TAGS:
            self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.output.append(html.escape(data))


class _QuietRequestHandler(WSGIRequestHandler):
    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        return

    def log_error(self, format: str, *args: object) -> None:
        return


def _clean_controls(value: str) -> str:
    return "".join(
        character
        for character in value
        if character in "\n\r\t" or (ord(character) >= 32 and ord(character) != 127)
    )


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def _resolve_preview(
    paths: SecondSelfPaths, scope: str, relative_path: str
) -> tuple[Path, Path] | None:
    if scope == "layer1":
        root = paths.layer1
    elif scope == "projects":
        root = paths.projects
    else:
        return None
    if "\\" in relative_path:
        return None
    pure = PurePosixPath(relative_path)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(
            part in {"", ".", ".."}
            or ":" in part
            or any(ord(character) < 32 or ord(character) == 127 for character in part)
            for part in pure.parts
        )
    ):
        return None
    folded_parts = tuple(part.casefold() for part in pure.parts)
    if scope == "layer1" and folded_parts[0] in DISALLOWED_LAYER1_PARTS:
        return None
    if scope == "layer1" and folded_parts[:3] == ("01 notes", "04 imports", "originals"):
        return None
    if scope == "projects" and len(pure.parts) != 1:
        return None
    candidate = root.joinpath(*pure.parts)
    if (
        candidate.suffix.casefold() != ".md"
        or not candidate.is_file()
        or not _is_inside(candidate, root)
    ):
        return None
    try:
        if candidate.stat().st_size > MAX_NOTE_BYTES:
            return None
    except OSError:
        return None
    return root, candidate


def _relative_display(scope: str, relative_path: str) -> str:
    prefix = (
        "01-strategy-storage"
        if scope == "layer1"
        else "02-skills-projects/projects"
    )
    return f"{prefix}/{relative_path}"


def create_app(
    paths: SecondSelfPaths,
    *,
    read_only: bool = False,
    secret_key: str | bytes | None = None,
    testing: bool = False,
) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=secret_key or secrets.token_hex(32),
        MAX_CONTENT_LENGTH=128 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=False,
        TRUSTED_HOSTS=["localhost", "127.0.0.1"],
        TESTING=testing,
        READ_ONLY=read_only,
    )
    serializer = URLSafeSerializer(app.config["SECRET_KEY"], salt=PREVIEW_SALT)
    app.extensions["second_self_paths"] = paths
    app.extensions["second_self_preview_serializer"] = serializer

    def csrf_token() -> str:
        token = session.get(CSRF_SESSION_KEY)
        if not token:
            token = secrets.token_urlsafe(32)
            session[CSRF_SESSION_KEY] = token
        return str(token)

    def preview_token(scope: str, relative_path: str) -> str:
        return serializer.dumps({"scope": scope, "path": relative_path})

    def preview_url(item: DashboardItem) -> str:
        return url_for(
            "preview",
            token=preview_token(item.scope, item.relative_path),
        )

    def tag_token(tag: str) -> str:
        return serializer.dumps({"tag": tag})

    def tag_url(tag: str) -> str:
        return url_for("tag_view", token=tag_token(tag))

    app.jinja_env.globals.update(
        csrf_token=csrf_token,
        preview_url=preview_url,
        tag_url=tag_url,
    )

    @app.after_request
    def security_headers(response):  # type: ignore[no-untyped-def]
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'none'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'; "
            "style-src 'self'; script-src 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response

    @app.get("/healthz")
    def healthz():
        return {"status": "ready"}

    @app.get("/stats")
    def stats():
        snapshot = scan_dashboard(paths)
        captures = snapshot.queues.get("captures")
        return {
            "scanned_files": snapshot.scanned_files,
            "captures": len(captures.items) if captures else 0,
            "wiki_pending": len(snapshot.wiki.get("pending", [])),
            "active_projects": len(snapshot.active_projects),
        }

    @app.get("/legacy")
    def legacy():
        items = legacy_items(paths)
        return render_template(
            "legacy.html",
            items=items,
            read_only=read_only,
        )

    @app.get("/")
    def home():
        snapshot = scan_dashboard(paths)
        return render_template(
            "home.html",
            snapshot=snapshot,
            queue_order=("captures",),
            read_only=read_only,
        )

    @app.get("/queue/<queue_key>")
    def queue_view(queue_key: str):
        snapshot = scan_dashboard(paths)
        queue = snapshot.queues.get(queue_key)
        if queue is None:
            abort(404)
        return render_template(
            "queue.html",
            queue=queue,
            read_only=read_only,
        )

    @app.get("/tags")
    def tag_list():
        snapshot = scan_dashboard(paths)
        tags = sorted(
            snapshot.tag_index.items(),
            key=lambda pair: (-len(pair[1]), pair[0].casefold()),
        )
        return render_template(
            "tags.html",
            tags=tags,
            read_only=read_only,
        )

    @app.get("/tags/<token>")
    def tag_view(token: str):
        try:
            payload = serializer.loads(token)
        except BadSignature:
            abort(404)
        if not isinstance(payload, dict):
            abort(404)
        tag = str(payload.get("tag", ""))
        snapshot = scan_dashboard(paths)
        items = snapshot.tag_index.get(tag)
        if items is None:
            abort(404)
        all_tags = sorted(
            snapshot.tag_index.items(),
            key=lambda pair: (-len(pair[1]), pair[0].casefold()),
        )
        return render_template(
            "tag.html",
            tag=tag,
            items=items,
            tags=all_tags,
            read_only=read_only,
        )

    @app.post("/tags/rename")
    def rename_tag():
        if read_only:
            abort(403)
        submitted = request.form.get("csrf_token", "")
        expected = session.get(CSRF_SESSION_KEY, "")
        if not expected or not secrets.compare_digest(str(expected), submitted):
            abort(400)
        old_tag = (request.form.get("old_tag") or "").strip()
        new_tag = (request.form.get("new_tag") or "").strip()
        if not old_tag or not new_tag:
            flash("Both old and new tags are required.", "error")
            return redirect(url_for("tag_list"))
        try:
            specification = build_tag_rename_proposal(paths, old_tag, new_tag)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("tag_list"))
        proposal = propose(paths, specification)
        paths.audit.mkdir(parents=True, exist_ok=True)
        event = {
            "time": proposal["created"],
            "agent": "dashboard",
            "action": "tag-rename-propose",
            "paths": [item["path"] for item in specification.get("changes", [])],
            "approval": proposal["id"],
        }
        with (paths.audit / "agent-edits.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event) + "\n")
        flash(
            f"Tag rename proposal created: {old_tag} -> {new_tag}. Review and approve it below.",
            "success",
        )
        return redirect(url_for("broker_show", proposal_id=proposal["id"]), code=303)

    @app.get("/broker/<proposal_id>")
    def broker_show(proposal_id: str):
        try:
            proposal = load_proposal(paths, proposal_id)
        except FileNotFoundError:
            abort(404)
        return render_template(
            "broker.html",
            proposal=proposal,
            read_only=read_only,
        )

    @app.post("/broker/<proposal_id>/approve")
    def broker_approve(proposal_id: str):
        if read_only:
            abort(403)
        submitted = request.form.get("csrf_token", "")
        expected = session.get(CSRF_SESSION_KEY, "")
        if not expected or not secrets.compare_digest(str(expected), submitted):
            abort(400)
        confirmation = request.form.get("confirm", "Y")
        result = approve(paths, proposal_id, confirmation, agent="dashboard")
        flash("Tag rename applied.", "success")
        return redirect(url_for("broker_show", proposal_id=proposal_id))

    @app.route("/capture", methods=["GET", "POST"])
    def capture():
        if read_only:
            return render_template("capture.html", read_only=True), 403
        if request.method == "POST":
            submitted = request.form.get("csrf_token", "")
            expected = session.get(CSRF_SESSION_KEY, "")
            if not expected or not secrets.compare_digest(str(expected), submitted):
                abort(400)
            title = request.form.get("title", "")
            body = request.form.get("body", "")
            try:
                captured = capture_note(
                    paths,
                    title,
                    body,
                    source="dashboard",
                    require_body=True,
                )
            except ValueError as exc:
                return (
                    render_template(
                        "capture.html",
                        read_only=False,
                        error=str(exc),
                        title=title,
                        body=body,
                    ),
                    400,
                )
            relative = captured.path.relative_to(paths.layer1).as_posix()
            flash("Capture saved to the private inbox.", "success")
            return redirect(
                url_for(
                    "preview",
                    token=preview_token("layer1", relative),
                ),
                code=303,
            )
        return render_template("capture.html", read_only=False)

    @app.get("/search")
    def search():
        query = request.args.get("q", "").strip()
        results = search_layer1(paths, query) if query else []
        for result in results:
            result["preview_url"] = url_for(
                "preview",
                token=preview_token(
                    result.get("scope", "layer1"),
                    result.get("relative_path", ""),
                ),
            )
            matched = result.get("matched", "")
            snippet_html = html.escape(result.get("snippet", ""))
            if matched:
                snippet_html = snippet_html.replace(
                    html.escape(matched),
                    f"<mark>{html.escape(matched)}</mark>",
                )
            result["snippet_html"] = Markup(snippet_html)
        return render_template(
            "search.html",
            query=query,
            results=results,
            truncated=getattr(results, "truncated", False),
            read_only=read_only,
        )

    @app.get("/due")
    def due():
        results = due_items(paths)
        for item in results:
            item["preview_url"] = url_for(
                "preview",
                token=preview_token(item["scope"], item["relative_path"]),
            )
        overdue = [r for r in results if int(r["days_until_due"]) < 0]
        upcoming = [r for r in results if int(r["days_until_due"]) >= 0]
        return render_template(
            "due.html",
            overdue=overdue,
            upcoming=upcoming,
            read_only=read_only,
        )

    @app.get("/recent")
    def recent():
        days = request.args.get("days", default=7, type=int)
        results = recent_items(paths, days=days)
        for item in results:
            item["preview_url"] = url_for(
                "preview",
                token=preview_token(item["scope"], item["relative_path"]),
            )
        return render_template(
            "recent.html",
            days=days,
            results=results,
            read_only=read_only,
        )

    @app.route("/journal", methods=["GET", "POST"])
    def journal():
        if read_only:
            return render_template("journal.html", read_only=True), 403
        if request.method == "POST":
            submitted = request.form.get("csrf_token", "")
            expected = session.get(CSRF_SESSION_KEY, "")
            if not expected or not secrets.compare_digest(str(expected), submitted):
                abort(400)
            body = request.form.get("body", "")
            title = request.form.get("title", "")
            try:
                entry = journal_entry(paths, body, title=title)
            except ValueError as exc:
                return (
                    render_template(
                        "journal.html",
                        read_only=False,
                        error=str(exc),
                        title=title,
                        body=body,
                    ),
                    400,
                )
            relative = entry.path.relative_to(paths.layer1).as_posix()
            flash("Journal entry saved.", "success")
            return redirect(
                url_for(
                    "preview",
                    token=preview_token("layer1", relative),
                ),
                code=303,
            )
        return render_template("journal.html", read_only=False)

    @app.get("/view/<token>")
    def preview(token: str):
        try:
            payload = serializer.loads(token)
        except BadSignature:
            abort(404)
        if not isinstance(payload, dict):
            abort(404)
        scope = str(payload.get("scope", ""))
        relative_path = str(payload.get("path", ""))
        resolved = _resolve_preview(paths, scope, relative_path)
        if resolved is None:
            abort(404)
        root, note = resolved
        try:
            metadata, body = read_note(note)
        except (OSError, UnicodeError, ValueError):
            abort(404)

        def rewrite_link(value: str) -> str | None:
            parsed = urlsplit(value)
            scheme = parsed.scheme.casefold()
            if scheme in {"http", "https", "mailto"}:
                return value
            if scheme or parsed.netloc or not parsed.path:
                return None
            candidate = (note.parent / unquote(parsed.path)).resolve()
            if not _is_inside(candidate, root):
                return None
            try:
                candidate_relative = candidate.relative_to(root.resolve()).as_posix()
            except ValueError:
                return None
            if _resolve_preview(paths, scope, candidate_relative) is None:
                return None
            internal = url_for(
                "preview",
                token=preview_token(scope, candidate_relative),
            )
            if parsed.fragment and re.fullmatch(r"[-A-Za-z0-9_:.]+", parsed.fragment):
                internal += f"#{parsed.fragment}"
            return internal

        escaped = html.escape(_clean_controls(body))
        generated = markdown.markdown(escaped, extensions=["sane_lists"])
        parser = _SafeHTMLParser(rewrite_link)
        parser.feed(generated)
        parser.close()
        safe_html = Markup("".join(parser.output))
        tags = metadata.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        return render_template(
            "preview.html",
            metadata={
                "type": metadata.get("type", ""),
                "status": metadata.get("status", ""),
                "created": metadata.get("created", ""),
            },
            tags=[str(tag) for tag in tags if isinstance(tag, str) and tag.strip()],
            title=next(
                (
                    line[2:].strip()
                    for line in body.splitlines()
                    if line.startswith("# ") and line[2:].strip()
                ),
                note.stem,
            ),
            content=safe_html,
            relative_path=_relative_display(scope, relative_path),
            read_only=read_only,
        )

    @app.errorhandler(SecurityError)
    def untrusted_host(error):  # type: ignore[no-untyped-def]
        correlation = secrets.token_hex(4)
        page = (
            "<!doctype html><html lang=\"en\"><head>"
            "<meta charset=\"utf-8\"><meta name=\"color-scheme\" content=\"dark\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>Local request rejected · Second Self</title>"
            "<style>body{margin:0;background:#1b1c20;color:#f2eee5}"
            "main{display:flex;min-height:100vh;align-items:center;justify-content:center}"
            ".card{border:1px solid #414249;border-radius:24px;background:#25262b;"
            "box-shadow:0 18px 50px rgba(0,0,0,.24);max-width:600px;padding:2.5rem;text-align:center}"
            ".accent{color:#e2bd6b}.muted{color:#b8b2a6;font-size:.82rem}"
            "a{color:#e2bd6b;text-decoration:none}a:hover{color:#d5ad5b}"
            "code{background:#3d3322;padding:.1rem .25rem;border-radius:3px}</style></head>"
            "<body><main><section class=\"card\">"
            "<p class=\"accent\">Local request rejected</p>"
            "<h1>Second Self could not complete that request.</h1>"
            "<p class=\"muted\">No private content or filesystem details were included in this error.</p>"
            "<p class=\"muted\">Reference: <code>"
            + correlation
            + "</code></p>"
            "<p><a href=\"/\">Return Home</a></p>"
            "</section></main></body></html>"
        )
        return page, 400

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(413)
    def expected_error(error):  # type: ignore[no-untyped-def]
        code = int(getattr(error, "code", 500))
        return (
            render_template(
                "error.html",
                code=code,
                correlation=secrets.token_hex(4),
            ),
            code,
        )

    if not testing:
        @app.errorhandler(Exception)
        def unexpected_error(error):  # type: ignore[no-untyped-def]
            return (
                render_template(
                    "error.html",
                    code=500,
                    correlation=secrets.token_hex(4),
                ),
                500,
            )

    return app


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
        try:
            stream.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _select_port(explicit: int | None) -> int:
    if explicit is not None:
        if not 1 <= explicit <= 65535:
            raise ValueError("Port must be between 1 and 65535.")
        if not _port_available(explicit):
            raise RuntimeError(
                f"Local port {explicit} is already in use. Choose another --port."
            )
        return explicit
    for port in range(DEFAULT_PORT, LAST_AUTOMATIC_PORT + 1):
        if _port_available(port):
            return port
    raise RuntimeError(
        f"No free local port was found from {DEFAULT_PORT} through "
        f"{LAST_AUTOMATIC_PORT}."
    )


def serve_web(
    paths: SecondSelfPaths,
    *,
    port: int | None = None,
    open_browser: bool = True,
    read_only: bool = False,
) -> None:
    selected = _select_port(port)
    app = create_app(paths, read_only=read_only)
    server = make_server(
        "127.0.0.1",
        selected,
        app,
        threaded=False,
        request_handler=_QuietRequestHandler,
    )
    url = f"http://127.0.0.1:{selected}/"
    print(f"Second Self Home: {url}")
    print("Private content remains local. Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.35, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
