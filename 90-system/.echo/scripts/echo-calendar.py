#!/usr/bin/env python3
"""
echo-calendar — ECHO Google Calendar Connector CLI

A command-line tool that gives ECHO read-only access to Chad's Google
Calendar: OAuth setup, today/week event fetching, a local JSON snapshot
cache with offline fallback, and a health check consumed by echo-doctor.

Usage:
    echo-calendar auth [--base-dir <path>]
    echo-calendar fetch --period today|week [--json] [--base-dir <path>]
    echo-calendar cache --refresh [--base-dir <path>]
    echo-calendar doctor-check [--json] [--base-dir <path>]

Exit codes:
    0  success
    1  usage error or degraded result (e.g. stale snapshot served)
    2  failure (no token, no credentials, API error)

Status: PHASE 1 SCAFFOLD — all logic stubs raise NotImplementedError.
Phase 2 implements fetch/cache/auth against a mocked API; Phase 3 adds
real credentials; Phase 4 verifies live; Phase 5 integrates.
Project plan: 02-skills-projects/projects/echo-google-calendar/PLAN.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Timezone for all date-window computation (PRD: single user, Asia/Shanghai)
CALENDAR_TIMEZONE = "Asia/Shanghai"

# OAuth scope — READ-ONLY by design (PRD non-goal: no write access in
# this project, ever, until Phase 4+ brokered autonomy).
OAUTH_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"

# Keyring service name under which the token record is stored
KEYRING_SERVICE = "second-self-echo-calendar"

# Snapshot staleness thresholds (hours). Explicit staleness beats silent
# staleness — the CLI always reports age when serving from cache.
STALE_TODAY_HOURS = 6
STALE_WEEK_HOURS = 12

# Severity levels (mirror echo-doctor for doctor-check output)
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


def _credentials_path(base_dir: Path) -> Path:
    """Return the path where credentials.json is expected (Phase 3)."""
    return base_dir / "scripts" / "credentials.json"


def _cache_dir(base_dir: Path) -> Path:
    """Return the snapshot cache directory (git-ignored by design)."""
    # NOTE: .second-self-cache/ lives at repo root and is git-ignored.
    return base_dir.parent.parent / ".second-self-cache" / "calendar"


# ---------------------------------------------------------------------------
# Token storage (Phase 2)
# ---------------------------------------------------------------------------

def load_token(base_dir: Path) -> dict[str, Any]:
    """Load the token record: keyring primary, local JSON fallback.

    Returns the token dict and records which store served it.
    Raises: FileNotFoundError when neither store has a token.
    """
    raise NotImplementedError("Phase 2: token load (keyring + fallback)")


def save_token(base_dir: Path, token: dict[str, Any]) -> str:
    """Persist the token record to keyring (primary) and fallback JSON.

    Returns the name of the primary store used ("keyring" or "local").
    """
    raise NotImplementedError("Phase 2: token save (keyring + fallback)")


# ---------------------------------------------------------------------------
# Snapshot cache (Phase 2)
# ---------------------------------------------------------------------------

def write_snapshot(base_dir: Path, snapshot: dict[str, Any]) -> Path:
    """Write the event snapshot JSON to the cache directory."""
    raise NotImplementedError("Phase 2: snapshot write")


def read_snapshot(base_dir: Path) -> dict[str, Any] | None:
    """Read the cached snapshot, or None if absent/unreadable."""
    raise NotImplementedError("Phase 2: snapshot read")


def snapshot_age_hours(snapshot: dict[str, Any]) -> float:
    """Return the snapshot's age in hours based on its fetched_at stamp."""
    raise NotImplementedError("Phase 2: snapshot age")


def is_stale(snapshot: dict[str, Any]) -> bool:
    """Return True when the snapshot is older than the period's threshold."""
    raise NotImplementedError("Phase 2: staleness check (6h/12h thresholds)")


# ---------------------------------------------------------------------------
# Calendar client (Phase 2 — mocked; Phase 4 — live)
# ---------------------------------------------------------------------------

def build_service(base_dir: Path) -> Any:
    """Build an authorized googleapiclient service for calendar.readonly."""
    raise NotImplementedError("Phase 2: service build (mocked); Phase 4: live")


def fetch_events(base_dir: Path, period: str) -> dict[str, Any]:
    """Fetch today's or this week's events; return the snapshot dict.

    Falls back to the cached snapshot (with an explicit staleness notice)
    when live fetch fails.
    """
    raise NotImplementedError("Phase 2: fetch + normalize + fallback")


# ---------------------------------------------------------------------------
# OAuth flow (Phase 2 — mocked; Phase 3 — real)
# ---------------------------------------------------------------------------

def run_auth(base_dir: Path) -> dict[str, Any]:
    """Run the installed-app OAuth flow and persist the resulting token."""
    raise NotImplementedError("Phase 2: auth flow (mocked); Phase 3: real")


# ---------------------------------------------------------------------------
# Doctor check (Phase 2 — CLI side; Phase 5 — echo-doctor integration)
# ---------------------------------------------------------------------------

def run_doctor_check(base_dir: Path) -> dict[str, str]:
    """Report connector health: token present, credentials.json exists,
    snapshot readable. Shape mirrors echo-doctor checks:
    {"check": "calendar-connector", "status": OK|WARN|FAIL, "detail": str}
    """
    raise NotImplementedError("Phase 2: doctor-check")


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _render_text(snapshot: dict[str, Any], stale_notice: str | None) -> str:
    """Render a snapshot as human-readable text lines."""
    raise NotImplementedError("Phase 2: text rendering")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_auth(args: argparse.Namespace) -> int:
    """Run the OAuth flow and store the token."""
    base = Path(args.base_dir) if args.base_dir else _default_base_dir()
    run_auth(base)
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    """Fetch events for the requested period and print them."""
    base = Path(args.base_dir) if args.base_dir else _default_base_dir()
    snapshot = fetch_events(base, args.period)
    if args.json:
        print(json.dumps(snapshot, indent=2))
    else:
        print(_render_text(snapshot, stale_notice=None))
    return 0


def cmd_cache(args: argparse.Namespace) -> int:
    """Refresh the local snapshot cache from live data."""
    base = Path(args.base_dir) if args.base_dir else _default_base_dir()
    raise NotImplementedError("Phase 2: cache refresh command")


def cmd_doctor(args: argparse.Namespace) -> int:
    """Print the connector health check."""
    base = Path(args.base_dir) if args.base_dir else _default_base_dir()
    result = run_doctor_check(base)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"[{result['status']}] {result['check']}: {result['detail']}")
    return 0


# ---------------------------------------------------------------------------
# CLI setup
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="echo-calendar",
        description="Read-only Google Calendar connector for ECHO.",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        help="Override the .echo base directory (default: auto-detected)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Machine-readable JSON output",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_auth = sub.add_parser("auth", help="Run the OAuth flow, store the token")
    p_auth.set_defaults(func=cmd_auth)

    p_fetch = sub.add_parser("fetch", help="Fetch events (live, cache fallback)")
    p_fetch.add_argument(
        "--period", choices=["today", "week"], required=True,
        help="Time window: today or this week",
    )
    p_fetch.set_defaults(func=cmd_fetch)

    p_cache = sub.add_parser("cache", help="Snapshot cache operations")
    p_cache.add_argument(
        "--refresh", action="store_true",
        help="Refresh the snapshot from live data",
    )
    p_cache.set_defaults(func=cmd_cache)

    p_doc = sub.add_parser("doctor-check", help="Report connector health")
    p_doc.set_defaults(func=cmd_doctor)

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