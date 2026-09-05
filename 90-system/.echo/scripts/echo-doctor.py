#!/usr/bin/env python3
"""
echo-doctor — ECHO System Health Check CLI

A command-line tool that verifies ECHO's file convention is intact:
stable-block files present, session pointer valid, staging queue size,
log status lines well-formed, stale wip.md detection, and session
filename sanity.

Usage:
    echo-doctor [--fix] [--strict] [--json] [--base-dir <path>]

Exit codes:
    0  all checks OK (or only WARNs without --strict)
    1  any WARN or FAIL with --strict
    2  any FAIL (even without --strict)

All paths default to 90-system/.echo/ but can be overridden with
--base-dir.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Matches: YYYY-MM-DDTHHMM.md (the session convention filename)
SESSION_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{4}\.md$")

# Matches the agent status line: "# Charlie — Status: Done"
STATUS_LINE_RE = re.compile(r"^# .+ — Status: .+$")

# Stable-block files that must exist under the .echo directory
STABLE_BLOCK_FILES = [
    "IDENTITY.md",
    "STABLE_BLOCK.md",
    "RECALL.md",
    "MEMORY-TOOLS.md",
    "CAPABILITIES.md",
    "CAPABILITY-LIST.md",
    "subagents/README.md",
]

# Severity levels
OK = "OK"
WARN = "WARN"
FAIL = "FAIL"


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def _default_base_dir() -> Path:
    """Return the default .echo directory (parent of scripts/)."""
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent


def _redact(path: Path, base_dir: Path) -> str:
    """Return a redacted relative path safe for reports."""
    try:
        return str(path.relative_to(base_dir))
    except ValueError:
        return "<external>"


# ---------------------------------------------------------------------------
# Check helpers
# ---------------------------------------------------------------------------

def _add_result(
    results: list[dict[str, str]], check: str, status: str, detail: str
) -> None:
    """Append one check result to the results list."""
    results.append({"check": check, "status": status, "detail": detail})


def _check_stable_block(base_dir: Path, results: list[dict[str, str]]) -> None:
    """Check 1: all stable-block files exist."""
    missing = [f for f in STABLE_BLOCK_FILES if not (base_dir / f).exists()]
    if missing:
        _add_result(results, 
            "stable-block-files",
            FAIL,
            f"missing: {', '.join(missing)}",
        )
    else:
        _add_result(results, 
            "stable-block-files",
            OK,
            f"all {len(STABLE_BLOCK_FILES)} files present",
        )


def _check_session_pointer(base_dir: Path, results: list[dict[str, str]]) -> None:
    """Check 2: current-session.md is absent or points at an existing file."""
    pointer = base_dir / "memory" / "current-session.md"
    if not pointer.exists():
        _add_result(results, "session-pointer", OK, "no pointer file (fresh state)")
        return
    text = pointer.read_text(encoding="utf-8")
    if "(none)" in text:
        _add_result(results, "session-pointer", OK, "no active session (pointer at (none))")
        return
    match = re.search(r"`([^`]+)`", text)
    if not match:
        _add_result(results, "session-pointer", WARN, "pointer exists but names no session")
        return
    target = base_dir / "memory" / "sessions" / match.group(1)
    if target.exists():
        _add_result(results, "session-pointer", OK, f"points at {match.group(1)}")
    else:
        _add_result(results, 
            "session-pointer",
            FAIL,
            f"points at missing session: {match.group(1)}",
        )


def _check_staging_queue(base_dir: Path, results: list[dict[str, str]]) -> None:
    """Check 3: staging queue size (WARN if > 10 pending memories)."""
    staging = base_dir / "memory" / "staging"
    if not staging.exists():
        _add_result(results, "staging-queue", OK, "no staging directory (empty)")
        return
    count = sum(1 for f in staging.iterdir() if f.is_file())
    if count > 10:
        _add_result(results, "staging-queue", WARN, f"{count} files pending review (> 10)")
    else:
        _add_result(results, "staging-queue", OK, f"{count} files pending")


def _check_log_status_lines(base_dir: Path, results: list[dict[str, str]]) -> None:
    """Check 4: each subagents/*/log.md starts with a well-formed status line."""
    subagents = base_dir / "subagents"
    if not subagents.exists():
        _add_result(results, "log-status-lines", OK, "no subagents directory")
        return
    bad: list[str] = []
    checked = 0
    for log in sorted(subagents.glob("*/log.md")):
        checked += 1
        first = ""
        with log.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    first = line
                break
        if not STATUS_LINE_RE.match(first):
            bad.append(log.parent.name)
    if bad:
        _add_result(results, 
            "log-status-lines",
            WARN,
            f"malformed status line in: {', '.join(bad)}",
        )
    elif checked:
        _add_result(results, "log-status-lines", OK, f"{checked} log(s) well-formed")
    else:
        _add_result(results, "log-status-lines", OK, "no agent logs found")


def _check_stale_wip(
    base_dir: Path, results: list[dict[str, str]], fix: bool
) -> None:
    """Check 5: wip.md files whose log shows the latest task Done are stale."""
    subagents = base_dir / "subagents"
    if not subagents.exists():
        _add_result(results, "stale-wip", OK, "no subagents directory")
        return
    stale: list[Path] = []
    for wip in sorted(subagents.glob("*/wip.md")):
        log = wip.parent / "log.md"
        if not log.exists():
            continue
        # TECHNICAL: Scan log rows bottom-up; the last row with a task-level
        # status (Done/Cancelled) decides. Checkpoint rows (25%/50%/75%) are
        # continuation markers, not terminal states, so they are skipped.
        #
        # JUNIOR: Read the to-do list from the bottom up. Ignore notes like
        # "halfway there" and stop at the first real verdict — if the last
        # verdict says "finished", the WIP note is leftover clutter.
        lines = log.read_text(encoding="utf-8").splitlines()
        latest = ""
        for line in reversed(lines):
            if "| Done |" in line or "| Cancelled |" in line:
                latest = line
                break
        if latest:
            stale.append(wip)
    if not stale:
        _add_result(results, "stale-wip", OK, "no stale wip.md files")
        return
    if fix:
        removed: list[str] = []
        for wip in stale:
            wip.unlink()
            removed.append(wip.parent.name)
        _add_result(results, 
            "stale-wip", OK, f"removed stale wip.md in: {', '.join(removed)}"
        )
    else:
        _add_result(results, 
            "stale-wip",
            WARN,
            f"stale wip.md in: {', '.join(p.parent.name for p in stale)}"
            " (use --fix to remove)",
        )


def _check_session_filenames(base_dir: Path, results: list[dict[str, str]]) -> None:
    """Check 6: session files match the convention; .archived noted separately."""
    sessions = base_dir / "memory" / "sessions"
    if not sessions.exists():
        _add_result(results, "session-filenames", OK, "no sessions directory")
        return
    bad: list[str] = []
    archived = 0
    for f in sorted(sessions.iterdir()):
        if not f.is_file():
            continue
        if f.name == "SESSION-CONVENTION.md":
            continue  # convention doc, expected in this folder
        if f.name.endswith(".archived"):
            archived += 1
        elif not SESSION_FILENAME_RE.match(f.name):
            bad.append(f.name)
    if bad:
        _add_result(results, 
            "session-filenames",
            WARN,
            f"non-conforming names: {', '.join(bad[:5])}"
            + (" ..." if len(bad) > 5 else ""),
        )
    else:
        detail = f"all conforming ({archived} archived)" if archived else "all conforming"
        _add_result(results, "session-filenames", OK, detail)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _print_report(results: list[dict[str, str]], base_dir: Path) -> None:
    """Print the human-readable health report."""
    print(f"echo-doctor — ECHO system health check ({_redact(base_dir, base_dir)})")
    print("=" * 60)
    for r in results:
        marker = {OK: "[OK]  ", WARN: "[WARN]", FAIL: "[FAIL]"}[r["status"]]
        print(f"{marker} {r['check']:<20} {r['detail']}")
    counts = {s: sum(1 for r in results if r["status"] == s) for s in (OK, WARN, FAIL)}
    print("-" * 60)
    print(
        f"Summary: {counts[OK]} OK, {counts[WARN]} WARN, {counts[FAIL]} FAIL"
    )


def _exit_code(results: list[dict[str, str]], strict: bool) -> int:
    """Compute the exit code: 2 on any FAIL, 1 on WARN with --strict, else 0."""
    if any(r["status"] == FAIL for r in results):
        return 2
    if strict and any(r["status"] == WARN for r in results):
        return 1
    return 0


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_doctor(args: argparse.Namespace) -> int:
    """Run all health checks and report."""
    base = Path(args.base_dir) if args.base_dir else _default_base_dir()
    results: list[dict[str, str]] = []

    _check_stable_block(base, results)
    _check_session_pointer(base, results)
    _check_staging_queue(base, results)
    _check_log_status_lines(base, results)
    _check_stale_wip(base, results, fix=args.fix)
    _check_session_filenames(base, results)

    if args.json:
        # NOTE: Paths are already redacted inside check details; the base
        # directory itself is never emitted in JSON output.
        print(json.dumps({"results": results}, indent=2))
    else:
        _print_report(results, base)

    return _exit_code(results, strict=args.strict)


# ---------------------------------------------------------------------------
# CLI setup
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="echo-doctor",
        description="Check that ECHO's file convention is intact.",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        help="Override the .echo base directory (default: auto-detected)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply safe fixes (e.g. remove stale wip.md files)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 on any WARN or FAIL (for pre-commit gating)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Machine-readable JSON output (paths redacted)",
    )
    parser.set_defaults(func=cmd_doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())