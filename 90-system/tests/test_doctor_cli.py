"""Tests for the public ``second-self doctor`` command."""

from __future__ import annotations

import json

import pytest

from second_self.cli import _load_echo_health_registry, build_parser, main
from second_self.core.paths import REPO_ROOT
from second_self.health import FAIL, OK, WARN, HealthCheck, HealthRegistry, HealthResult


CHECK_NAMES = [
    "stable-block-files",
    "session-pointer",
    "staging-queue",
    "log-status-lines",
    "stale-wip",
    "session-filenames",
    "calendar-connector",
]


def _registry(*statuses: str) -> HealthRegistry:
    registry = HealthRegistry()
    for index, status in enumerate(statuses):
        name = f"check-{index}"
        registry.register(
            HealthCheck(
                name,
                lambda _fix, name=name, status=status: HealthResult(
                    name, status, "redacted detail"
                ),
            )
        )
    return registry


def _patch_doctor(
    monkeypatch: pytest.MonkeyPatch,
    registry: HealthRegistry,
) -> None:
    monkeypatch.setattr(
        "second_self.cli._load_echo_health_registry", lambda _root: registry
    )
    monkeypatch.setattr(
        "second_self.cli.build_system_health_registry", lambda _context: HealthRegistry()
    )


def test_parser_help_lists_doctor_and_only_public_doctor_flags(capsys):
    parser = build_parser()

    with pytest.raises(SystemExit) as help_exit:
        parser.parse_args(["doctor", "--help"])

    assert help_exit.value.code == 0
    help_text = capsys.readouterr().out
    assert "--strict" in help_text
    assert "--json" in help_text
    assert "--fix" not in help_text
    assert "--base-dir" not in help_text


@pytest.mark.parametrize("arguments", [["--fix"], ["--base-dir", "sandbox"]])
def test_public_doctor_rejects_standalone_maintenance_flags(arguments):
    with pytest.raises(SystemExit) as parse_exit:
        build_parser().parse_args(["doctor", *arguments])

    assert parse_exit.value.code == 2


def test_doctor_text_output_and_ok_exit(monkeypatch, capsys):
    _patch_doctor(monkeypatch, _registry(OK))

    code = main(["doctor"])

    assert code == 0
    assert capsys.readouterr().out.splitlines() == [
        "second-self doctor — system health check",
        "=" * 60,
        "[OK]   check-0              redacted detail",
        "-" * 60,
        "Summary: 1 OK, 0 WARN, 0 FAIL",
    ]


def test_doctor_json_uses_shared_shape(monkeypatch, capsys):
    _patch_doctor(monkeypatch, _registry(OK, WARN))

    code = main(["doctor", "--json"])

    assert code == 0
    assert json.loads(capsys.readouterr().out) == {
        "results": [
            {"check": "check-0", "status": OK, "detail": "redacted detail"},
            {"check": "check-1", "status": WARN, "detail": "redacted detail"},
        ]
    }


@pytest.mark.parametrize(
    ("arguments", "status", "expected"),
    [([], WARN, 0), (["--strict"], WARN, 1), ([], FAIL, 2), (["--strict"], FAIL, 2)],
)
def test_doctor_exit_semantics(monkeypatch, capsys, arguments, status, expected):
    _patch_doctor(monkeypatch, _registry(status))

    assert main(["doctor", *arguments]) == expected
    capsys.readouterr()


def test_doctor_loads_the_same_seven_check_registry_as_echo_doctor():
    registry = _load_echo_health_registry(REPO_ROOT)

    assert [check.name for check in registry] == CHECK_NAMES


def test_registry_loader_hides_underlying_path(monkeypatch, tmp_path):
    private_path = tmp_path / "private" / "plugin.py"
    script = tmp_path / "90-system" / ".echo" / "scripts" / "echo-doctor.py"
    script.parent.mkdir(parents=True)
    script.write_text("# synthetic adapter\n", encoding="utf-8")
    monkeypatch.setattr(
        "second_self.cli.importlib.util.spec_from_file_location",
        lambda *_args: (_ for _ in ()).throw(RuntimeError(f"broken {private_path}")),
    )

    with pytest.raises(RuntimeError) as error:
        _load_echo_health_registry(tmp_path)

    assert str(error.value) == "ECHO health registry could not be loaded."
    assert str(private_path) not in str(error.value)


def test_doctor_redacts_registry_load_error(monkeypatch, tmp_path, capsys):
    private_path = tmp_path / "private" / "secret.json"
    monkeypatch.setattr(
        "second_self.cli._load_echo_health_registry",
        lambda _root: (_ for _ in ()).throw(
            RuntimeError("ECHO health registry could not be loaded.")
        ),
    )

    code = main(["doctor"])

    captured = capsys.readouterr()
    assert code == 2
    assert str(private_path) not in captured.err
    assert "error:" in captured.err
