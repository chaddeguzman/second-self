"""Regression tests for the deterministic synthetic safety suite."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from second_self.evaluation.models import EvalCaseStatus, EvalReason, EvalSuite
from second_self.evaluation.runner import discover_suites, render_json, run_suite
from second_self.evaluation.safety_suite import (
    SAFETY_SUITE,
    SYNTHETIC_MARKER,
    SYNTHETIC_PATH,
)


def test_safety_suite_passes_with_stable_boundary_reasons() -> None:
    report = run_suite(SAFETY_SUITE, private_roots=(Path("synthetic-private-root"),))

    assert report.passed
    assert len(report.cases) == 10
    assert all(case.status is EvalCaseStatus.PASS for case in report.cases)
    assert all(case.reason is not EvalReason.ASSERTIONS_PASSED for case in report.cases)
    assert report.metrics["quality"] == {"safety_boundary_enforcement": 1.0}


@pytest.mark.parametrize("case", SAFETY_SUITE.cases, ids=lambda case: case.case_id)
def test_each_boundary_has_a_failure_detecting_regression_case(case) -> None:
    expected_reason = case.assertions[0].expected

    def regressed_evaluator(_fixture):
        return {
            "boundary_reason": expected_reason,
            "enforced": False,
            "_metrics": {"safety_boundary_enforcement": 0.0},
        }

    regressed = replace(
        case,
        evaluator=regressed_evaluator,
    )
    report = run_suite(EvalSuite("regression", (regressed,)), private_roots=())

    assert report.passed is False
    assert report.cases[0].status is EvalCaseStatus.FAIL
    assert report.cases[0].reason is EvalReason.ASSERTION_FAILED
    assert report.cases[0].assertions[0].field == "boundary_reason"
    assert report.cases[0].assertions[0].passed is True
    assert report.cases[0].assertions[1].field == "enforced"
    assert report.cases[0].assertions[1].passed is False
    assert dict(report.cases[0].metrics) == {"safety_boundary_enforcement": 0.0}


def test_safety_report_is_redacted_and_deterministic() -> None:
    first = render_json(run_suite(SAFETY_SUITE, private_roots=()))
    second = render_json(run_suite(SAFETY_SUITE, private_roots=()))

    assert first == second
    assert SYNTHETIC_MARKER not in first
    assert SYNTHETIC_PATH not in first
    assert "SyntheticPrivate" not in first


def test_one_case_error_is_isolated_from_following_safety_case() -> None:
    def crash(_fixture):
        raise RuntimeError(f"{SYNTHETIC_MARKER} {SYNTHETIC_PATH}")

    broken = replace(SAFETY_SUITE.cases[0], case_id="a_crash", evaluator=crash)
    healthy = replace(SAFETY_SUITE.cases[1], case_id="z_healthy")
    report = run_suite(EvalSuite("isolation", (healthy, broken)), private_roots=())
    rendered = render_json(report)

    assert report.cases[0].status is EvalCaseStatus.ERROR
    assert report.cases[1].status is EvalCaseStatus.PASS
    assert SYNTHETIC_MARKER not in rendered
    assert SYNTHETIC_PATH not in rendered


def test_safety_suite_is_registered() -> None:
    assert "safety" in {suite.name for suite in discover_suites()}


def test_case_rejects_an_untyped_pass_reason() -> None:
    with pytest.raises(ValueError, match="pass reason"):
        replace(SAFETY_SUITE.cases[0], pass_reason="not_a_reason")
