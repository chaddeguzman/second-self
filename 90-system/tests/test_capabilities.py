"""Tests for ECHO capability status reporting."""

import json

from second_self.capabilities import build_guide_report, build_registry, main


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


def test_capability_registry_explains_boundary_prerequisites_and_fallback():
    registry = {item.name: item for item in build_registry()}

    gmail = registry["gmail"].as_dict()
    assert gmail["boundary"] == "external_provider_when_enabled"
    assert gmail["prerequisites"] == ("DOC-002 contract", "explicit enablement")
    assert gmail["approval"] == "explicit_request"
    assert gmail["fallback"] == "remains disabled; local recall is unaffected"
    assert gmail["examples"] == ("search Gmail metadata",)


def test_capability_guide_report_has_state_legend_and_safe_next_steps():
    report = build_guide_report()

    assert report["version"] == "capability-help/v1"
    assert report["state_legend"]["degraded"]["meaning"]
    gmail = next(item for item in report["capabilities"] if item["name"] == "gmail")
    assert gmail["state"] == "disabled"
    assert gmail["next_step"] == "wait for an approved adapter and explicit enablement"


def test_capability_guide_cli_is_human_readable(capsys):
    assert main(["--guide"]) == 0
    output = capsys.readouterr().out

    assert "ECHO capability guide" in output
    assert "State meanings" in output
    assert "gmail: disabled" in output
    assert "Next: wait for an approved adapter and explicit enablement" in output


def test_capability_guide_cli_is_machine_readable(capsys):
    assert main(["--guide", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["version"] == "capability-help/v1"
    assert "state_legend" in payload
    assert any(item["name"] == "drive" for item in payload["capabilities"])
