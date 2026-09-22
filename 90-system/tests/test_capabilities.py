"""Tests for ECHO capability status reporting."""

import json

from second_self.capabilities import build_registry, main


def test_future_external_connectors_are_explicitly_disabled():
    registry = {item.name: item for item in build_registry()}
    assert registry["gmail"].state == "disabled"
    assert registry["drive"].state == "disabled"
    assert registry["gmail"].reason_code == "future_connector"
    assert registry["drive"].reason_code == "future_connector"


def test_registry_has_stable_states_and_no_paths():
    payload = [item.as_dict() for item in build_registry()]
    assert {item["state"] for item in payload} <= {
        "planned", "disabled", "available", "degraded"
    }
    serialized = json.dumps(payload)
    assert "C:\\Users" not in serialized
    assert "token" not in serialized.casefold()


def test_capability_cli_is_machine_readable(capsys):
    assert main(["--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["version"] == "capabilities/v1"
    assert any(item["name"] == "gmail" for item in payload["capabilities"])
