"""Tests for deterministic, synthetic-only evaluation execution and CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from second_self.cli import build_parser, main
from second_self.evaluation import (
    EvalAssertion,
    EvalCase,
    EvalCaseStatus,
    EvalFixture,
    EvalReason,
    EvalSuite,
    discover_suites,
    render_json,
    render_text,
    run_suite,
)


def evaluator(fixture):
    if fixture.get("error"):
        raise RuntimeError("raw private evaluator failure")
    return {"value": fixture.get("value")}


def case(
    case_id: str,
    *,
    value: str = "synthetic",
    expected: str = "synthetic",
    error: bool = False,
    fixture: EvalFixture | None = None,
) -> EvalCase:
    return EvalCase(
        case_id,
        fixture or EvalFixture(True, data={"value": value, "error": error}),
        evaluator,
        (EvalAssertion("value", expected),),
    )


def test_builtin_discovery_and_case_execution_are_stably_sorted():
    suites = discover_suites()

    assert [suite.name for suite in suites] == sorted(suite.name for suite in suites)
    smoke = next(suite for suite in suites if suite.name == "smoke")
    report = run_suite(smoke, private_roots=())
    assert [item.case_id for item in report.cases] == [
        "assertion-failure",
        "passing-case",
        "runner-error",
    ]
    assert [item.status for item in report.cases] == [
        EvalCaseStatus.FAIL,
        EvalCaseStatus.PASS,
        EvalCaseStatus.ERROR,
    ]
    assert report.metrics == {"total": 3, "passed": 1, "failed": 1, "errors": 1}


def test_same_suite_produces_byte_identical_text_and_json_reports():
    suite = EvalSuite("repeatable", (case("z-case"), case("a-case")))

    first = run_suite(suite, private_roots=())
    second = run_suite(suite, private_roots=())

    assert first == second
    assert render_json(first) == render_json(second)
    assert render_text(first) == render_text(second)


def test_case_error_is_redacted_and_does_not_stop_later_cases():
    suite = EvalSuite("isolated", (case("first", error=True), case("second")))

    report = run_suite(suite, private_roots=())

    assert report.cases[0].reason is EvalReason.RUNNER_ERROR
    assert report.cases[1].status is EvalCaseStatus.PASS
    assert "raw private" not in render_json(report)
    assert "raw private" not in render_text(report)


@pytest.mark.parametrize(
    "fixture",
    [
        EvalFixture(False, data={"value": "synthetic"}),
        EvalFixture(True),
        EvalFixture(True, data={}, path=Path("also-a-path.json")),
    ],
)
def test_invalid_fixture_contract_is_isolated(fixture):
    report = run_suite(
        EvalSuite("invalid", (case("bad", fixture=fixture),)), private_roots=()
    )

    assert report.cases[0].status is EvalCaseStatus.ERROR
    assert report.cases[0].reason is EvalReason.INVALID_FIXTURE


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        "[]",
        '{"synthetic": false, "data": {}}',
        '{"synthetic": true, "data": [], "extra": true}',
    ],
)
def test_invalid_file_fixture_schema_is_redacted(tmp_path, payload):
    fixture_path = tmp_path / "invalid.json"
    fixture_path.write_text(payload, encoding="utf-8")
    suite = EvalSuite(
        "invalid-file",
        (case("bad", fixture=EvalFixture(True, path=fixture_path)),),
    )

    report = run_suite(suite, private_roots=())

    assert report.cases[0].reason is EvalReason.INVALID_FIXTURE
    assert str(fixture_path) not in render_json(report)


def test_valid_file_fixture_requires_synthetic_marker(tmp_path):
    fixture_path = tmp_path / "synthetic.json"
    fixture_path.write_text(
        json.dumps({"synthetic": True, "data": {"value": "synthetic"}}),
        encoding="utf-8",
    )
    suite = EvalSuite(
        "file-fixture",
        (case("valid", fixture=EvalFixture(True, path=fixture_path)),),
    )

    assert run_suite(suite, private_roots=()).passed is True


def test_fixture_inside_private_root_is_rejected_without_path_or_read(tmp_path):
    private_root = tmp_path / "private-root"
    private_root.mkdir()
    fixture_path = private_root / "do-not-read.json"
    private_content = "raw-private-marker"
    fixture_path.write_text(private_content, encoding="utf-8")
    suite = EvalSuite(
        "private-fixture",
        (case("private", fixture=EvalFixture(True, path=fixture_path)),),
    )

    report = run_suite(suite, private_roots=(private_root,))
    output = render_json(report) + render_text(report)

    assert report.cases[0].reason is EvalReason.PRIVATE_FIXTURE_REJECTED
    assert str(private_root) not in output
    assert private_content not in output


def test_reports_exclude_fixture_expected_and_observed_values():
    secret = "synthetic-secret-value"
    report = run_suite(
        EvalSuite("redacted", (case("failure", value=secret, expected="other"),)),
        private_roots=(),
    )

    output = render_json(report) + render_text(report)
    assert secret not in output
    assert "other" not in output


def test_invalid_suite_registry_and_duplicate_cases_are_rejected():
    duplicate = case("duplicate")
    with pytest.raises(ValueError, match="case IDs must be unique"):
        EvalSuite("duplicates", (duplicate, duplicate))
    with pytest.raises(ValueError, match="suite names must be unique"):
        discover_suites(
            (
                EvalSuite("same", (case("one"),)),
                EvalSuite("same", (case("two"),)),
            )
        )


def test_private_root_boundary_is_required_and_validated():
    suite = EvalSuite("boundary", (case("one"),))
    with pytest.raises(TypeError):
        run_suite(suite)  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="private root boundary is invalid"):
        run_suite(suite, private_roots=("not-a-path",))  # type: ignore[arg-type]


def test_out_of_range_quality_metric_becomes_redacted_runner_error():
    def invalid_metric(_fixture):
        return {"value": "synthetic", "_metrics": {"quality": 1.5}}

    invalid = EvalCase(
        "invalid-metric",
        EvalFixture(True, data={"value": "synthetic"}),
        invalid_metric,
        (EvalAssertion("value", "synthetic"),),
    )
    report = run_suite(EvalSuite("metric-bounds", (invalid,)), private_roots=())

    assert report.cases[0].reason is EvalReason.RUNNER_ERROR
    assert report.cases[0].metrics == ()


def test_eval_help_and_list_behavior(capsys):
    with pytest.raises(SystemExit) as help_exit:
        build_parser().parse_args(["eval", "--help"])
    assert help_exit.value.code == 0
    assert "--json" in capsys.readouterr().out

    assert main(["eval"]) == 0
    assert "smoke" in capsys.readouterr().out
    assert main(["eval", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "version": "evaluation-suite-list/v1",
        "suites": ["recall", "smoke"],
    }


def test_eval_unknown_suite_is_redacted(capsys):
    raw_name = "unknown-private-suite"

    assert main(["eval", raw_name, "--json"]) == 2
    output = capsys.readouterr().out
    assert json.loads(output)["error"] == "unknown_suite"
    assert raw_name not in output


def test_eval_smoke_reports_failure_and_error_with_nonzero_exit(capsys):
    assert main(["eval", "smoke", "--json"]) == 1
    output = json.loads(capsys.readouterr().out)

    assert output["version"] == "evaluation-report/v1"
    assert output["passed"] is False
    assert output["metrics"] == {
        "total": 3,
        "passed": 1,
        "failed": 1,
        "errors": 1,
    }


def test_eval_cli_returns_zero_for_a_passing_suite(monkeypatch, capsys):
    passing = EvalSuite("passing", (case("only-case"),))
    monkeypatch.setattr("second_self.cli.discover_suites", lambda: (passing,))

    assert main(["eval", "passing"]) == 0
    assert "result: PASS" in capsys.readouterr().out
