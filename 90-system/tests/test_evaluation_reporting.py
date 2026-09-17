"""Deterministic baseline comparison, refresh, and safety tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from second_self.cli import main
from second_self.evaluation.models import (
    EvalAssertion,
    EvalCase,
    EvalCaseResult,
    EvalCaseStatus,
    EvalFixture,
    EvalReason,
    EvalReport,
    EvalSuite,
)
from second_self.evaluation.reporting import (
    BASELINE_VERSION,
    BaselineError,
    baseline_compatibility,
    build_baseline,
    compare_report,
    load_baseline,
    render_comparison_text,
    write_baseline,
)
from second_self.evaluation.runner import REPORT_VERSION


def _case(
    case_id: str,
    status: EvalCaseStatus = EvalCaseStatus.PASS,
    metric: float = 1.0,
) -> EvalCaseResult:
    reason = (
        EvalReason.ASSERTIONS_PASSED
        if status is EvalCaseStatus.PASS
        else EvalReason.ASSERTION_FAILED
    )
    return EvalCaseResult(
        case_id,
        status,
        reason,
        "synthetic result",
        metrics=(("quality", metric),),
    )


def _report(*cases: EvalCaseResult, suite: str = "synthetic") -> EvalReport:
    return EvalReport(
        REPORT_VERSION,
        suite,
        all(case.status is EvalCaseStatus.PASS for case in cases),
        tuple(cases),
    )


def test_no_change_is_compatible_and_deterministic() -> None:
    report = _report(_case("one"))
    baseline = build_baseline((report,))

    first = compare_report(report, baseline)
    second = compare_report(report, baseline)

    assert first == second
    assert first.passed
    assert first.as_dict()["regressed_cases"] == []
    assert render_comparison_text(first) == (
        "baseline: PASS\nadded=0 removed=0 improved=0 regressed=0"
    )


def test_added_removed_improved_and_regressed_cases_are_visible() -> None:
    baseline_report = _report(
        _case("improves", EvalCaseStatus.FAIL),
        _case("regresses"),
        _case("removed"),
    )
    current = _report(
        _case("added"),
        _case("improves"),
        _case("regresses", EvalCaseStatus.FAIL),
    )

    comparison = compare_report(current, build_baseline((baseline_report,)))

    assert comparison.added_cases == ("added",)
    assert comparison.removed_cases == ("removed",)
    assert comparison.improved_cases == ("improves",)
    assert comparison.regressed_cases == ("regresses",)
    assert comparison.passed is False


def test_zero_drop_metric_threshold_detects_regression_and_improvement() -> None:
    baseline = build_baseline((_report(_case("one", metric=0.5)),))

    improved = compare_report(_report(_case("one", metric=0.6)), baseline)
    regressed = compare_report(_report(_case("one", metric=0.4)), baseline)

    assert improved.improved_metrics == ("one.quality",)
    assert improved.passed
    assert regressed.regressed_metrics == ("one.quality",)
    assert regressed.passed is False


def test_quality_averages_only_cases_that_define_metric() -> None:
    report = _report(
        _case("defined", metric=1.0),
        EvalCaseResult(
            "undefined", EvalCaseStatus.PASS, EvalReason.ASSERTIONS_PASSED,
            "synthetic result",
        ),
    )

    assert report.metrics["quality"] == {"quality": 1.0}


def test_case_status_order_distinguishes_error_fail_and_pass() -> None:
    failed_baseline = build_baseline(
        (_report(_case("one", EvalCaseStatus.FAIL)),)
    )
    error_baseline = build_baseline(
        (_report(_case("one", EvalCaseStatus.ERROR)),)
    )

    regressed = compare_report(
        _report(_case("one", EvalCaseStatus.ERROR)), failed_baseline
    )
    improved = compare_report(
        _report(_case("one", EvalCaseStatus.FAIL)), error_baseline
    )

    assert regressed.regressed_cases == ("one",)
    assert improved.improved_cases == ("one",)


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        '{"version": "wrong"}',
        json.dumps(
            {
                "version": BASELINE_VERSION,
                "report_version": REPORT_VERSION,
                "synthetic": False,
                "thresholds": {"case_score_drop": 0.0, "metric_drop": 0.0},
                "suites": {},
            }
        ),
    ],
)
def test_missing_corrupt_or_incompatible_baseline_is_rejected(
    tmp_path: Path, payload: str
) -> None:
    path = tmp_path / "baseline.json"
    if payload:
        path.write_text(payload, encoding="utf-8")
    with pytest.raises(BaselineError):
        load_baseline(path)

    path.unlink(missing_ok=True)
    with pytest.raises(BaselineError, match="missing"):
        load_baseline(path)


def test_registry_compatibility_requires_exact_suite_set() -> None:
    baseline = build_baseline((_report(_case("one")),))

    baseline_compatibility(baseline, ("synthetic",))
    with pytest.raises(BaselineError, match="registry"):
        baseline_compatibility(baseline, ("synthetic", "added"))


def test_write_is_deterministic_and_contains_only_synthetic_metadata(
    tmp_path: Path,
) -> None:
    path = tmp_path / "baseline.json"
    report = _report(_case("one"))
    write_baseline(path, (report,))
    first = path.read_bytes()
    write_baseline(path, (report,))

    assert path.read_bytes() == first
    payload = json.loads(first)
    assert payload["synthetic"] is True
    assert set(payload) == {
        "report_version",
        "suites",
        "synthetic",
        "thresholds",
        "version",
    }


def test_explicit_cli_refresh_writes_only_redirected_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    baseline = tmp_path / "output" / "baseline.json"
    protected = tmp_path / "evidence" / "memory.md"
    runtime = tmp_path / "runtime" / "policy.md"
    protected.parent.mkdir()
    runtime.parent.mkdir()
    protected.write_text("fictional evidence", encoding="utf-8")
    runtime.write_text("fictional policy", encoding="utf-8")
    before = (protected.read_bytes(), runtime.read_bytes())
    monkeypatch.setattr("second_self.cli.EVALUATION_BASELINE_PATH", baseline)
    synthetic_suite = EvalSuite(
        "synthetic",
        (
            EvalCase(
                "only-case",
                EvalFixture(True, data={"value": "synthetic"}),
                lambda fixture: {"value": fixture["value"]},
                (EvalAssertion("value", "synthetic"),),
            ),
        ),
    )
    monkeypatch.setattr(
        "second_self.cli.discover_suites", lambda: (synthetic_suite,)
    )

    assert main(["eval", "--refresh-baseline", "--json"]) == 0
    output = json.loads(capsys.readouterr().out)

    assert output["status"] == "refreshed"
    assert load_baseline(baseline)["synthetic"] is True
    assert (protected.read_bytes(), runtime.read_bytes()) == before
    assert sorted(path for path in tmp_path.rglob("*") if path.is_file()) == [
        protected,
        baseline,
        runtime,
    ]


def test_cli_missing_baseline_is_redacted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    missing = tmp_path / "private-name" / "baseline.json"
    monkeypatch.setattr("second_self.cli.EVALUATION_BASELINE_PATH", missing)

    assert main(["eval", "recall", "--json"]) == 2
    output = capsys.readouterr().out
    assert json.loads(output)["error"] == "baseline_unavailable"
    assert str(tmp_path) not in output


@pytest.mark.parametrize(
    ("baseline_metric", "current_metric", "expected_exit", "field"),
    [
        (1.0, 0.9, 1, "regressed_metrics"),
        (0.5, 0.6, 0, "improved_metrics"),
    ],
)
def test_cli_metric_gate_has_stable_ci_exit_and_visible_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
    baseline_metric: float,
    current_metric: float,
    expected_exit: int,
    field: str,
) -> None:
    suite = EvalSuite(
        "gate",
        (
            EvalCase(
                "only-case",
                EvalFixture(True, data={"metric": current_metric}),
                lambda fixture: {
                    "value": "synthetic",
                    "_metrics": {"quality": fixture["metric"]},
                },
                (EvalAssertion("value", "synthetic"),),
            ),
        ),
    )
    baseline_path = tmp_path / "baseline.json"
    write_baseline(
        baseline_path,
        (_report(_case("only-case", metric=baseline_metric), suite="gate"),),
    )
    monkeypatch.setattr("second_self.cli.discover_suites", lambda: (suite,))
    monkeypatch.setattr(
        "second_self.cli.EVALUATION_BASELINE_PATH", baseline_path
    )

    assert main(["eval", "gate", "--json"]) == expected_exit
    output = json.loads(capsys.readouterr().out)
    assert output["baseline"][field] == ["only-case.quality"]


def test_refresh_rejects_a_suite_argument_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    baseline = tmp_path / "baseline.json"
    monkeypatch.setattr("second_self.cli.EVALUATION_BASELINE_PATH", baseline)

    assert main(["eval", "recall", "--refresh-baseline", "--json"]) == 2
    assert json.loads(capsys.readouterr().out)["error"] == "invalid_refresh"
    assert not baseline.exists()
