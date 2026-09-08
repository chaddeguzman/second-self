"""Tests for echo-calendar (ECHO Google Calendar Connector).

Phase 2: full mocked test suite — token storage (keyring primary +
local fallback, Option C), snapshot cache, fetch/fallback, timezone
window edges, event normalization, auth flow, doctor-check, CLI
behavior. No network in any test, ever: the Google API client `build`
and the OAuth `InstalledAppFlow` are patched at the module boundary.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

# ---------------------------------------------------------------------------
# Module loading (subprocess-free import of the standalone script)
# ---------------------------------------------------------------------------

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / ".echo" / "scripts" / "echo-calendar.py"
)

spec = importlib.util.spec_from_file_location("echo_calendar", SCRIPT)
assert spec is not None and spec.loader is not None
echo_calendar = importlib.util.module_from_spec(spec)
sys.modules["echo_calendar"] = echo_calendar
spec.loader.exec_module(echo_calendar)


# ---------------------------------------------------------------------------
# Shared fixtures: isolated base dir + fake keyring (never touches the OS
# Credential Manager — Option C's local fallback is exercised by making
# the fake backend fail on demand)
# ---------------------------------------------------------------------------

SHANGHAI = ZoneInfo("Asia/Shanghai")

TOKEN = {
    "refresh_token": "refresh-abc",
    "client_id": "client-id.apps.googleusercontent.com",
    "client_secret": "client-secret",
    "token_uri": "https://oauth2.googleapis.com/token",
    "scopes": ["https://www.googleapis.com/auth/calendar.readonly"],
}


@pytest.fixture()
def sandbox(tmp_path: Path) -> Path:
    """Model <repo>/90-system/.echo so all derived paths stay in tmp."""
    base = tmp_path / "90-system" / ".echo"
    (base / "scripts").mkdir(parents=True)
    return base


class FakeKeyring:
    """In-memory stand-in for the OS keyring backend."""

    def __init__(self) -> None:
        self.store: dict[tuple[str, str], str] = {}
        self.fail = False

    def get_password(self, service: str, user: str) -> str | None:
        if self.fail:
            raise echo_calendar.KeyringError("backend unavailable")
        return self.store.get((service, user))

    def set_password(self, service: str, user: str, value: str) -> None:
        if self.fail:
            raise echo_calendar.KeyringError("backend unavailable")
        self.store[(service, user)] = value


@pytest.fixture()
def fake_keyring(monkeypatch: pytest.MonkeyPatch) -> FakeKeyring:
    fk = FakeKeyring()
    monkeypatch.setattr(echo_calendar.keyring, "get_password", fk.get_password)
    monkeypatch.setattr(echo_calendar.keyring, "set_password", fk.set_password)
    return fk


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    """Scaffold invariants that later phases depend on."""

    def test_timezone_is_shanghai(self) -> None:
        assert echo_calendar.CALENDAR_TIMEZONE == "Asia/Shanghai"

    def test_scope_is_readonly(self) -> None:
        assert echo_calendar.OAUTH_SCOPE.endswith("calendar.readonly")

    def test_keyring_service_name(self) -> None:
        assert echo_calendar.KEYRING_SERVICE == "second-self-echo-calendar"

    def test_staleness_thresholds(self) -> None:
        assert echo_calendar.STALE_TODAY_HOURS == 6
        assert echo_calendar.STALE_WEEK_HOURS == 12


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

class TestPaths:
    """Path resolution used by later phases."""

    def test_credentials_path(self, tmp_path: Path) -> None:
        expected = tmp_path / "scripts" / "credentials.json"
        assert echo_calendar._credentials_path(tmp_path) == expected

    def test_cache_dir(self, tmp_path: Path) -> None:
        # base_dir models the .echo dir: <root>/90-system/.echo
        echo_dir = tmp_path / "90-system" / ".echo"
        expected = tmp_path / ".second-self-cache" / "calendar"
        assert echo_calendar._cache_dir(echo_dir) == expected

    def test_local_token_path(self, tmp_path: Path) -> None:
        echo_dir = tmp_path / "90-system" / ".echo"
        expected = tmp_path / ".second-self.local.json"
        assert echo_calendar._local_token_path(echo_dir) == expected

    def test_snapshot_paths_split_by_period(self, tmp_path: Path) -> None:
        echo_dir = tmp_path / "90-system" / ".echo"
        cache = tmp_path / ".second-self-cache" / "calendar"
        assert echo_calendar._snapshot_path(echo_dir, "today") == cache / "snapshot-today.json"
        assert echo_calendar._snapshot_path(echo_dir, "week") == cache / "snapshot-week.json"


# ---------------------------------------------------------------------------
# Token storage — Option C: keyring primary (read + write), local JSON
# fallback; the fallback is used only when keyring returns nothing/errors
# ---------------------------------------------------------------------------

class TestTokenStore:
    def test_save_and_load_roundtrip_keyring(
        self, sandbox: Path, fake_keyring: FakeKeyring
    ) -> None:
        assert echo_calendar.save_token(sandbox, TOKEN) == "keyring"
        token, store = echo_calendar.load_token(sandbox)
        assert token == TOKEN
        assert store == "keyring"

    def test_load_prefers_keyring_over_local(
        self, sandbox: Path, fake_keyring: FakeKeyring, tmp_path: Path
    ) -> None:
        fake_keyring.set_password(
            echo_calendar.KEYRING_SERVICE, echo_calendar.KEYRING_USER, json.dumps(TOKEN)
        )
        local = echo_calendar._local_token_path(sandbox)
        local.parent.mkdir(parents=True, exist_ok=True)
        stale = dict(TOKEN, refresh_token="older")
        local.write_text(json.dumps({echo_calendar.LOCAL_TOKEN_KEY: stale}), encoding="utf-8")
        token, store = echo_calendar.load_token(sandbox)
        assert store == "keyring"
        assert token["refresh_token"] == "refresh-abc"

    def test_load_falls_back_to_local_when_keyring_empty(
        self, sandbox: Path, fake_keyring: FakeKeyring, tmp_path: Path
    ) -> None:
        local = echo_calendar._local_token_path(sandbox)
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(json.dumps({echo_calendar.LOCAL_TOKEN_KEY: TOKEN}), encoding="utf-8")
        token, store = echo_calendar.load_token(sandbox)
        assert store == "local"
        assert token == TOKEN

    def test_load_falls_back_when_keyring_backend_errors(
        self, sandbox: Path, fake_keyring: FakeKeyring, tmp_path: Path
    ) -> None:
        fake_keyring.fail = True
        local = echo_calendar._local_token_path(sandbox)
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(json.dumps({echo_calendar.LOCAL_TOKEN_KEY: TOKEN}), encoding="utf-8")
        _token, store = echo_calendar.load_token(sandbox)
        assert store == "local"

    def test_load_raises_when_neither_store_has_token(
        self, sandbox: Path, fake_keyring: FakeKeyring
    ) -> None:
        with pytest.raises(FileNotFoundError):
            echo_calendar.load_token(sandbox)

    def test_load_falls_back_on_corrupt_keyring_payload(
        self, sandbox: Path, fake_keyring: FakeKeyring, tmp_path: Path
    ) -> None:
        fake_keyring.set_password(
            echo_calendar.KEYRING_SERVICE, echo_calendar.KEYRING_USER, "{not json"
        )
        local = echo_calendar._local_token_path(sandbox)
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(json.dumps({echo_calendar.LOCAL_TOKEN_KEY: TOKEN}), encoding="utf-8")
        _token, store = echo_calendar.load_token(sandbox)
        assert store == "local"

    def test_save_falls_back_to_local_when_keyring_fails(
        self, sandbox: Path, fake_keyring: FakeKeyring, tmp_path: Path
    ) -> None:
        fake_keyring.fail = True
        store = echo_calendar.save_token(sandbox, TOKEN)
        assert store == "local"
        # Full dev/test cycle without touching the OS keyring:
        token, read_store = echo_calendar.load_token(sandbox)
        assert read_store == "local"
        assert token == TOKEN

    def test_save_rejects_incomplete_token(
        self, sandbox: Path, fake_keyring: FakeKeyring
    ) -> None:
        with pytest.raises(ValueError):
            echo_calendar.save_token(sandbox, {"refresh_token": "x"})

    def test_save_overwrites_existing_keyring_token(
        self, sandbox: Path, fake_keyring: FakeKeyring
    ) -> None:
        echo_calendar.save_token(sandbox, TOKEN)
        rotated = dict(TOKEN, refresh_token="rotated")
        echo_calendar.save_token(sandbox, rotated)
        token, _store = echo_calendar.load_token(sandbox)
        assert token["refresh_token"] == "rotated"


# ---------------------------------------------------------------------------
# Snapshot cache
# ---------------------------------------------------------------------------

def _snapshot(period: str, age_hours: float | None = 0.0) -> dict:
    snap: dict = {"period": period, "events": [], "timezone": "Asia/Shanghai"}
    if age_hours is not None:
        fetched = datetime.now(timezone.utc) - timedelta(hours=age_hours)
        snap["fetched_at"] = fetched.isoformat()
    return snap


class TestSnapshotCache:
    def test_write_and_read_roundtrip(self, sandbox: Path) -> None:
        path = echo_calendar.write_snapshot(sandbox, _snapshot("today"))
        assert path.exists()
        assert echo_calendar.read_snapshot(sandbox, "today") is not None

    def test_write_routes_week_to_week_file(self, sandbox: Path) -> None:
        path = echo_calendar.write_snapshot(sandbox, _snapshot("week"))
        assert path.name == "snapshot-week.json"

    def test_read_missing_returns_none(self, sandbox: Path) -> None:
        assert echo_calendar.read_snapshot(sandbox, "today") is None

    def test_read_corrupt_returns_none(self, sandbox: Path) -> None:
        echo_calendar._cache_dir(sandbox).mkdir(parents=True, exist_ok=True)
        (echo_calendar._cache_dir(sandbox) / "snapshot-today.json").write_text("{bad", encoding="utf-8")
        assert echo_calendar.read_snapshot(sandbox, "today") is None

    def test_age_recent_is_small(self, sandbox: Path) -> None:
        assert echo_calendar.snapshot_age_hours(_snapshot("today", 0.5)) == pytest.approx(0.5, abs=0.01)

    def test_age_missing_stamp_raises(self) -> None:
        with pytest.raises(ValueError):
            echo_calendar.snapshot_age_hours({"period": "today"})

    def test_stale_today_over_6h(self) -> None:
        assert echo_calendar.is_stale(_snapshot("today", 7.0)) is True
        assert echo_calendar.is_stale(_snapshot("today", 5.0)) is False

    def test_stale_week_over_12h(self) -> None:
        assert echo_calendar.is_stale(_snapshot("week", 13.0)) is True
        assert echo_calendar.is_stale(_snapshot("week", 11.0)) is False

    def test_missing_timestamp_is_always_stale(self) -> None:
        # Freshness must be provable — never assumed.
        assert echo_calendar.is_stale({"period": "today", "events": []}) is True


# ---------------------------------------------------------------------------
# Timezone windows + event normalization (Asia/Shanghai edge cases)
# ---------------------------------------------------------------------------

class TestPeriodWindow:
    def test_today_window_late_evening(self) -> None:
        # 23:30 local on Tue 2026-09-08 → the same local day in UTC.
        now = datetime(2026, 9, 8, 23, 30, tzinfo=SHANGHAI)
        start, end = echo_calendar._period_window("today", now)
        assert start == datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)
        assert end == datetime(2026, 9, 8, 16, 0, tzinfo=timezone.utc)

    def test_today_window_just_after_midnight(self) -> None:
        # 00:10 local Wed → window starts at that same local midnight.
        now = datetime(2026, 9, 9, 0, 10, tzinfo=SHANGHAI)
        start, _end = echo_calendar._period_window("today", now)
        assert start == datetime(2026, 9, 8, 16, 0, tzinfo=timezone.utc)

    def test_week_window_runs_monday_to_monday(self) -> None:
        # Thursday 2026-09-10 → ISO week Mon 09-07 … Sun 09-13.
        now = datetime(2026, 9, 10, 15, 0, tzinfo=SHANGHAI)
        start, end = echo_calendar._period_window("week", now)
        assert start == datetime(2026, 9, 6, 16, 0, tzinfo=timezone.utc)
        assert end == datetime(2026, 9, 13, 16, 0, tzinfo=timezone.utc)

    def test_week_window_on_sunday_includes_full_week(self) -> None:
        now = datetime(2026, 9, 13, 20, 0, tzinfo=SHANGHAI)
        start, end = echo_calendar._period_window("week", now)
        assert start == datetime(2026, 9, 6, 16, 0, tzinfo=timezone.utc)
        assert end == datetime(2026, 9, 13, 16, 0, tzinfo=timezone.utc)

    def test_unknown_period_raises(self) -> None:
        with pytest.raises(ValueError):
            echo_calendar._period_window("month", datetime(2026, 9, 8, tzinfo=SHANGHAI))

    def test_event_at_2330_lands_inside_today_window(self) -> None:
        # The classic boundary: a 23:30 local event is 15:30Z — inside.
        now = datetime(2026, 9, 8, 12, 0, tzinfo=SHANGHAI)
        start, end = echo_calendar._period_window("today", now)
        event_utc = datetime(2026, 9, 8, 23, 30, tzinfo=SHANGHAI)
        assert start <= event_utc.astimezone(timezone.utc) < end


class TestNormalizeEvent:
    def test_timed_event(self) -> None:
        item = {
            "id": "e1",
            "summary": "Standup",
            "start": {"dateTime": "2026-09-08T09:30:00+08:00"},
            "end": {"dateTime": "2026-09-08T10:00:00+08:00"},
            "status": "confirmed",
            "location": "Room 4",
            "hangoutLink": "https://meet.example/x",
        }
        ev = echo_calendar._normalize_event(item)
        assert ev["all_day"] is False
        assert ev["start"].endswith("+08:00")
        assert ev["location"] == "Room 4"

    def test_all_day_event_uses_date(self) -> None:
        item = {
            "id": "e2",
            "summary": "Holiday",
            "start": {"date": "2026-09-08"},
            "end": {"date": "2026-09-09"},
        }
        ev = echo_calendar._normalize_event(item)
        assert ev["all_day"] is True
        assert ev["start"] == "2026-09-08"

    def test_cancelled_and_recurring_flags(self) -> None:
        item = {
            "id": "e3",
            "summary": "Cancelled series",
            "start": {"dateTime": "2026-09-08T23:30:00+08:00"},
            "end": {"dateTime": "2026-09-08T23:59:00+08:00"},
            "status": "cancelled",
            "recurringEventId": "series-1",
        }
        ev = echo_calendar._normalize_event(item)
        assert ev["status"] == "cancelled"
        assert ev["recurring"] is True

    def test_missing_summary_gets_placeholder(self) -> None:
        item = {"id": "e4", "start": {"date": "2026-09-08"}, "end": {"date": "2026-09-09"}}
        ev = echo_calendar._normalize_event(item)
        assert ev["summary"] == "(no title)"


class TestRfc3339:
    def test_formats_utc_z(self) -> None:
        dt = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)
        assert echo_calendar._rfc3339(dt) == "2026-09-07T16:00:00Z"

    def test_converts_shanghai_input(self) -> None:
        dt = datetime(2026, 9, 8, 0, 0, tzinfo=SHANGHAI)
        assert echo_calendar._rfc3339(dt) == "2026-09-07T16:00:00Z"


# ---------------------------------------------------------------------------
# Fetch + fallback (service mocked at the module `build` boundary)
# ---------------------------------------------------------------------------

class FakeService:
    """Mimics the googleapiclient events().list().execute() chain."""

    def __init__(self, items: list[dict] | Exception) -> None:
        self._items = items
        self.list_kwargs: dict = {}

    def events(self) -> "FakeService":
        return self

    def list(self, **kwargs: object) -> "FakeService":
        self.list_kwargs = kwargs
        return self

    def execute(self) -> dict:
        if isinstance(self._items, Exception):
            raise self._items
        return {"items": self._items}


class TestFetchEvents:
    def test_live_success_normalizes_and_caches(
        self, sandbox: Path, fake_keyring: FakeKeyring, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        echo_calendar.save_token(sandbox, TOKEN)
        service = FakeService([
            {
                "id": "e1",
                "summary": "Review",
                "start": {"dateTime": "2026-09-08T14:00:00+08:00"},
                "end": {"dateTime": "2026-09-08T15:00:00+08:00"},
            }
        ])
        monkeypatch.setattr(echo_calendar, "build", lambda *a, **k: service)
        snapshot, from_cache = echo_calendar.fetch_events(sandbox, "today")
        assert from_cache is False
        assert snapshot["events"][0]["summary"] == "Review"
        assert snapshot["period"] == "today"
        assert snapshot["timezone"] == "Asia/Shanghai"
        # Query was read-only, scoped to the window, and ordered.
        assert service.list_kwargs["calendarId"] == "primary"
        assert service.list_kwargs["singleEvents"] is True
        assert service.list_kwargs["orderBy"] == "startTime"
        assert service.list_kwargs["timeMin"].endswith("Z")
        # Live result was written to the snapshot cache.
        assert echo_calendar.read_snapshot(sandbox, "today") is not None

    def test_live_failure_falls_back_to_cache(
        self, sandbox: Path, fake_keyring: FakeKeyring, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        echo_calendar.save_token(sandbox, TOKEN)
        echo_calendar.write_snapshot(sandbox, _snapshot("today", age_hours=1.0))
        monkeypatch.setattr(echo_calendar, "build", lambda *a, **k: FakeService(OSError("offline")))
        snapshot, from_cache = echo_calendar.fetch_events(sandbox, "today")
        assert from_cache is True
        assert snapshot["period"] == "today"

    def test_live_failure_with_no_cache_raises(
        self, sandbox: Path, fake_keyring: FakeKeyring, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        echo_calendar.save_token(sandbox, TOKEN)
        monkeypatch.setattr(echo_calendar, "build", lambda *a, **k: FakeService(OSError("offline")))
        with pytest.raises(OSError):
            echo_calendar.fetch_events(sandbox, "today")

    def test_missing_token_with_cache_still_serves(
        self, sandbox: Path, fake_keyring: FakeKeyring, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Offline scenario with no token at all: snapshot still works.
        echo_calendar.write_snapshot(sandbox, _snapshot("week", age_hours=2.0))
        monkeypatch.setattr(
            echo_calendar, "build", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("no token"))
        )
        snapshot, from_cache = echo_calendar.fetch_events(sandbox, "week")
        assert from_cache is True


# ---------------------------------------------------------------------------
# OAuth flow (InstalledAppFlow mocked — no browser, no network)
# ---------------------------------------------------------------------------

class FakeCreds:
    refresh_token = "refresh-xyz"
    client_id = TOKEN["client_id"]
    client_secret = TOKEN["client_secret"]
    token_uri = TOKEN["token_uri"]


class FakeFlow:
    last_scopes: list[str] = []
    last_run_kwargs: dict = {}

    def __init__(self) -> None:
        self.ran = False

    @classmethod
    def from_client_secrets_file(cls, path: str, scopes: list[str]) -> "FakeFlow":
        FakeFlow.last_scopes = scopes
        return cls()

    def run_local_server(self, port: int = 0, **kwargs: object) -> FakeCreds:
        self.ran = True
        FakeFlow.last_run_kwargs = {"port": port, **kwargs}
        return FakeCreds()


class TestRunAuth:
    def test_missing_credentials_raises(
        self, sandbox: Path, fake_keyring: FakeKeyring
    ) -> None:
        with pytest.raises(FileNotFoundError):
            echo_calendar.run_auth(sandbox)

    def test_success_stores_token_in_keyring(
        self, sandbox: Path, fake_keyring: FakeKeyring, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (echo_calendar._credentials_path(sandbox)).write_text("{}", encoding="utf-8")
        monkeypatch.setattr(echo_calendar, "InstalledAppFlow", FakeFlow)
        record, store = echo_calendar.run_auth(sandbox)
        assert store == "keyring"
        assert record["refresh_token"] == "refresh-xyz"
        assert FakeFlow.last_scopes == [echo_calendar.OAUTH_SCOPE]
        # prompt="consent" guarantees Google re-issues the refresh token
        # on repeat visits (without it, a skipped consent screen returns
        # no refresh_token and the storage layer would persist a dud).
        assert FakeFlow.last_run_kwargs.get("prompt") == "consent"
        token, read_store = echo_calendar.load_token(sandbox)
        assert read_store == "keyring"
        assert token["client_id"] == TOKEN["client_id"]

    def test_success_falls_back_to_local_when_keyring_fails(
        self, sandbox: Path, fake_keyring: FakeKeyring, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_keyring.fail = True
        (echo_calendar._credentials_path(sandbox)).write_text("{}", encoding="utf-8")
        monkeypatch.setattr(echo_calendar, "InstalledAppFlow", FakeFlow)
        _record, store = echo_calendar.run_auth(sandbox)
        assert store == "local"


# ---------------------------------------------------------------------------
# Doctor check
# ---------------------------------------------------------------------------

class TestDoctorCheck:
    def test_fail_when_no_token_anywhere(
        self, sandbox: Path, fake_keyring: FakeKeyring
    ) -> None:
        result = echo_calendar.run_doctor_check(sandbox)
        assert result["check"] == "calendar-connector"
        assert result["status"] == echo_calendar.FAIL

    def test_ok_with_keyring_token(
        self, sandbox: Path, fake_keyring: FakeKeyring
    ) -> None:
        echo_calendar.save_token(sandbox, TOKEN)
        result = echo_calendar.run_doctor_check(sandbox)
        assert result["status"] == echo_calendar.OK
        assert "keyring" in result["detail"]

    def test_warn_with_local_only_token(
        self, sandbox: Path, fake_keyring: FakeKeyring, tmp_path: Path
    ) -> None:
        fake_keyring.fail = True
        echo_calendar.save_token(sandbox, TOKEN)
        result = echo_calendar.run_doctor_check(sandbox)
        assert result["status"] == echo_calendar.WARN
        assert "local" in result["detail"]

    def test_reports_missing_credentials_and_snapshot(
        self, sandbox: Path, fake_keyring: FakeKeyring
    ) -> None:
        echo_calendar.save_token(sandbox, TOKEN)
        result = echo_calendar.run_doctor_check(sandbox)
        assert "credentials.json missing" in result["detail"]
        assert "no cached snapshot" in result["detail"]

    def test_reports_stale_snapshot_explicitly(
        self, sandbox: Path, fake_keyring: FakeKeyring
    ) -> None:
        echo_calendar.save_token(sandbox, TOKEN)
        echo_calendar.write_snapshot(sandbox, _snapshot("today", age_hours=20.0))
        result = echo_calendar.run_doctor_check(sandbox)
        assert "STALE" in result["detail"]


# ---------------------------------------------------------------------------
# Output rendering + commands
# ---------------------------------------------------------------------------

class TestRenderText:
    def test_lists_events_with_marks(self) -> None:
        snap = {
            "period": "today",
            "timezone": "Asia/Shanghai",
            "events": [
                {"summary": "All-day thing", "start": "2026-09-08", "end": "2026-09-09",
                 "all_day": True, "status": "confirmed", "recurring": False},
                {"summary": "Late call", "start": "2026-09-08T23:30:00+08:00",
                 "end": "2026-09-08T23:59:00+08:00", "all_day": False,
                 "status": "cancelled", "recurring": True, "location": "Zoom"},
            ],
        }
        text = echo_calendar._render_text(snap, stale_notice=None)
        assert "2 event(s)" in text
        assert "[all-day]" in text
        assert "[cancelled, recurring]" in text
        assert "at: Zoom" in text
        assert "NOTE:" not in text

    def test_stale_notice_is_explicit(self) -> None:
        text = echo_calendar._render_text(
            {"period": "today", "timezone": "Asia/Shanghai", "events": []},
            stale_notice="cached snapshot is 9.0h old",
        )
        assert "NOTE: cached snapshot is 9.0h old" in text

    def test_empty_events_placeholder(self) -> None:
        text = echo_calendar._render_text(
            {"period": "week", "timezone": "Asia/Shanghai", "events": []}, None
        )
        assert "(no events)" in text


class TestCommands:
    def _args(self, argv: list[str]) -> argparse.Namespace:
        return echo_calendar.build_parser().parse_args(argv)

    def test_fetch_live_exits_zero(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(
            echo_calendar, "fetch_events",
            lambda b, p: ({"period": p, "timezone": "Asia/Shanghai", "events": []}, False),
        )
        args = self._args(["fetch", "--period", "today"])
        assert echo_calendar.cmd_fetch(args) == 0

    def test_fetch_cached_exits_one_with_notice(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        old = _snapshot("today", age_hours=9.0)
        monkeypatch.setattr(echo_calendar, "fetch_events", lambda b, p: (old, True))
        args = self._args(["fetch", "--period", "today"])
        assert echo_calendar.cmd_fetch(args) == 1
        assert "NOTE:" in capsys.readouterr().out

    def test_fetch_json_output(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(
            echo_calendar, "fetch_events",
            lambda b, p: ({"period": p, "events": []}, False),
        )
        args = self._args(["--json", "fetch", "--period", "week"])
        assert echo_calendar.cmd_fetch(args) == 0
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["period"] == "week"

    def test_cache_refresh_fetches_both_periods(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        seen: list[str] = []

        def fake_fetch(base: object, period: str) -> tuple[dict, bool]:
            seen.append(period)
            return {"period": period, "events": []}, False

        monkeypatch.setattr(echo_calendar, "fetch_events", fake_fetch)
        args = self._args(["cache", "--refresh"])
        assert echo_calendar.cmd_cache(args) == 0
        assert seen == ["today", "week"]

    def test_cache_without_refresh_is_usage_error(self, capsys: pytest.CaptureFixture) -> None:
        args = self._args(["cache"])
        assert echo_calendar.cmd_cache(args) == 2

    def test_doctor_prints_status_line(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(
            echo_calendar, "run_doctor_check",
            lambda b: {"check": "calendar-connector", "status": "OK", "detail": "fine"},
        )
        args = self._args(["doctor-check"])
        assert echo_calendar.cmd_doctor(args) == 0
        assert "[OK] calendar-connector: fine" in capsys.readouterr().out

    def test_auth_prints_store_name(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(echo_calendar, "run_auth", lambda b: ({}, "keyring"))
        args = self._args(["auth"])
        assert echo_calendar.cmd_auth(args) == 0
        assert "keyring" in capsys.readouterr().out

    def test_main_maps_errors_to_exit_2(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        def boom(base: object, period: str) -> tuple[dict, bool]:
            raise FileNotFoundError("no token")

        monkeypatch.setattr(echo_calendar, "fetch_events", boom)
        assert echo_calendar.main(["fetch", "--period", "today"]) == 2
        assert "error:" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# CLI shape
# ---------------------------------------------------------------------------

class TestParser:
    """The CLI exposes the four commands with the documented flags."""

    def test_parser_builds(self) -> None:
        parser = echo_calendar.build_parser()
        assert parser.prog == "echo-calendar"

    def test_fetch_requires_period(self) -> None:
        parser = echo_calendar.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["fetch"])

    def test_fetch_accepts_today_and_week(self) -> None:
        parser = echo_calendar.build_parser()
        args = parser.parse_args(["fetch", "--period", "today"])
        assert args.period == "today"
        args = parser.parse_args(["fetch", "--period", "week"])
        assert args.period == "week"

    def test_period_rejects_unknown(self) -> None:
        parser = echo_calendar.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["fetch", "--period", "month"])

    def test_cache_has_refresh_flag(self) -> None:
        parser = echo_calendar.build_parser()
        args = parser.parse_args(["cache", "--refresh"])
        assert args.refresh is True