"""Unit tests for the reusable Second Self health registry."""

import json

import pytest

from second_self.health import FAIL, OK, WARN, HealthCheck, HealthRegistry, HealthResult
from second_self.health.registry import exit_code, render_json, render_text


def _result(name: str, status: str = OK, detail: str = "healthy"):
    return lambda _fix: HealthResult(name, status, detail)


def test_registry_preserves_registration_order():
    registry = HealthRegistry()
    registry.register(HealthCheck("first", _result("first")))
    registry.register(HealthCheck("second", _result("second", WARN, "review")))

    assert [result.check for result in registry.run()] == ["first", "second"]


def test_registry_rejects_duplicate_names():
    registry = HealthRegistry()
    registry.register(HealthCheck("same", _result("same")))

    with pytest.raises(ValueError, match="duplicate health check"):
        registry.register(HealthCheck("same", _result("same")))


def test_registry_contains_exception_without_leaking_message():
    def crashes(_fix: bool) -> HealthResult:
        raise RuntimeError(r"secret at C:\private\payload.md")

    registry = HealthRegistry()
    registry.register(HealthCheck("safe-name", crashes))

    assert registry.run() == [
        HealthResult("safe-name", FAIL, "check raised an unexpected error")
    ]


def test_registry_contains_invalid_or_mismatched_result():
    registry = HealthRegistry()
    registry.register(HealthCheck("expected", _result("different")))

    assert registry.run()[0] == HealthResult(
        "expected", FAIL, "check raised an unexpected error"
    )


def test_fix_is_passed_only_to_explicit_safe_check():
    received: list[tuple[str, bool]] = []
    registry = HealthRegistry()
    registry.register(
        HealthCheck(
            "read-only",
            lambda fix: received.append(("read-only", fix))
            or HealthResult("read-only", OK, "checked"),
        )
    )
    registry.register(
        HealthCheck(
            "repairable",
            lambda fix: received.append(("repairable", fix))
            or HealthResult("repairable", OK, "checked"),
            supports_fix=True,
        )
    )

    registry.run(fix=True)

    assert received == [("read-only", False), ("repairable", True)]


@pytest.mark.parametrize(
    ("statuses", "strict", "expected"),
    [
        ([OK], False, 0),
        ([WARN], False, 0),
        ([WARN], True, 1),
        ([FAIL], False, 2),
        ([WARN, FAIL], True, 2),
    ],
)
def test_exit_code_semantics(statuses, strict, expected):
    results = [HealthResult(f"check-{i}", status, "detail") for i, status in enumerate(statuses)]

    assert exit_code(results, strict=strict) == expected


def test_renderers_have_stable_text_and_json_shapes():
    results = [
        HealthResult("alpha", OK, "ready"),
        HealthResult("beta", WARN, "review"),
        HealthResult("gamma", FAIL, "broken"),
    ]

    text = render_text(results, heading="Health")
    assert text.splitlines() == [
        "Health",
        "=" * 60,
        "[OK]   alpha                ready",
        "[WARN] beta                 review",
        "[FAIL] gamma                broken",
        "-" * 60,
        "Summary: 1 OK, 1 WARN, 1 FAIL",
    ]
    assert json.loads(render_json(results)) == {
        "results": [result.as_dict() for result in results]
    }
