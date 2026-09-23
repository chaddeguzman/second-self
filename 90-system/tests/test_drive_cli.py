"""Tests for explicit, redacted Drive CLI routes."""

import json

import second_self.cli as cli
from second_self.cli import main
from second_self.connectors import DriveAuthError


def test_drive_search_is_disabled_without_explicit_enablement(monkeypatch, capsys):
    monkeypatch.delenv("SECOND_SELF_DRIVE_ENABLED", raising=False)
    monkeypatch.setattr(
        cli,
        "DriveCredentialStore",
        lambda: (_ for _ in ()).throw(AssertionError("disabled search must not inspect keyring")),
    )

    assert main(["drive", "search", "name contains 'plan'", "--json"]) == 0

    output = capsys.readouterr()
    payload = json.loads(output.out)
    assert payload["kind"] == "drive"
    assert payload["state"] == "disabled"
    assert "credential" not in output.err.casefold()


def test_drive_search_rejects_out_of_range_limit(monkeypatch):
    monkeypatch.setenv("SECOND_SELF_DRIVE_ENABLED", "1")

    assert main(["drive", "search", "name contains 'plan'", "--limit", "101", "--json"]) == 2


def test_drive_auth_reports_safe_configuration_error(tmp_path, capsys):
    assert main(["drive", "auth", "--client-config", str(tmp_path / "missing.json")]) == 2

    output = capsys.readouterr()
    assert "configuration unavailable" in output.err
    assert str(tmp_path) not in output.err


def test_drive_search_json_does_not_expose_configuration(monkeypatch, capsys):
    monkeypatch.setenv("SECOND_SELF_DRIVE_ENABLED", "1")
    monkeypatch.setenv("SECOND_SELF_DRIVE_CLIENT_CONFIG", "C:/private/client.json")
    monkeypatch.setattr(
        cli,
        "_build_drive_service",
        lambda: (_ for _ in ()).throw(DriveAuthError("synthetic unavailable")),
    )

    assert main(["drive", "search", "name contains 'plan'", "--json"]) == 2

    output = capsys.readouterr()
    assert "C:/private/client.json" not in output.out
    assert "C:/private/client.json" not in output.err
