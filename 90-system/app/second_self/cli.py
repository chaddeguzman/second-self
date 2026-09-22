from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from .agent_status import build_report as build_agent_status_report
from .agent_status import render_report as render_agent_status
from .broker.broker import (
    approve,
    load_proposal,
    propose,
    recover_wiki_transactions,
)
from .capabilities import (
    build_guide_report as build_capability_guide_report,
)
from .capabilities import (
    build_report as build_capability_report,
)
from .capabilities import (
    render_guide as render_capability_guide,
)
from .connectors import (
    ConnectorKind,
    ConnectorRequest,
    ConnectorResult,
    ConnectorState,
    GmailAuthError,
    GmailCredentialStore,
    authorize_gmail,
    load_gmail_credentials,
)
from .connectors.gmail import GmailConnector
from .core.paths import CONFIG_PATH, REPO_ROOT, load_paths, write_config
from .core.scaffold import scaffold
from .evaluation import discover_suites, run_suite
from .evaluation import render_text as render_eval_text
from .evaluation.reporting import (
    BASELINE_VERSION,
    BaselineError,
    baseline_compatibility,
    compare_report,
    load_baseline,
    render_comparison_text,
    write_baseline,
)
from .health import HealthRegistry, SystemHealthContext, build_system_health_registry
from .health.registry import exit_code, render_json, render_text
from .ingest.ingest import ingest
from .maintenance.indexes import generate_indexes
from .maintenance.link_check import build_link_fix_proposal
from .maintenance.tag_audit import audit_tags, build_tag_audit_proposal
from .maintenance.validation import validate
from .observability.retrieval_quality import (
    RetrievalEvent,
    append_event,
    load_events,
    summarize_events,
)
from .projects.projects import register_project, registration_preview
from .reads.dashboard import legacy_items, scan_dashboard
from .reads.due import due_items
from .reads.recall import hybrid_recall
from .reads.recent import recent_items
from .reads.search import search_layer1
from .reads.semantic import (
    FastEmbedder,
    SemanticError,
    SemanticIndex,
    layer1_documents,
    memory_store_documents,
)
from .retrieval_transparency import build_report as build_retrieval_transparency
from .routing import DataOrigin, DataOriginKind, diagnose_policy
from .scheduler import JobStore, SchedulerStateError
from .scheduler.due import run_due
from .scheduler.launcher import (
    WindowsTaskScheduler,
    install_launcher,
    launcher_status,
    remove_launcher,
)
from .scheduler.lock import SchedulerLock, SchedulerLockError
from .wiki.wiki import add_source, initialize_wiki, lint_wiki, wiki_status
from .writes.capture import capture_note
from .writes.journal import journal_entry
from .writes.tag_rename import build_tag_rename_proposal

EVALUATION_BASELINE_PATH = REPO_ROOT / "90-system" / "evaluation-baseline.json"


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


def _load_echo_health_registry(repo_root: Path) -> HealthRegistry:
    """Load the canonical seven-check ECHO registry without duplicating checks."""
    script = repo_root / "90-system" / ".echo" / "scripts" / "echo-doctor.py"
    if not script.is_file():
        raise FileNotFoundError("ECHO doctor compatibility script is unavailable.")
    try:
        spec = importlib.util.spec_from_file_location("second_self_echo_doctor", script)
        if spec is None or spec.loader is None:
            raise ImportError("loader unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        registry = module.build_registry(script.parent.parent)
    except Exception:
        # NOTE: The underlying import error is deliberately hidden because it
        # can include an absolute repository path or connector configuration.
        raise RuntimeError("ECHO health registry could not be loaded.") from None
    if not isinstance(registry, HealthRegistry):
        raise RuntimeError("ECHO health registry returned an invalid result.")
    return registry


def _command_doctor(args: argparse.Namespace) -> int:
    """Run the shared ECHO health registry through the Second Self CLI."""
    registry = _load_echo_health_registry(REPO_ROOT)
    system_registry = build_system_health_registry(
        SystemHealthContext(repo_root=REPO_ROOT, config_path=CONFIG_PATH)
    )
    for check in system_registry:
        registry.register(check)
    results = registry.run(fix=False)
    if args.json:
        print(render_json(results))
    else:
        print(render_text(results, heading="second-self doctor — system health check"))
    return exit_code(results, strict=args.strict)


def _command_capabilities(args: argparse.Namespace) -> int:
    report = build_capability_guide_report() if args.guide else build_capability_report()
    if args.json:
        _print(report)
    elif args.guide:
        print(render_capability_guide(report))
    else:
        for item in report["capabilities"]:
            print(f"{item['name']}: {item['state']} — {item['summary']}")
    return 0


def _gmail_enabled() -> bool:
    return os.environ.get("SECOND_SELF_GMAIL_ENABLED", "").casefold() in {
        "1",
        "true",
        "yes",
    }


def _gmail_client_config(args: argparse.Namespace) -> Path:
    configured = args.client_config or os.environ.get("SECOND_SELF_GMAIL_CLIENT_CONFIG", "")
    return Path(configured) if configured else Path("missing-gmail-client.json")


def _build_gmail_service():
    try:
        from googleapiclient.discovery import build

        credentials = load_gmail_credentials(GmailCredentialStore())
        return build("gmail", "v1", credentials=credentials, cache_discovery=False)
    except GmailAuthError:
        raise
    except Exception as exc:
        raise GmailAuthError("Gmail service is unavailable") from exc


def _gmail_payload(result: ConnectorResult) -> dict[str, object]:
    return {
        "version": "gmail-connector/v1",
        "kind": result.kind.value,
        "state": result.state.value,
        "message": result.message,
        "items": [
            {
                "id": item.item_id,
                "title": item.title,
                "source_uri": item.source_uri,
                "metadata": dict(item.metadata),
            }
            for item in result.items
        ],
    }


def _render_gmail_result(result: ConnectorResult, *, as_json: bool) -> None:
    payload = _gmail_payload(result)
    if as_json:
        _print(payload)
        return
    print(f"Gmail: {result.state.value}")
    if result.message:
        print(result.message)
    for item in result.items:
        print(f"- {item.title} ({item.source_uri})")


def _command_gmail(args: argparse.Namespace) -> int:
    store = GmailCredentialStore()
    if args.gmail_command == "auth":
        try:
            authorize_gmail(_gmail_client_config(args), store)
        except GmailAuthError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        payload = {
            "version": "gmail-auth/v1",
            "state": "available",
            "message": "Gmail read-only authorization stored in the OS keyring.",
        }
        if args.json:
            _print(payload)
        else:
            print(payload["message"])
        return 0

    request = ConnectorRequest(ConnectorKind.GMAIL, args.query, limit=args.limit)
    if not _gmail_enabled():
        result = ConnectorResult(
            ConnectorKind.GMAIL,
            ConnectorState.DISABLED,
            message="Gmail is disabled; local Second Self recall remains available.",
        )
        _render_gmail_result(result, as_json=args.json)
        return 0
    try:
        connector = GmailConnector(_build_gmail_service, enabled=True)
        result = connector.search(request)
    except GmailAuthError:
        result = ConnectorResult(
            ConnectorKind.GMAIL,
            ConnectorState.UNAVAILABLE,
            message="Gmail authorization is unavailable; run explicit read-only authorization.",
        )
    _render_gmail_result(result, as_json=args.json)
    return 0 if result.state is not ConnectorState.UNAVAILABLE else 2


def _command_route(args: argparse.Namespace) -> int:
    """Explain a fail-closed route decision without invoking a provider."""
    decision = diagnose_policy(
        operation=args.operation,
        sensitivity=args.sensitivity,
        origins=(DataOrigin(DataOriginKind.EXTERNAL_UNTRUSTED, "cli-diagnostic"),),
    )
    if args.json:
        _print(decision.as_dict())
    else:
        provider = decision.provider or "none"
        print(f"route: {decision.outcome.value.upper()}")
        print(f"reason: {decision.reason.value}")
        print(f"provider: {provider}")
        print(f"detail: {decision.explanation}")
    return 0 if decision.provider is not None else 2


def _command_eval(args: argparse.Namespace) -> int:
    """List or run deterministic built-in synthetic evaluation suites."""
    suites = discover_suites()
    paths = load_paths()
    private_roots = (paths.layer1, paths.projects, paths.wiki)
    if args.refresh_baseline:
        if args.suite is not None:
            if args.json:
                _print({"version": BASELINE_VERSION, "error": "invalid_refresh"})
            else:
                print("error: baseline refresh does not accept a suite", file=sys.stderr)
            return 2
        reports = tuple(
            run_suite(suite, private_roots=private_roots) for suite in suites
        )
        try:
            write_baseline(EVALUATION_BASELINE_PATH, reports)
        except BaselineError:
            if args.json:
                _print({"version": BASELINE_VERSION, "error": "refresh_failed"})
            else:
                print("error: baseline refresh failed", file=sys.stderr)
            return 2
        if args.json:
            _print(
                {
                    "version": BASELINE_VERSION,
                    "status": "refreshed",
                    "suites": [suite.name for suite in suites],
                }
            )
        else:
            print(f"baseline refreshed: {len(suites)} suites")
        return 0

    try:
        baseline = load_baseline(EVALUATION_BASELINE_PATH)
        baseline_compatibility(baseline, [suite.name for suite in suites])
    except BaselineError:
        if args.json:
            _print({"version": BASELINE_VERSION, "error": "baseline_unavailable"})
        else:
            print("error: evaluation baseline is unavailable", file=sys.stderr)
        return 2
    if args.suite is None:
        names = [suite.name for suite in suites]
        if args.json:
            _print(
                {
                    "version": "evaluation-suite-list/v1",
                    "suites": names,
                    "baseline": "compatible",
                }
            )
        else:
            print("Available evaluation suites:")
            for name in names:
                print(f"- {name}")
            print("baseline: compatible")
        return 0
    selected = next((suite for suite in suites if suite.name == args.suite), None)
    if selected is None:
        if args.json:
            _print(
                {
                    "version": "evaluation-suite-list/v1",
                    "error": "unknown_suite",
                }
            )
        else:
            print("error: unknown evaluation suite", file=sys.stderr)
        return 2
    report = run_suite(
        selected,
        private_roots=private_roots,
    )
    try:
        comparison = compare_report(report, baseline)
    except BaselineError:
        if args.json:
            _print({"version": BASELINE_VERSION, "error": "baseline_incompatible"})
        else:
            print("error: evaluation baseline is incompatible", file=sys.stderr)
        return 2
    if args.json:
        output = report.as_dict()
        output["baseline"] = comparison.as_dict()
        _print(output)
    else:
        print(f"{render_eval_text(report)}\n{render_comparison_text(comparison)}")
    return 0 if report.passed and comparison.passed else 1


def _scheduler_store() -> JobStore:
    paths = load_paths(require_config=True)
    return JobStore(paths.cache / "scheduler" / "jobs.json")


def _command_schedule(args: argparse.Namespace) -> int:
    """Read scheduler definitions and redacted run metadata only."""
    if args.schedule_command == "status" and getattr(args, "launcher", False):
        payload = launcher_status(WindowsTaskScheduler())
        if args.json:
            _print(payload)
        else:
            print(f"launcher: {'installed' if payload['installed'] else 'not installed'}")
        return 0
    if args.schedule_command == "install":
        payload = install_launcher(WindowsTaskScheduler(), confirmed=args.confirm)
        if args.json:
            _print(payload)
        else:
            print(json.dumps(payload, indent=2))
        return 0 if payload.get("changed") or payload.get("reason") == "confirmation_required" else 2
    if args.schedule_command == "remove":
        payload = remove_launcher(WindowsTaskScheduler(), confirmed=args.confirm)
        if args.json:
            _print(payload)
        else:
            print(json.dumps(payload, indent=2))
        return 0 if payload.get("changed") or payload.get("reason") == "confirmation_required" else 2
    try:
        state = _scheduler_store().read()
    except SchedulerStateError:
        if args.json:
            _print({"version": "schedule-view/v1", "error": "scheduler_state_unavailable"})
        else:
            print("error: scheduler state is unavailable", file=sys.stderr)
        return 2
    if args.schedule_command == "list":
        jobs = [
            {"job_id": job.job_id, "adapter": job.adapter, "enabled": job.enabled,
             "time_zone": job.time_zone, "schedule": job.schedule.as_dict()}
            for job in state.jobs
        ]
        payload = {"version": "schedule-list/v1", "jobs": jobs}
        if args.json:
            _print(payload)
        else:
            print("Scheduled jobs:")
            for job in jobs:
                print(f"- {job['job_id']} ({job['adapter']}, {'enabled' if job['enabled'] else 'disabled'})")
            if not jobs:
                print("(none)")
        return 0
    runs = [run.as_dict() for run in state.runs]
    payload = {"version": "schedule-status/v1", "job_count": len(state.jobs), "run_count": len(runs), "runs": runs}
    if args.json:
        _print(payload)
    else:
        print(f"Scheduler status: {len(state.jobs)} job(s), {len(runs)} run(s)")
    return 0


def _command_schedule_run_due(args: argparse.Namespace) -> int:
    try:
        paths = load_paths(require_config=True)
        store = JobStore(paths.cache / "scheduler" / "jobs.json")
        result = run_due(
            store,
            SchedulerLock(paths.cache / "scheduler" / "run-due.lock"),
            now=datetime.now(timezone.utc),
        )
    except (SchedulerStateError, SchedulerLockError):
        result = None
    if result is None:
        payload = {"version": "schedule-run/v1", "outcome": "state-failure", "reason": "scheduler_state_unavailable"}
        if args.json:
            _print(payload)
        else:
            print("scheduler run failed: state unavailable", file=sys.stderr)
        return 2
    if args.json:
        _print(result.as_dict())
    else:
        print(f"scheduler run: {result.outcome} ({result.succeeded} succeeded, {result.failed} failed)")
    return {"no-work": 0, "success": 0, "partial-failure": 1, "lock-contention": 2, "state-failure": 2}.get(result.outcome, 2)


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
    try:
        page = search_layer1(paths, args.query, max_results=args.max_results)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    _print(page.as_dict())
    return 0


def _command_recall(args: argparse.Namespace) -> int:
    paths = load_paths(require_config=True)
    semantic_index = SemanticIndex(paths.cache / "semantic-memory" / "index.sqlite3")
    started = perf_counter()
    results = hybrid_recall(
        paths,
        args.query,
        semantic_index=semantic_index,
        embedder=FastEmbedder(),
        max_results=args.max_results,
        min_score=args.min_score,
    )
    fallback = not any(item.get("retrieval") in {"semantic", "hybrid"} for item in results)
    payload: dict[str, object] = {"results": results}
    if args.explain:
        payload["transparency"] = build_retrieval_transparency(results, fallback=fallback)
    _print(payload)
    append_event(
        paths.cache / "retrieval-quality.jsonl",
        RetrievalEvent.from_results(
            result_count=len(results),
            results=results,
            fallback=fallback,
            latency_ms=round((perf_counter() - started) * 1000),
            event_id=f"recall-{round(started * 1000)}",
        ),
    )
    return 0


def _command_agents(args: argparse.Namespace) -> int:
    report = build_agent_status_report(REPO_ROOT / "90-system" / ".echo" / "subagents")
    if args.json:
        _print(report)
    else:
        print(render_agent_status(report))
    return 0


def _command_retrieval_quality(args: argparse.Namespace) -> int:
    paths = load_paths(require_config=True)
    summary = summarize_events(load_events(paths.cache / "retrieval-quality.jsonl"))
    _print(summary)
    return 0


def _command_recall_index(args: argparse.Namespace) -> int:
    paths = load_paths(require_config=True)
    index = SemanticIndex(paths.cache / "semantic-memory" / "index.sqlite3")
    if args.recall_index_command == "status":
        documents = layer1_documents(paths) + memory_store_documents(paths.repo_root)
        try:
            status = index.status(documents, model_id=FastEmbedder().model_id)
            _print(status.as_dict())
        except SemanticError:
            _print({
                "indexed": 0, "expected": len(documents), "changed": 0,
                "missing": len(documents), "model_mismatch": False,
                "ready": False, "fallback_reason": "semantic-index-corrupt",
            })
        return 0
    try:
        embedder = FastEmbedder()
        documents = layer1_documents(paths) + memory_store_documents(paths.repo_root)
        indexed = index.refresh(documents, embedder)
    except SemanticError:
        _print({"error": "embedded semantic model unavailable"})
        return 2
    _print({"indexed": indexed, "sources": len(documents)})
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

    doctor = sub.add_parser(
        "doctor",
        help="run redacted Second Self and ECHO health checks",
    )
    doctor.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 when any check reports WARN",
    )
    doctor.add_argument(
        "--json",
        action="store_true",
        help="emit the stable machine-readable result shape",
    )
    doctor.set_defaults(func=_command_doctor)

    capabilities = sub.add_parser(
        "capabilities", help="show redacted ECHO capability availability"
    )
    capabilities.add_argument("--json", action="store_true")
    capabilities.add_argument(
        "--guide",
        action="store_true",
        help="show state meanings, boundaries, prerequisites, examples, and safe next steps",
    )
    capabilities.set_defaults(func=_command_capabilities)

    gmail = sub.add_parser("gmail", help="explicit read-only Gmail operations")
    gmail_sub = gmail.add_subparsers(dest="gmail_command", required=True)
    gmail_auth = gmail_sub.add_parser("auth", help="authorize Gmail read-only access")
    gmail_auth.add_argument("--client-config", type=Path)
    gmail_auth.add_argument("--json", action="store_true")
    gmail_auth.set_defaults(func=_command_gmail)
    gmail_search = gmail_sub.add_parser("search", help="search bounded Gmail metadata")
    gmail_search.add_argument("query")
    gmail_search.add_argument("--limit", type=int, default=20)
    gmail_search.add_argument("--json", action="store_true")
    gmail_search.set_defaults(func=_command_gmail)

    route = sub.add_parser(
        "route",
        help="explain a model route without invoking a provider",
    )
    route.add_argument("--operation", required=True)
    route.add_argument("--sensitivity", required=True)
    route.add_argument(
        "--dry-run",
        action="store_true",
        required=True,
        help="required safety marker; no provider is invoked",
    )
    route.add_argument("--json", action="store_true")
    route.set_defaults(func=_command_route)

    evaluation = sub.add_parser(
        "eval",
        help="list or run deterministic synthetic evaluation suites",
    )
    evaluation.add_argument("suite", nargs="?")
    evaluation.add_argument(
        "--json",
        action="store_true",
        help="emit the stable versioned machine-readable report",
    )
    evaluation.add_argument(
        "--refresh-baseline",
        action="store_true",
        help="explicitly replace the tracked synthetic baseline for every suite",
    )
    evaluation.set_defaults(func=_command_eval)

    schedule = sub.add_parser("schedule", help="inspect local scheduler state")
    schedule_sub = schedule.add_subparsers(dest="schedule_command", required=True)
    schedule_list = schedule_sub.add_parser("list", help="list job definitions")
    schedule_list.add_argument("--json", action="store_true")
    schedule_status = schedule_sub.add_parser("status", help="show redacted run history status")
    schedule_status.add_argument("--json", action="store_true")
    schedule_status.add_argument("--launcher", action="store_true", help="show Task Scheduler state")
    schedule_run = schedule_sub.add_parser("run-due", help="run due test-only jobs")
    schedule_run.add_argument("--json", action="store_true")
    schedule_install = schedule_sub.add_parser("install", help="preview or install the fixed launcher")
    schedule_install.add_argument("--confirm", action="store_true", help="confirm the OS task mutation")
    schedule_install.add_argument("--json", action="store_true")
    schedule_remove = schedule_sub.add_parser("remove", help="preview or remove the fixed launcher")
    schedule_remove.add_argument("--confirm", action="store_true", help="confirm the OS task mutation")
    schedule_remove.add_argument("--json", action="store_true")
    schedule.set_defaults(func=_command_schedule)
    schedule_run.set_defaults(func=_command_schedule_run_due)

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
    recall.add_argument(
        "--explain",
        action="store_true",
        help="include evidence, provenance, retrieval status, uncertainty, and next action",
    )
    recall.set_defaults(func=_command_recall)

    agents = sub.add_parser("agents", help="show delegated-agent status")
    agents_sub = agents.add_subparsers(dest="agents_command", required=True)
    agents_status = agents_sub.add_parser(
        "status", help="show redacted status and latest assignment for each agent"
    )
    agents_status.add_argument("--json", action="store_true")
    agents_status.set_defaults(func=_command_agents)

    retrieval_quality = sub.add_parser(
        "retrieval-quality", help="show redacted retrieval quality metrics"
    )
    retrieval_quality.set_defaults(func=_command_retrieval_quality)

    recall_index = sub.add_parser(
        "recall-index", help="inspect or rebuild the private semantic index"
    )
    recall_index_sub = recall_index.add_subparsers(
        dest="recall_index_command", required=True
    )
    recall_index_status = recall_index_sub.add_parser("status")
    recall_index_status.set_defaults(func=_command_recall_index)
    recall_index_rebuild = recall_index_sub.add_parser("rebuild")
    recall_index_rebuild.set_defaults(func=_command_recall_index)

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
