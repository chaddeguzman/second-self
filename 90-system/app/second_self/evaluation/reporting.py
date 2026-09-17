"""Synthetic baseline persistence and deterministic regression comparison."""

from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .models import EvalCaseStatus, EvalReport
from .runner import REPORT_VERSION

BASELINE_VERSION = "evaluation-baseline/v1"
COMPARISON_VERSION = "evaluation-comparison/v1"
DEFAULT_THRESHOLDS = {"case_score_drop": 0.0, "metric_drop": 0.0}
MAX_BASELINE_BYTES = 1_048_576
SAFE_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


class BaselineError(ValueError):
    """A redacted baseline validation failure safe for CLI and doctor output."""


@dataclass(frozen=True, slots=True)
class BaselineComparison:
    """Payload-free differences between one current report and its baseline."""

    suite: str
    added_cases: tuple[str, ...]
    removed_cases: tuple[str, ...]
    improved_cases: tuple[str, ...]
    regressed_cases: tuple[str, ...]
    improved_metrics: tuple[str, ...]
    regressed_metrics: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not (self.removed_cases or self.regressed_cases or self.regressed_metrics)

    def as_dict(self) -> dict[str, object]:
        return {
            "version": COMPARISON_VERSION,
            "suite": self.suite,
            "compatible": True,
            "passed": self.passed,
            "added_cases": list(self.added_cases),
            "removed_cases": list(self.removed_cases),
            "improved_cases": list(self.improved_cases),
            "regressed_cases": list(self.regressed_cases),
            "improved_metrics": list(self.improved_metrics),
            "regressed_metrics": list(self.regressed_metrics),
        }


def _case_record(case) -> dict[str, object]:
    return {
        "status": case.status.value,
        "metrics": {name: value for name, value in case.metrics},
    }


def build_baseline(reports: Sequence[EvalReport]) -> dict[str, object]:
    """Create a deterministic synthetic-only baseline from current reports."""
    if not isinstance(reports, Sequence) or not reports:
        raise BaselineError("baseline reports are invalid")
    suites: dict[str, object] = {}
    for report in sorted(reports, key=lambda item: item.suite):
        if not isinstance(report, EvalReport) or report.version != REPORT_VERSION:
            raise BaselineError("baseline report version is incompatible")
        if report.suite in suites:
            raise BaselineError("baseline suite names are invalid")
        suites[report.suite] = {
            "cases": {
                case.case_id: _case_record(case)
                for case in sorted(report.cases, key=lambda item: item.case_id)
            }
        }
    return {
        "version": BASELINE_VERSION,
        "report_version": REPORT_VERSION,
        "synthetic": True,
        "thresholds": dict(DEFAULT_THRESHOLDS),
        "suites": suites,
    }


def write_baseline(path: Path, reports: Sequence[EvalReport]) -> None:
    """Atomically write only the deterministic baseline payload."""
    if not isinstance(path, Path):
        raise BaselineError("baseline destination is invalid")
    payload = build_baseline(reports)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise BaselineError("baseline refresh failed") from None


def _bounded_number(value: object) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0.0 <= float(value) <= 1.0
    ):
        raise BaselineError("baseline is corrupt")
    return float(value)


def _validate_baseline(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict) or set(payload) != {
        "version",
        "report_version",
        "synthetic",
        "thresholds",
        "suites",
    }:
        raise BaselineError("baseline is corrupt")
    if (
        payload["version"] != BASELINE_VERSION
        or payload["report_version"] != REPORT_VERSION
        or payload["synthetic"] is not True
    ):
        raise BaselineError("baseline version is incompatible")
    thresholds = payload["thresholds"]
    if not isinstance(thresholds, dict) or set(thresholds) != set(DEFAULT_THRESHOLDS):
        raise BaselineError("baseline thresholds are invalid")
    for value in thresholds.values():
        _bounded_number(value)
    suites = payload["suites"]
    if not isinstance(suites, dict) or not suites:
        raise BaselineError("baseline suites are invalid")
    for suite_name, suite in suites.items():
        if not isinstance(suite_name, str) or not SAFE_NAME.fullmatch(suite_name):
            raise BaselineError("baseline suite names are invalid")
        if not isinstance(suite, dict) or set(suite) != {"cases"}:
            raise BaselineError("baseline suite is corrupt")
        cases = suite["cases"]
        if not isinstance(cases, dict) or not cases:
            raise BaselineError("baseline cases are invalid")
        for case_id, record in cases.items():
            if not isinstance(case_id, str) or not SAFE_NAME.fullmatch(case_id):
                raise BaselineError("baseline case IDs are invalid")
            if not isinstance(record, dict) or set(record) != {"status", "metrics"}:
                raise BaselineError("baseline case is corrupt")
            try:
                EvalCaseStatus(record["status"])
            except (TypeError, ValueError):
                raise BaselineError("baseline case status is invalid") from None
            metrics = record["metrics"]
            if not isinstance(metrics, dict):
                raise BaselineError("baseline metrics are invalid")
            for metric_name, value in metrics.items():
                if not isinstance(metric_name, str) or not SAFE_NAME.fullmatch(metric_name):
                    raise BaselineError("baseline metric names are invalid")
                _bounded_number(value)
    return payload


def load_baseline(path: Path) -> dict[str, object]:
    """Load a bounded checked-in baseline without exposing path or parse errors."""
    try:
        if not path.is_file():
            raise BaselineError("baseline is missing")
        if path.stat().st_size > MAX_BASELINE_BYTES:
            raise BaselineError("baseline is corrupt")
        payload = json.loads(path.read_text(encoding="utf-8"))
    except BaselineError:
        raise
    except (OSError, UnicodeError, ValueError):
        raise BaselineError("baseline is corrupt") from None
    return _validate_baseline(payload)


def baseline_compatibility(
    baseline: Mapping[str, object], expected_suites: Sequence[str]
) -> None:
    """Require the baseline to describe exactly the registered suite set."""
    payload = _validate_baseline(dict(baseline))
    suites = payload["suites"]
    assert isinstance(suites, dict)
    if sorted(suites) != sorted(expected_suites):
        raise BaselineError("baseline suite registry is incompatible")


def _status_score(value: str) -> float:
    return {
        EvalCaseStatus.ERROR.value: 0.0,
        EvalCaseStatus.FAIL.value: 0.5,
        EvalCaseStatus.PASS.value: 1.0,
    }[value]


def compare_report(
    report: EvalReport, baseline: Mapping[str, object]
) -> BaselineComparison:
    """Compare one compatible report using explicit zero-drop thresholds."""
    payload = _validate_baseline(dict(baseline))
    if report.version != payload["report_version"]:
        raise BaselineError("baseline report version is incompatible")
    suites = payload["suites"]
    assert isinstance(suites, dict)
    suite = suites.get(report.suite)
    if not isinstance(suite, dict):
        raise BaselineError("baseline suite is missing")
    baseline_cases = suite["cases"]
    assert isinstance(baseline_cases, dict)
    current_cases = {case.case_id: case for case in report.cases}
    baseline_ids = set(baseline_cases)
    current_ids = set(current_cases)
    added = tuple(sorted(current_ids - baseline_ids))
    removed = tuple(sorted(baseline_ids - current_ids))
    improved_cases: list[str] = []
    regressed_cases: list[str] = []
    improved_metrics: list[str] = []
    regressed_metrics: list[str] = []
    thresholds = payload["thresholds"]
    assert isinstance(thresholds, dict)
    case_drop = float(thresholds["case_score_drop"])
    metric_drop = float(thresholds["metric_drop"])
    for case_id in sorted(current_ids & baseline_ids):
        current = current_cases[case_id]
        old = baseline_cases[case_id]
        assert isinstance(old, dict)
        old_status = str(old["status"])
        delta = _status_score(current.status.value) - _status_score(old_status)
        if delta < -case_drop:
            regressed_cases.append(case_id)
        elif delta > case_drop:
            improved_cases.append(case_id)
        old_metrics = old["metrics"]
        assert isinstance(old_metrics, dict)
        new_metrics = dict(current.metrics)
        for name in sorted(set(old_metrics) | set(new_metrics)):
            # A metric is meaningful only for cases that define it in both
            # reports. Missing metrics are not failed measurements.
            if name not in old_metrics or name not in new_metrics:
                continue
            identifier = f"{case_id}.{name}"
            old_value = float(old_metrics[name])
            new_value = float(new_metrics[name])
            metric_delta = new_value - old_value
            if metric_delta < -metric_drop:
                regressed_metrics.append(identifier)
            elif metric_delta > metric_drop:
                improved_metrics.append(identifier)
    return BaselineComparison(
        report.suite,
        added,
        removed,
        tuple(improved_cases),
        tuple(regressed_cases),
        tuple(improved_metrics),
        tuple(regressed_metrics),
    )


def render_comparison_text(comparison: BaselineComparison) -> str:
    """Render a compact, deterministic, payload-free comparison summary."""
    status = "PASS" if comparison.passed else "REGRESSION"
    return "\n".join(
        (
            f"baseline: {status}",
            f"added={len(comparison.added_cases)} removed={len(comparison.removed_cases)} "
            f"improved={len(comparison.improved_cases) + len(comparison.improved_metrics)} "
            f"regressed={len(comparison.regressed_cases) + len(comparison.regressed_metrics)}",
        )
    )
