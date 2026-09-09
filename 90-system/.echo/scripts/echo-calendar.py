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

Status: PHASE 2 — calendar module implemented against a mocked API
(token storage, fetch/cache/fallback, auth flow, doctor-check). Phase 3
adds real credentials; Phase 4 verifies live; Phase 5 integrates.
Project plan: 02-skills-projects/projects/echo-google-calendar/PLAN.md
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

# TECHNICAL: google-api-core emits a PQC/grpcio FutureWarning at import
# time on every run; it is noise for a CLI, so filter it before the
# google imports pull that module in.
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module=r"google\.api_core\._python_package_support",
)

# TECHNICAL: corporate networks often run TLS inspection with a root CA
# that Python's bundled CA list does not trust (SSL: self-signed
# certificate in certificate chain). truststore makes Python validate
# against the OS certificate store — Windows already trusts the
# corporate root there. Optional: without the package, default SSL
# behavior continues (fine on networks without TLS inspection).
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

import keyring
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from keyring.errors import KeyringError

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

# Keyring entry (user) name — service + user identify the record in
# Windows Credential Manager; one token record per machine.
KEYRING_USER = "token"

# Key inside .second-self.local.json holding the dev/test fallback token
LOCAL_TOKEN_KEY = "echo_calendar_token"

# Snapshot file names inside the cache directory (one file per period so
# today/week staleness thresholds stay independent)
SNAPSHOT_TODAY = "snapshot-today.json"
SNAPSHOT_WEEK = "snapshot-week.json"

# Default calendar (PRD: single calendar for v1)
DEFAULT_CALENDAR_ID = "primary"

# Required keys for a valid token record (ARCHITECTURE.md token schema)
TOKEN_REQUIRED_KEYS = (
    "refresh_token",
    "client_id",
    "client_secret",
    "token_uri",
    "scopes",
)

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


def _local_token_path(base_dir: Path) -> Path:
    """Return the repo-root .second-self.local.json (dev/test fallback)."""
    # base_dir models <repo>/90-system/.echo → repo root is two levels up.
    return base_dir.parent.parent / ".second-self.local.json"


def _snapshot_path(base_dir: Path, period: str) -> Path:
    """Return the snapshot file for a period (today/week kept separate)."""
    name = SNAPSHOT_TODAY if period == "today" else SNAPSHOT_WEEK
    return _cache_dir(base_dir) / name


# ---------------------------------------------------------------------------
# Token storage (Phase 2)
# ---------------------------------------------------------------------------

def load_token(base_dir: Path) -> tuple[dict[str, Any], str]:
    """Load the token record: keyring primary, local JSON fallback.

    Option C (locked 2026-09-08): keyring is the primary source AND
    destination; .second-self.local.json is a fallback used only when
    the keyring read returns nothing or the backend errors.

    Returns (token_dict, store_name) where store_name is "keyring" or
    "local". Raises FileNotFoundError when neither store has a token.
    """
    # TECHNICAL: keyring.get_password returns None for a missing entry
    # and raises KeyringError when no usable backend exists — both mean
    # "try the local fallback", not "fail".
    try:
        raw = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
    except (KeyringError, RuntimeError):
        raw = None
    if raw:
        try:
            return json.loads(raw), "keyring"
        except ValueError:
            pass  # corrupt keyring payload — treat as absent, try local
    local = _local_token_path(base_dir)
    if local.exists():
        try:
            data = json.loads(local.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        token = data.get(LOCAL_TOKEN_KEY) if isinstance(data, dict) else None
        if isinstance(token, dict):
            return token, "local"
    raise FileNotFoundError(
        "No token found in keyring or .second-self.local.json — run `auth` first"
    )


def save_token(base_dir: Path, token: dict[str, Any]) -> str:
    """Persist the token record: keyring primary, local JSON fallback.

    Writes to Windows Credential Manager via keyring; when the keyring
    backend is unavailable or errors, falls back to the git-ignored
    .second-self.local.json so dev/test automation can exercise the
    full write→read cycle without touching the OS keyring.

    Returns the store name used ("keyring" or "local").
    """
    missing = [k for k in TOKEN_REQUIRED_KEYS if k not in token]
    if missing:
        raise ValueError(f"token record missing required keys: {', '.join(missing)}")
    payload = json.dumps(token)
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USER, payload)
        return "keyring"
    except (KeyringError, RuntimeError):
        # JUNIOR: keyring failed (e.g. no backend in CI) — keep the token
        # in the git-ignored local JSON instead of losing it.
        path = _local_token_path(base_dir)
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except (OSError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        data[LOCAL_TOKEN_KEY] = token
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return "local"


# ---------------------------------------------------------------------------
# Snapshot cache (Phase 2)
# ---------------------------------------------------------------------------

def write_snapshot(base_dir: Path, snapshot: dict[str, Any]) -> Path:
    """Write the event snapshot JSON to the cache directory."""
    period = snapshot.get("period", "today")
    path = _snapshot_path(base_dir, period)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def read_snapshot(base_dir: Path, period: str) -> dict[str, Any] | None:
    """Read the cached snapshot for a period, or None if absent/unreadable."""
    path = _snapshot_path(base_dir, period)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def snapshot_age_hours(snapshot: dict[str, Any]) -> float:
    """Return the snapshot's age in hours based on its fetched_at stamp."""
    raw = snapshot.get("fetched_at")
    if not raw:
        raise ValueError("snapshot has no fetched_at stamp")
    # TECHNICAL: fromisoformat accepts "Z" only from Python 3.11+, but we
    # normalize explicitly so the parse works on any ISO-8601 UTC stamp.
    fetched = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - fetched).total_seconds() / 3600.0


def is_stale(snapshot: dict[str, Any]) -> bool:
    """Return True when the snapshot is older than the period's threshold.

    today → 6h, week → 12h. A snapshot with no parsable timestamp is
    always stale: freshness must be provable, never assumed.
    """
    try:
        age = snapshot_age_hours(snapshot)
    except ValueError:
        return True
    threshold = STALE_TODAY_HOURS if snapshot.get("period") == "today" else STALE_WEEK_HOURS
    return age > threshold


# ---------------------------------------------------------------------------
# Calendar client (Phase 2 — mocked; Phase 4 — live)
# ---------------------------------------------------------------------------

def _now_shanghai() -> datetime:
    """Current time in the calendar timezone (seam for window tests)."""
    return datetime.now(ZoneInfo(CALENDAR_TIMEZONE))


def _period_window(period: str, now: datetime) -> tuple[datetime, datetime]:
    """Return the UTC [start, end) window for today or this week.

    TECHNICAL: windows are computed in Asia/Shanghai, then converted to
    UTC for the API. "today" = the local calendar day; "week" = the ISO
    week (Monday 00:00 local → next Monday 00:00 local).
    """
    if period not in ("today", "week"):
        raise ValueError(f"unknown period: {period}")
    local_now = now.astimezone(ZoneInfo(CALENDAR_TIMEZONE))
    start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        # JUNIOR: weekday() → Monday=0 … Sunday=6; step back to Monday.
        start -= timedelta(days=local_now.weekday())
    days = 7 if period == "week" else 1
    end = (start + timedelta(days=days)).astimezone(timezone.utc)
    return start.astimezone(timezone.utc), end


def _rfc3339(dt: datetime) -> str:
    """Format an aware datetime as RFC3339 UTC (Google API style)."""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_event(item: dict[str, Any]) -> dict[str, Any]:
    """Map a Google Calendar API event into the snapshot event shape."""
    start = item.get("start") or {}
    end = item.get("end") or {}
    return {
        "id": item.get("id", ""),
        "summary": item.get("summary") or "(no title)",
        "start": start.get("dateTime") or start.get("date", ""),
        "end": end.get("dateTime") or end.get("date", ""),
        "all_day": "date" in start,  # date-only start ⇒ all-day event
        "status": item.get("status", "confirmed"),
        "recurring": "recurringEventId" in item or "recurrence" in item,
        "location": item.get("location"),
        "hangout_link": item.get("hangoutLink"),
    }


def build_service(base_dir: Path) -> Any:
    """Build an authorized googleapiclient service for calendar.readonly."""
    token, _store = load_token(base_dir)
    creds = Credentials(
        token=None,
        refresh_token=token.get("refresh_token"),
        client_id=token.get("client_id"),
        client_secret=token.get("client_secret"),
        token_uri=token.get("token_uri"),
        scopes=token.get("scopes") or [OAUTH_SCOPE],
    )
    # TECHNICAL: cache_discovery=False avoids writing discovery docs to
    # the user's cache; tests patch this `build` symbol — no network.
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _fetch_live(base_dir: Path, period: str) -> dict[str, Any]:
    """Run the live API query for a period; return the snapshot dict.

    Raises on any failure — callers decide whether to fall back to cache.
    """
    service = build_service(base_dir)
    start, end = _period_window(period, _now_shanghai())
    result = (
        service.events()
        .list(
            calendarId=DEFAULT_CALENDAR_ID,
            timeMin=_rfc3339(start),
            timeMax=_rfc3339(end),
            singleEvents=True,
            orderBy="startTime",
            maxResults=250,
        )
        .execute()
    )
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "period": period,
        "calendar_id": DEFAULT_CALENDAR_ID,
        "timezone": CALENDAR_TIMEZONE,
        "events": [_normalize_event(item) for item in result.get("items", [])],
    }


def fetch_events(base_dir: Path, period: str) -> tuple[dict[str, Any], bool]:
    """Fetch today's or this week's events; return (snapshot, from_cache).

    Live fetch first; on any failure (offline, expired/revoked token,
    API error) fall back to the cached snapshot. Staleness is reported
    explicitly by the caller — never silently old (PRD requirement).
    """
    try:
        snapshot = _fetch_live(base_dir, period)
    except Exception:
        # TECHNICAL: deliberately broad — any live-path failure degrades
        # to the snapshot instead of crashing the briefing flow.
        cached = read_snapshot(base_dir, period)
        if cached is not None:
            return cached, True
        raise
    write_snapshot(base_dir, snapshot)
    return snapshot, False


# ---------------------------------------------------------------------------
# OAuth flow (Phase 2 — mocked; Phase 3 — real)
# ---------------------------------------------------------------------------

def run_auth(base_dir: Path) -> tuple[dict[str, Any], str]:
    """Run the installed-app OAuth flow and persist the resulting token.

    Returns (token_record, store_name). Phase 3 runs this against the
    real Google consent screen; tests mock InstalledAppFlow.
    """
    creds_path = _credentials_path(base_dir)
    if not creds_path.exists():
        raise FileNotFoundError(
            f"credentials.json not found at {creds_path} — complete the Phase 3 setup first"
        )
    # TECHNICAL: the installed-app flow starts a short-lived local HTTP
    # server and opens the browser; the refresh token only ever lands in
    # save_token (keyring → local fallback), never in a tracked file.
    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), scopes=[OAUTH_SCOPE])
    # TECHNICAL: prompt="consent" forces Google to (re)issue a refresh
    # token — on a repeat visit with an existing grant, the consent
    # screen can be skipped and the response would carry no
    # refresh_token, which this project's storage layer depends on.
    creds = flow.run_local_server(port=0, prompt="consent")
    record = {
        "refresh_token": creds.refresh_token,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        # TECHNICAL: token_uri via getattr — the google-auth typings do
        # not expose it on every Credentials variant, but the value is
        # always present for user-consent flows.
        "token_uri": getattr(creds, "token_uri", None),
        "scopes": [OAUTH_SCOPE],
    }
    store = save_token(base_dir, record)
    return record, store


# ---------------------------------------------------------------------------
# Doctor check (Phase 2 — CLI side; Phase 5 — echo-doctor integration)
# ---------------------------------------------------------------------------

def run_doctor_check(base_dir: Path) -> dict[str, str]:
    """Report connector health: token present, credentials.json exists,
    snapshot readable. Shape mirrors echo-doctor checks:
    {"check": "calendar-connector", "status": OK|WARN|FAIL, "detail": str}
    """
    store = "keyring"  # reassigned by load_token on success; keeps Pylance happy
    try:
        _token, store = load_token(base_dir)
        token_note = f"token present ({store})"
        token_ok = True
    except FileNotFoundError:
        token_note = "no token — run `auth`"
        token_ok = False

    creds_ok = _credentials_path(base_dir).exists()
    creds_note = (
        "credentials.json present" if creds_ok
        else "credentials.json missing (needed for `auth`)"
    )

    snapshot = read_snapshot(base_dir, "today")
    if snapshot is None:
        snap_note = "no cached snapshot"
    else:
        try:
            age = snapshot_age_hours(snapshot)
            flag = " (STALE)" if is_stale(snapshot) else ""
            snap_note = f"snapshot age {age:.1f}h{flag}"
        except ValueError:
            snap_note = "snapshot unreadable (no timestamp)"

    if not token_ok:
        status = FAIL
    elif store == "local":
        # Token held only by the dev fallback store — works, but flag it.
        status = WARN
    else:
        status = OK
    return {"check": "calendar-connector", "status": status, "detail": f"{token_note}; {creds_note}; {snap_note}"}


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _render_text(snapshot: dict[str, Any], stale_notice: str | None) -> str:
    """Render a snapshot as human-readable text lines."""
    events = snapshot.get("events", [])
    lines = [
        f"Calendar ({snapshot.get('period', '?')}, {snapshot.get('timezone', '?')}): "
        f"{len(events)} event(s)"
    ]
    if stale_notice:
        # PRD: stale snapshots are flagged in output, never silent.
        lines.append(f"NOTE: {stale_notice}")
    if not events:
        lines.append("  (no events)")
    for ev in events:
        when = f"{ev.get('start', '')} → {ev.get('end', '')}"
        marks = []
        if ev.get("all_day"):
            marks.append("all-day")
        if ev.get("status") == "cancelled":
            marks.append("cancelled")
        if ev.get("recurring"):
            marks.append("recurring")
        suffix = f" [{', '.join(marks)}]" if marks else ""
        lines.append(f"  - {ev.get('summary', '?')}  {when}{suffix}")
        if ev.get("location"):
            lines.append(f"      at: {ev['location']}")
    return "\n".join(lines)


def _stale_notice(snapshot: dict[str, Any]) -> str | None:
    """Human-readable staleness notice for a cached snapshot, or None."""
    try:
        age = snapshot_age_hours(snapshot)
    except ValueError:
        return "cached snapshot has no timestamp — treating as stale"
    if not is_stale(snapshot):
        return None
    return f"cached snapshot is {age:.1f}h old (threshold {STALE_TODAY_HOURS if snapshot.get('period') == 'today' else STALE_WEEK_HOURS}h)"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_auth(args: argparse.Namespace) -> int:
    """Run the OAuth flow and store the token."""
    base = Path(args.base_dir) if args.base_dir else _default_base_dir()
    _record, store = run_auth(base)
    print(f"Token stored in: {store}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    """Fetch events for the requested period and print them.

    Exit code 1 = degraded (served from the cache), 0 = live success.
    """
    base = Path(args.base_dir) if args.base_dir else _default_base_dir()
    snapshot, from_cache = fetch_events(base, args.period)
    stale = _stale_notice(snapshot) if from_cache else None
    if args.json:
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
    else:
        print(_render_text(snapshot, stale_notice=stale))
    return 1 if from_cache else 0


def cmd_cache(args: argparse.Namespace) -> int:
    """Refresh the local snapshot cache from live data."""
    base = Path(args.base_dir) if args.base_dir else _default_base_dir()
    if not args.refresh:
        print("error: nothing to do — pass --refresh", file=sys.stderr)
        return 2
    for period in ("today", "week"):
        snapshot, _from_cache = fetch_events(base, period)
        print(f"Refreshed {period}: {len(snapshot.get('events', []))} event(s)")
    return 0


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
    except (OSError, ValueError, KeyError) as exc:
        # OSError covers FileNotFoundError/PermissionError from token,
        # credentials, and snapshot paths; ValueError covers malformed
        # token records; KeyError covers a corrupt credentials.json.
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())