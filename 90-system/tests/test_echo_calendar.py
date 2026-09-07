"""Tests for echo-calendar (ECHO Google Calendar Connector).

Phase 1: scaffold tests only — verify the module shape (imports, CLI
parser, constants, stub behavior). Phase 2 adds the full mocked test
suite: token storage, snapshot cache, fetch/fallback, timezone edges,
CLI behavior. No network in any test, ever.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

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


# ---------------------------------------------------------------------------
# Phase 1 stubs — every logic entry point must refuse to run
# ---------------------------------------------------------------------------

class TestPhase1Stubs:
    """All logic stubs raise NotImplementedError (scaffold discipline)."""

    def test_load_token_stub(self, tmp_path: Path) -> None:
        with pytest.raises(NotImplementedError):
            echo_calendar.load_token(tmp_path)

    def test_save_token_stub(self, tmp_path: Path) -> None:
        with pytest.raises(NotImplementedError):
            echo_calendar.save_token(tmp_path, {})

    def test_write_snapshot_stub(self, tmp_path: Path) -> None:
        with pytest.raises(NotImplementedError):
            echo_calendar.write_snapshot(tmp_path, {})

    def test_read_snapshot_stub(self, tmp_path: Path) -> None:
        with pytest.raises(NotImplementedError):
            echo_calendar.read_snapshot(tmp_path)

    def test_snapshot_age_stub(self) -> None:
        with pytest.raises(NotImplementedError):
            echo_calendar.snapshot_age_hours({})

    def test_is_stale_stub(self) -> None:
        with pytest.raises(NotImplementedError):
            echo_calendar.is_stale({})

    def test_build_service_stub(self, tmp_path: Path) -> None:
        with pytest.raises(NotImplementedError):
            echo_calendar.build_service(tmp_path)

    def test_fetch_events_stub(self, tmp_path: Path) -> None:
        with pytest.raises(NotImplementedError):
            echo_calendar.fetch_events(tmp_path, "today")

    def test_run_auth_stub(self, tmp_path: Path) -> None:
        with pytest.raises(NotImplementedError):
            echo_calendar.run_auth(tmp_path)

    def test_run_doctor_check_stub(self, tmp_path: Path) -> None:
        with pytest.raises(NotImplementedError):
            echo_calendar.run_doctor_check(tmp_path)

    def test_render_text_stub(self) -> None:
        with pytest.raises(NotImplementedError):
            echo_calendar._render_text({}, stale_notice=None)


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