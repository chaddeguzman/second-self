"""Deterministic, redaction-safe health-check registry.

The registry owns result validation, execution order, exception containment,
rendering, summary counts, and process exit-code calculation. Individual checks
remain responsible for returning details that are safe to display.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass

OK = "OK"
WARN = "WARN"
FAIL = "FAIL"
STATUSES = (OK, WARN, FAIL)


@dataclass(frozen=True, slots=True)
class HealthResult:
    """One validated, display-safe health-check result."""

    check: str
    status: str
    detail: str

    def __post_init__(self) -> None:
        if not self.check:
            raise ValueError("health result check name cannot be empty")
        if self.status not in STATUSES:
            raise ValueError(f"invalid health status for check {self.check!r}")
        if not self.detail:
            raise ValueError(f"health detail cannot be empty for check {self.check!r}")

    def as_dict(self) -> dict[str, str]:
        """Return the stable JSON-compatible result shape."""
        return {"check": self.check, "status": self.status, "detail": self.detail}


HealthRunner = Callable[[bool], HealthResult]


@dataclass(frozen=True, slots=True)
class HealthCheck:
    """A named check and whether it is allowed to apply a safe fix."""

    name: str
    runner: HealthRunner
    supports_fix: bool = False


class HealthRegistry:
    """Register and execute health checks in insertion order."""

    def __init__(self) -> None:
        self._checks: list[HealthCheck] = []
        self._names: set[str] = set()

    def register(self, check: HealthCheck) -> None:
        """Register one uniquely named check at the end of the run order."""
        if not check.name:
            raise ValueError("health check name cannot be empty")
        if check.name in self._names:
            raise ValueError(f"duplicate health check: {check.name}")
        self._checks.append(check)
        self._names.add(check.name)

    def __iter__(self) -> Iterator[HealthCheck]:
        return iter(self._checks)

    def run(self, *, fix: bool = False) -> list[HealthResult]:
        """Run every check in registration order and contain check failures."""
        results: list[HealthResult] = []
        for check in self._checks:
            try:
                # TECHNICAL: Only a check explicitly marked safe receives the fix
                # flag. This prevents a future read-only check from accidentally
                # becoming mutating merely because the CLI was run with --fix.
                #
                # JUNIOR: The repair key is handed only to checks listed as safe
                # repairers; every other check is forced to inspect without edits.
                result = check.runner(fix and check.supports_fix)
                if result.check != check.name:
                    raise ValueError("health result name does not match registration")
            except Exception:
                # NOTE: Exception text is intentionally omitted because it may
                # contain private absolute paths or connector payload details.
                result = HealthResult(
                    check=check.name,
                    status=FAIL,
                    detail="check raised an unexpected error",
                )
            results.append(result)
        return results


def result_dicts(results: Sequence[HealthResult]) -> list[dict[str, str]]:
    """Serialize results using the stable legacy dictionary shape."""
    return [result.as_dict() for result in results]


def render_json(results: Sequence[HealthResult]) -> str:
    """Render the stable machine-readable report."""
    return json.dumps({"results": result_dicts(results)}, indent=2)


def render_text(results: Sequence[HealthResult], *, heading: str) -> str:
    """Render the stable human-readable report."""
    lines = [heading, "=" * 60]
    for result in results:
        marker = {OK: "[OK]  ", WARN: "[WARN]", FAIL: "[FAIL]"}[result.status]
        lines.append(f"{marker} {result.check:<20} {result.detail}")
    counts = {status: sum(1 for r in results if r.status == status) for status in STATUSES}
    lines.extend(
        [
            "-" * 60,
            f"Summary: {counts[OK]} OK, {counts[WARN]} WARN, {counts[FAIL]} FAIL",
        ]
    )
    return "\n".join(lines)


def exit_code(results: Sequence[HealthResult], *, strict: bool) -> int:
    """Return 2 for FAIL, 1 for strict WARN, otherwise 0."""
    if any(result.status == FAIL for result in results):
        return 2
    if strict and any(result.status == WARN for result in results):
        return 1
    return 0
