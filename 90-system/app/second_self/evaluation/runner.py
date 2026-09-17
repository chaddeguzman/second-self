"""Synthetic suite discovery, deterministic execution, and report rendering."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

from .models import (
    AssertionResult,
    EvalCase,
    EvalCaseResult,
    EvalCaseStatus,
    EvalFixture,
    EvalReason,
    EvalReport,
    EvalSuite,
    IDENTIFIER_RE,
)
from .recall_suite import RECALL_SUITE
from .semantic_suite import SEMANTIC_SUITE
from .safety_suite import SAFETY_SUITE
from .smoke import SMOKE_SUITE

REPORT_VERSION = "evaluation-report/v1"
MAX_FIXTURE_BYTES = 1_048_576
BUILTIN_SUITES = (RECALL_SUITE, SAFETY_SUITE, SEMANTIC_SUITE, SMOKE_SUITE)


class FixtureValidationError(ValueError):
    """Internal fixture error carrying only a stable reason code."""

    def __init__(self, reason: EvalReason) -> None:
        super().__init__(reason.value)
        self.reason = reason


def discover_suites(
    suites: Sequence[EvalSuite] = BUILTIN_SUITES,
) -> tuple[EvalSuite, ...]:
    """Return validated suites in stable name order."""
    if not isinstance(suites, Sequence) or isinstance(suites, (str, bytes)):
        raise ValueError("evaluation suite registry is invalid")
    if any(not isinstance(suite, EvalSuite) for suite in suites):
        raise ValueError("evaluation suite registry is invalid")
    names = [suite.name for suite in suites]
    if len(names) != len(set(names)):
        raise ValueError("evaluation suite names must be unique")
    return tuple(sorted(suites, key=lambda suite: suite.name))


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _load_fixture(
    fixture: EvalFixture, private_roots: Sequence[Path]
) -> Mapping[str, object]:
    if fixture.synthetic is not True:
        raise FixtureValidationError(EvalReason.INVALID_FIXTURE)
    if (fixture.data is None) == (fixture.path is None):
        raise FixtureValidationError(EvalReason.INVALID_FIXTURE)
    if fixture.data is not None:
        if not isinstance(fixture.data, Mapping):
            raise FixtureValidationError(EvalReason.INVALID_FIXTURE)
        return dict(fixture.data)

    if not isinstance(fixture.path, Path):
        raise FixtureValidationError(EvalReason.INVALID_FIXTURE)
    candidate = fixture.path.resolve()
    for raw_root in private_roots:
        if not isinstance(raw_root, Path):
            raise FixtureValidationError(EvalReason.INVALID_FIXTURE)
        if _inside(candidate, raw_root.resolve()):
            raise FixtureValidationError(EvalReason.PRIVATE_FIXTURE_REJECTED)
    try:
        if candidate.stat().st_size > MAX_FIXTURE_BYTES:
            raise FixtureValidationError(EvalReason.INVALID_FIXTURE)
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except FixtureValidationError:
        raise
    except (OSError, UnicodeError, ValueError):
        raise FixtureValidationError(EvalReason.INVALID_FIXTURE) from None
    if (
        not isinstance(payload, dict)
        or set(payload) != {"synthetic", "data"}
        or payload.get("synthetic") is not True
        or not isinstance(payload.get("data"), dict)
    ):
        raise FixtureValidationError(EvalReason.INVALID_FIXTURE)
    return payload["data"]


def _run_case(case: EvalCase, private_roots: Sequence[Path]) -> EvalCaseResult:
    try:
        fixture = _load_fixture(case.fixture, private_roots)
    except FixtureValidationError as exc:
        detail = (
            "fixture path is not allowed"
            if exc.reason is EvalReason.PRIVATE_FIXTURE_REJECTED
            else "synthetic fixture is invalid"
        )
        return EvalCaseResult(case.case_id, EvalCaseStatus.ERROR, exc.reason, detail)

    try:
        observed = case.evaluator(fixture)
        if not isinstance(observed, Mapping):
            raise TypeError("invalid evaluator result")
        raw_metrics = observed.get("_metrics", {})
        if not isinstance(raw_metrics, Mapping):
            raise TypeError("invalid metric result")
        metrics: list[tuple[str, float]] = []
        for name, value in raw_metrics.items():
            if (
                not isinstance(name, str)
                or not IDENTIFIER_RE.fullmatch(name)
                or isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0.0 <= float(value) <= 1.0
            ):
                raise TypeError("invalid metric result")
            metrics.append((name, float(value)))
        assertions = tuple(
            AssertionResult(item.field, observed.get(item.field) == item.expected)
            for item in case.assertions
        )
    except Exception:
        return EvalCaseResult(
            case.case_id,
            EvalCaseStatus.ERROR,
            EvalReason.RUNNER_ERROR,
            "case execution failed",
        )
    if all(item.passed for item in assertions):
        return EvalCaseResult(
            case.case_id,
            EvalCaseStatus.PASS,
            case.pass_reason,
            "all assertions passed",
            assertions,
            tuple(sorted(metrics)),
        )
    return EvalCaseResult(
        case.case_id,
        EvalCaseStatus.FAIL,
        EvalReason.ASSERTION_FAILED,
        "one or more assertions failed",
        assertions,
        tuple(sorted(metrics)),
    )


def run_suite(
    suite: EvalSuite, *, private_roots: Sequence[Path]
) -> EvalReport:
    """Run every case in stable ID order; one error never stops another case."""
    if not isinstance(suite, EvalSuite):
        raise ValueError("evaluation suite is invalid")
    if not isinstance(private_roots, Sequence) or isinstance(
        private_roots, (str, bytes)
    ):
        raise ValueError("private root boundary is invalid")
    if any(not isinstance(root, Path) for root in private_roots):
        raise ValueError("private root boundary is invalid")
    try:
        resolved_roots = tuple(root.resolve() for root in private_roots)
    except OSError:
        raise ValueError("private root boundary is invalid") from None
    results = tuple(
        _run_case(case, resolved_roots)
        for case in sorted(suite.cases, key=lambda item: item.case_id)
    )
    return EvalReport(
        REPORT_VERSION,
        suite.name,
        all(item.status is EvalCaseStatus.PASS for item in results),
        results,
    )


def render_json(report: EvalReport) -> str:
    """Return stable machine-readable output without fixture values or paths."""
    return json.dumps(report.as_dict(), indent=2, sort_keys=False)


def render_text(report: EvalReport) -> str:
    """Return stable human-readable output without fixture values or paths."""
    lines = [
        f"evaluation suite: {report.suite}",
        f"result: {'PASS' if report.passed else 'FAIL'}",
    ]
    for case in report.cases:
        lines.append(
            f"[{case.status.value.upper()}] {case.case_id}: "
            f"{case.reason.value} - {case.detail}"
        )
    metrics = report.metrics
    lines.append(
        "metrics: "
        f"total={metrics['total']} passed={metrics['passed']} "
        f"failed={metrics['failed']} errors={metrics['errors']}"
    )
    return "\n".join(lines)
