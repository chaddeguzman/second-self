from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .broker import (
    approve,
    load_proposal,
    propose,
    recover_wiki_transactions,
)
from .capture import capture_note
from .indexes import generate_indexes
from .ingest import ingest
from .paths import CONFIG_PATH, load_paths, write_config
from .projects import register_project, registration_preview
from .scaffold import scaffold
from .validation import validate
from .wiki import add_source, initialize_wiki, lint_wiki, wiki_status


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
    errors = validate(
        load_paths(require_config=require_config),
        privacy=args.privacy,
        check_private=CONFIG_PATH.exists() and not args.tracked_only,
    )
    if errors:
        _print({"valid": False, "errors": errors})
        return 1
    _print({"valid": True})
    return 0


def _command_capture(args: argparse.Namespace) -> int:
    paths = load_paths(require_config=True)
    captured = capture_note(paths, args.title, args.body or "", source="cli")
    print(captured.path.relative_to(paths.data_root))
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
    check.set_defaults(func=_command_validate)

    capture = sub.add_parser("capture")
    capture.add_argument("--title", required=True)
    capture.add_argument("--body")
    capture.set_defaults(func=_command_capture)

    web = sub.add_parser("web")
    web.add_argument("--port", type=int)
    web.add_argument("--no-browser", action="store_true")
    web.add_argument("--read-only", action="store_true")
    web.set_defaults(func=_command_web)

    intake = sub.add_parser("ingest")
    intake.add_argument("source", type=Path)
    intake.set_defaults(func=lambda args: (_print(ingest(load_paths(True), args.source)) or 0))

    indexes = sub.add_parser("indexes")
    indexes.set_defaults(func=lambda args: (_print(generate_indexes(load_paths(True))) or 0))

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
