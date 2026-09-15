"""Tiny built-in synthetic suite exercising pass, fail, and error isolation."""

from __future__ import annotations

from collections.abc import Mapping

from .models import EvalAssertion, EvalCase, EvalFixture, EvalSuite


def _synthetic_evaluator(fixture: Mapping[str, object]) -> Mapping[str, object]:
    if fixture.get("raise_error") is True:
        raise RuntimeError("synthetic runner error")
    return {"value": fixture.get("value")}


SMOKE_SUITE = EvalSuite(
    "smoke",
    (
        EvalCase(
            "runner-error",
            EvalFixture(True, data={"raise_error": True}),
            _synthetic_evaluator,
            (EvalAssertion("value", "synthetic"),),
        ),
        EvalCase(
            "assertion-failure",
            EvalFixture(True, data={"value": "synthetic-observed"}),
            _synthetic_evaluator,
            (EvalAssertion("value", "synthetic-expected"),),
        ),
        EvalCase(
            "passing-case",
            EvalFixture(True, data={"value": "synthetic"}),
            _synthetic_evaluator,
            (EvalAssertion("value", "synthetic"),),
        ),
    ),
)
