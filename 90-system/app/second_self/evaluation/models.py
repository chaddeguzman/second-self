"""Validated metadata and redacted result models for synthetic evaluations."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
Evaluator = Callable[[Mapping[str, object]], Mapping[str, object]]


class EvalCaseStatus(StrEnum):
    """Stable case outcomes."""

    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"


class EvalReason(StrEnum):
    """Stable, payload-free case reason codes."""

    ASSERTIONS_PASSED = "assertions_passed"
    ASSERTION_FAILED = "assertion_failed"
    RUNNER_ERROR = "runner_error"
    INVALID_FIXTURE = "invalid_fixture"
    PRIVATE_FIXTURE_REJECTED = "private_fixture_rejected"


@dataclass(frozen=True, slots=True)
class EvalFixture:
    """Synthetic inline data or a bounded JSON fixture path."""

    synthetic: bool
    data: Mapping[str, object] | None = None
    path: Path | None = None


@dataclass(frozen=True, slots=True)
class EvalAssertion:
    """One deterministic equality assertion over a top-level observed field."""

    field: str
    expected: object

    def __post_init__(self) -> None:
        if not isinstance(self.field, str) or not IDENTIFIER_RE.fullmatch(self.field):
            raise ValueError("evaluation assertion field is invalid")


@dataclass(frozen=True, slots=True)
class EvalCase:
    """One synthetic fixture, evaluator, and ordered assertion set."""

    case_id: str
    fixture: EvalFixture
    evaluator: Evaluator
    assertions: tuple[EvalAssertion, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not IDENTIFIER_RE.fullmatch(
            self.case_id
        ):
            raise ValueError("evaluation case ID is invalid")
        if not isinstance(self.fixture, EvalFixture):
            raise ValueError("evaluation fixture is invalid")
        if not callable(self.evaluator):
            raise ValueError("evaluation evaluator is invalid")
        if not isinstance(self.assertions, tuple) or not self.assertions or any(
            not isinstance(item, EvalAssertion) for item in self.assertions
        ):
            raise ValueError("evaluation assertions are invalid")


@dataclass(frozen=True, slots=True)
class EvalSuite:
    """Named collection of cases; runner order is independent of input order."""

    name: str
    cases: tuple[EvalCase, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not IDENTIFIER_RE.fullmatch(self.name):
            raise ValueError("evaluation suite name is invalid")
        if not isinstance(self.cases, tuple) or not self.cases or any(
            not isinstance(item, EvalCase) for item in self.cases
        ):
            raise ValueError("evaluation cases are invalid")
        identifiers = [item.case_id for item in self.cases]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("evaluation case IDs must be unique")


@dataclass(frozen=True, slots=True)
class AssertionResult:
    """Payload-free assertion result."""

    field: str
    passed: bool

    def as_dict(self) -> dict[str, object]:
        return {"field": self.field, "passed": self.passed}


@dataclass(frozen=True, slots=True)
class EvalCaseResult:
    """Redacted result for one isolated case."""

    case_id: str
    status: EvalCaseStatus
    reason: EvalReason
    detail: str
    assertions: tuple[AssertionResult, ...] = ()
    metrics: tuple[tuple[str, float], ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.case_id,
            "status": self.status.value,
            "reason": self.reason.value,
            "detail": self.detail,
            "assertions": [item.as_dict() for item in self.assertions],
            "metrics": {name: value for name, value in self.metrics},
        }


@dataclass(frozen=True, slots=True)
class EvalReport:
    """Versioned deterministic report with fixed aggregate metrics."""

    version: str
    suite: str
    passed: bool
    cases: tuple[EvalCaseResult, ...]

    @property
    def metrics(self) -> dict[str, object]:
        metrics: dict[str, object] = {
            "total": len(self.cases),
            "passed": sum(item.status is EvalCaseStatus.PASS for item in self.cases),
            "failed": sum(item.status is EvalCaseStatus.FAIL for item in self.cases),
            "errors": sum(item.status is EvalCaseStatus.ERROR for item in self.cases),
        }
        names = sorted({name for case in self.cases for name, _value in case.metrics})
        if names:
            metrics["quality"] = {
                name: round(
                    sum(dict(case.metrics).get(name, 0.0) for case in self.cases)
                    / len(self.cases),
                    6,
                )
                for name in names
            }
        return metrics

    def as_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "suite": self.suite,
            "passed": self.passed,
            "metrics": self.metrics,
            "cases": [item.as_dict() for item in self.cases],
        }
