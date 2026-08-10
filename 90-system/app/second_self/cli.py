from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .broker.broker import (
    approve,
    load_proposal,
    propose,
    recover_wiki_transactions,
)
from .core.paths import CONFIG_PATH, load_paths, write_config
from .core.scaffold import scaffold
from .ingest.ingest import ingest
from .maintenance.indexes import generate_indexes
from .maintenance.link_check import build_link_fix_proposal
from .maintenance.tag_audit import audit_tags, build_tag_audit_proposal
from .maintenance.validation import validate
from .projects.projects import register_project, registration_preview
from .reads.dashboard import legacy_items, scan_dashboard
from .reads.due import due_items
from .reads.recall import recall_layer1
from .reads.recent import recent_items
from .reads.search import search_layer1
from .wiki.wiki import add_source, initialize_wiki, lint_wiki, wiki_status
from .writes.capture import capture_note
from .writes.journal import journal_entry
from .writes.tag_rename import build_tag_rename_proposal


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, default=str))


def _command_bootstrap(args: argparse.Namespace) -> int:
    paths = load_paths()
    if args.data_root:
        write_config(Path(args.data_root).expanduser())
        paths = load_paths(require_config=True)
    else:
        write_config(paths.data_root)
    created = scaffold(paths)
    _print({"data_root": paths.data_root, "created": [str(path) for path in created]})
    return 0


def _command_validate(args: argparse.Namespace) -> int:
    require_config = not args.privacy
    paths = load_paths(require_config=require_config)
    errors = validate(
        paths,
        privacy=args.privacy,
        check_private=CONFIG_PATH.exists() and not args.tracked_only,
        link_check=args.link_check,
    )
    audit_result = None
    if args.tag_audit:
        audit_result = audit_tags(paths)
        if not audit_result.valid:
            errors.append("tag audit found issues")
    if errors:
        _print({"valid": False, "errors": errors})
        return 1
    if audit_result is not None:
        specification = build_tag_audit_proposal(paths)
        if specification["changes"]:
            _print(propose(paths, specification))
        else:
            _print(
                {
                    "valid": True,
                    "unused": audit_result.unused,
                    "unregistered": audit_result.unregistered,
                    "near_duplicates": audit_result.near_duplicates,
                }
            )
    else:
        _print({"valid": True})
    return 0


def _command_capture(args: argparse.Namespace) -> int:
    paths = load_paths(require_config=True)
    captured = capture_note(paths, args.title, args.body or "", source="cli")
    print(captured.path.relative_to(paths.data_root))
    return 0


def _command_journal(args: argparse.Namespace) -> int:
    paths = load_paths(require_config=True)
    entry = journal_entry(paths, args.body, title=args.title)
    print(entry.path.relative_to(paths.data_root))
    return 0


def _command_search(args: argparse.Namespace) -> int:
    paths = load_paths(require_config=True)
    _print({"results": search_layer1(paths, args.query, max_results=args.max_results)})
    return 0


def _command_recall(args: argparse.Namespace) -> int:
    paths = load_paths(require_config=True)
    _print(
        {
            "results": recall_layer1(
                paths,
                args.query,
                max_results=args.max_results,
                min_score=args.min_score,
            )
        }
    )
    return 0


def _command_due(args: argparse.Namespace) -> int:
    paths = load_paths(require_config=True)
    _print({"results": due_items(paths, overdue_only=args.overdue_only)})
    return 0


def _command_recent(args: argparse.Namespace) -> int:
    paths = load_paths(require_config=True)
    _print({"results": recent_items(paths, days=args.days)})
    return 0


def _command_web(args: argparse.Namespace) -> int:
    from .web import serve_web

    serve_web(
        load_paths(require_config=True),
        port=args.port,
        open_browser=not args.no_browser,
        read_only=args.read_only,
    )
    return 0


def _command_broker(args: argparse.Namespace) -> int:
    paths = load_paths(require_config=True)
    if args.broker_command == "propose":
        specification = json.loads(Path(args.specification).read_text(encoding="utf-8"))
        _print(propose(paths, specification))
    elif args.broker_command == "show":
        _print(load_proposal(paths, args.id))
    elif args.broker_command == "approve":
        proposal = load_proposal(paths, args.id)
        print(proposal["exact_preview"])
        confirmation = args.confirm or input("Apply this proposal? [y/N]: ")
        _print(approve(paths, args.id, confirmation, args.agent))
    return 0


def _command_tags(args: argparse.Namespace) -> int:
    snapshot = scan_dashboard(load_paths(require_config=True))
    tags: list[dict[str, object]] = [
        {"tag": tag, "count": len(items)}
        for tag, items in sorted(
            snapshot.tag_index.items(),
            key=lambda pair: (-len(pair[1]), pair[0].casefold()),
        )
    ]
    _print({"tags": tags})
    return 0


def _command_tag_rename(args: argparse.Namespace) -> int:
    paths = load_paths(require_config=True)
    specification = build_tag_rename_proposal(paths, args.old_tag, args.new_tag)
    proposal = propose(paths, specification)
    _print(proposal)
    return 0


def _command_stats(args: argparse.Namespace) -> int:
    paths = load_paths(require_config=True)
    snapshot = scan_dashboard(paths)
    all_items = [*snapshot.layer1, *snapshot.projects]
    counts_by_type: dict[str, int] = {}
    counts_by_status: dict[str, int] = {}
    captures_per_month: dict[str, int] = {}
    for item in all_items:
        counts_by_type[item.record_type] = counts_by_type.get(item.record_type, 0) + 1
        counts_by_status[item.status] = counts_by_status.get(item.status, 0) + 1
        if item.record_type == "capture" and item.created is not None:
            month = item.created.strftime("%Y-%m")
            captures_per_month[month] = captures_per_month.get(month, 0) + 1
    _print(
        {
            "counts_by_type": counts_by_type,
            "counts_by_status": counts_by_status,
            "captures_per_month": captures_per_month,
            "project_counts": {
                "total": len(snapshot.projects),
                "active": len(snapshot.active_projects),
                "raw_files": len(snapshot.queues["captures"].items),
            },
            "wiki": snapshot.wiki,
        }
    )
    return 0


def _command_legacy(args: argparse.Namespace) -> int:
    paths = load_paths(require_config=True)
    legacy = legacy_items(paths)
    scope = args.scope
    if scope != "all":
        legacy = tuple(item for item in legacy if item["scope"] == scope)
    if args.json:
        _print(legacy)
    else:
        for item in legacy:
            print(f"{item['scope']}: {item['path']} -- {item['reason']}")
        print(f"\nTotal legacy files: {len(legacy)}")
    return 0


def _command_intake(args: argparse.Namespace) -> int:
    _print(ingest(load_paths(True), args.source))
    return 0


def _command_indexes(args: argparse.Namespace) -> int:
    _print(generate_indexes(load_paths(True)))
    return 0


def _command_link_fix(args: argparse.Namespace) -> int:
    paths = load_paths(require_config=True)
    corrections = None
    if args.corrections:
        corrections = json.loads(Path(args.corrections).read_text(encoding="utf-8"))
    specification = build_link_fix_proposal(paths, corrections=corrections)
    if not specification["fixes"]:
        _print({"valid": True, "message": "No broken wikilinks detected."})
    else:
        _print(propose(paths, specification))
    return 0


def _command_wiki(args: argparse.Namespace) -> int:
    paths = load_paths(require_config=True)
    if args.wiki_command == "init":
        _print(initialize_wiki(paths))
    elif args.wiki_command == "add":
        _print(add_source(paths, args.path))
    elif args.wiki_command == "status":
        _print(wiki_status(paths))
    elif args.wiki_command == "lint":
        errors = lint_wiki(paths)
        _print({"valid": not errors, "errors": errors})
        return int(bool(errors))
    elif args.wiki_command == "recover":
        _print({"recovered": recover_wiki_transactions(paths)})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="second-self")
    sub = parser.add_subparsers(dest="command", required=True)

    bootstrap = sub.add_parser("bootstrap")
    bootstrap.add_argument("--data-root")
    bootstrap.set_defaults(func=_command_bootstrap)

    check = sub.add_parser("validate")
    check.add_argument("--privacy", action="store_true")
    check.add_argument(
        "--tracked-only",
        action="store_true",
        help="skip private-note schema checks and validate tracked repository privacy only",
    )
    check.add_argument(
        "--link-check",
        action="store_true",
        help="verify all [[wikilinks]] in Layer 1 notes resolve to existing targets",
    )
    check.add_argument(
        "--tag-audit",
        action="store_true",
        help="audit tags against the Tag Registry for unused or near-duplicate tags",
    )
    check.set_defaults(func=_command_validate)

    capture = sub.add_parser("capture")
    capture.add_argument("--title", required=True)
    capture.add_argument("--body")
    capture.set_defaults(func=_command_capture)

    journal = sub.add_parser("journal")
    journal.add_argument("--body", required=True)
    journal.add_argument("--title", default="")
    journal.set_defaults(func=_command_journal)

    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--max-results", type=int, default=50)
    search.set_defaults(func=_command_search)

    recall = sub.add_parser("recall")
    recall.add_argument("query")
    recall.add_argument("--max-results", type=int, default=50)
    recall.add_argument("--min-score", type=int, default=0)
    recall.set_defaults(func=_command_recall)

    due = sub.add_parser("due")
    due.add_argument("--overdue-only", action="store_true")
    due.set_defaults(func=_command_due)

    recent = sub.add_parser("recent")
    recent.add_argument("--days", type=int, default=7)
    recent.set_defaults(func=_command_recent)

    web = sub.add_parser("web")
    web.add_argument("--port", type=int)
    web.add_argument("--no-browser", action="store_true")
    web.add_argument("--read-only", action="store_true")
    web.set_defaults(func=_command_web)

    intake = sub.add_parser("ingest")
    intake.add_argument("source", type=Path)
    intake.set_defaults(func=_command_intake)

    indexes = sub.add_parser("indexes")
    indexes.set_defaults(func=_command_indexes)

    link_fix = sub.add_parser("link-fix")
    link_fix.add_argument(
        "--corrections",
        type=Path,
        help="JSON file mapping 'source>wikilink_target' to replacement wikilink text",
    )
    link_fix.set_defaults(func=_command_link_fix)

    tags = sub.add_parser("tags")
    tags.set_defaults(func=_command_tags)

    tag_rename = sub.add_parser("tag-rename")
    tag_rename.add_argument("old_tag")
    tag_rename.add_argument("new_tag")
    tag_rename.set_defaults(func=_command_tag_rename)

    stats = sub.add_parser("stats")
    stats.set_defaults(func=_command_stats)

    legacy = sub.add_parser("legacy")
    legacy.add_argument("--scope", choices=["layer1", "projects", "all"], default="all")
    legacy.add_argument("--json", action="store_true")
    legacy.set_defaults(func=_command_legacy)

    project = sub.add_parser("register-project")
    project.add_argument("path", type=Path)
    project.add_argument("--name", required=True)
    project.add_argument("--repository", default="")
    project.add_argument("--apply", action="store_true")
    def project_command(args: argparse.Namespace) -> int:
        paths = load_paths(True)
        _print(registration_preview(paths, args.path, args.name))
        if not args.apply:
            print("Preview only. Re-run with --apply after review.")
            return 0
        _print([str(path) for path in register_project(
            paths, args.path, args.name, args.repository
        )])
        return 0
    project.set_defaults(func=project_command)

    broker = sub.add_parser("broker")
    broker_sub = broker.add_subparsers(dest="broker_command", required=True)
    proposal = broker_sub.add_parser("propose")
    proposal.add_argument("specification")
    show = broker_sub.add_parser("show")
    show.add_argument("id")
    approval = broker_sub.add_parser("approve")
    approval.add_argument("id")
    approval.add_argument("--confirm")
    approval.add_argument("--agent", default="unknown")
    broker.set_defaults(func=_command_broker)

    wiki = sub.add_parser("wiki")
    wiki_sub = wiki.add_subparsers(dest="wiki_command", required=True)
    wiki_sub.add_parser("init")
    wiki_add = wiki_sub.add_parser("add")
    wiki_add.add_argument("path", type=Path)
    wiki_sub.add_parser("status")
    wiki_sub.add_parser("lint")
    wiki_sub.add_parser("recover")
    wiki.set_defaults(func=_command_wiki)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (FileNotFoundError, FileExistsError, PermissionError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
