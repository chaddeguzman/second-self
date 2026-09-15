"""Tests for the provider-free ``second-self route`` diagnostic CLI."""

from __future__ import annotations

import json

import pytest

from second_self.cli import build_parser, main


def test_route_help_documents_required_dry_run(capsys):
    with pytest.raises(SystemExit) as help_exit:
        build_parser().parse_args(["route", "--help"])

    assert help_exit.value.code == 0
    help_text = capsys.readouterr().out
    assert "--operation" in help_text
    assert "--sensitivity" in help_text
    assert "--dry-run" in help_text
    assert "--json" in help_text


def test_route_requires_dry_run_marker(capsys):
    with pytest.raises(SystemExit) as parse_exit:
        build_parser().parse_args(
            ["route", "--operation", "summarize", "--sensitivity", "public"]
        )

    assert parse_exit.value.code == 2
    assert "--dry-run" in capsys.readouterr().err


def test_route_json_is_payload_free_and_provider_free(capsys):
    code = main(
        [
            "route",
            "--operation",
            "summarize",
            "--sensitivity",
            "sensitive",
            "--dry-run",
            "--json",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert code == 2
    assert output == {
        "outcome": "deny",
        "reason": "local_provider_unavailable",
        "provider": None,
        "explanation": "required local provider is unavailable",
    }
    assert "payload" not in output
    assert "origin" not in output


def test_route_prohibited_denies_before_provider(capsys):
    code = main(
        [
            "route",
            "--operation",
            "summarize",
            "--sensitivity",
            "prohibited",
            "--dry-run",
        ]
    )

    output = capsys.readouterr().out
    assert code == 2
    assert "route: DENY" in output
    assert "reason: prohibited_data" in output
    assert "provider: none" in output


def test_route_unknown_sensitivity_returns_redacted_denial(capsys):
    raw_input = "unknown-private-payload"

    code = main(
        [
            "route",
            "--operation",
            "summarize",
            "--sensitivity",
            raw_input,
            "--dry-run",
            "--json",
        ]
    )

    output = capsys.readouterr().out
    assert code == 2
    assert json.loads(output)["reason"] == "invalid_request"
    assert raw_input not in output
