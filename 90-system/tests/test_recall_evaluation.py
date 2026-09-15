"""Failure-detection tests for fictional recall quality metrics."""

from __future__ import annotations

from copy import deepcopy

import pytest

from second_self.evaluation import render_json, run_suite
from second_self.evaluation.recall_suite import (
    RECALL_SUITE,
    RECALL_THRESHOLDS,
    evaluate_recall_fixture,
)


def fixture(case_id: str) -> dict[str, object]:
    selected = next(case for case in RECALL_SUITE.cases if case.case_id == case_id)
    assert selected.fixture.data is not None
    return deepcopy(dict(selected.fixture.data))


def metrics(payload: dict[str, object]) -> dict[str, float]:
    observed = evaluate_recall_fixture(payload)
    raw = observed["_metrics"]
    assert isinstance(raw, dict)
    return raw


def test_recall_suite_passes_thresholds_and_is_report_safe():
    report = run_suite(RECALL_SUITE, private_roots=())
    output = render_json(report)

    assert report.passed is True
    assert report.metrics["total"] == 8
    quality = report.metrics["quality"]
    assert isinstance(quality, dict)
    assert all(0.0 <= value <= 1.0 for value in quality.values())
    assert "Starling Protocol" not in output
    assert "amber cards" not in output
    assert "01-strategy-storage/" not in output


def test_recall_suite_is_byte_deterministic_across_temporary_vaults():
    first = run_suite(RECALL_SUITE, private_roots=())
    second = run_suite(RECALL_SUITE, private_roots=())

    assert first == second
    assert render_json(first) == render_json(second)


def test_retrieval_precision_detects_multiple_competing_weak_results():
    payload = fixture("exact-title-confirmed")
    notes = payload["notes"]
    assert isinstance(notes, list)
    notes.extend(
        [
            {"path": "04 References/03 research/Weak One.md", "created": "2026-05-01", "tags": [], "body": "Weak starling protocol mention."},
            {"path": "04 References/03 research/Weak Two.md", "created": "2026-05-01", "tags": [], "body": "Another starling protocol mention."},
        ]
    )

    assert metrics(payload)["retrieval_precision"] < RECALL_THRESHOLDS["retrieval_precision"]


def test_expected_source_coverage_detects_missing_retrieval():
    payload = fixture("exact-title-confirmed")
    payload["query"] = "absent fictional query"

    assert metrics(payload)["expected_source_coverage"] == 0.0


def test_source_attribution_detects_wrong_date():
    payload = fixture("exact-title-confirmed")
    response = payload["response"]
    assert isinstance(response, dict)
    response["findings"][0]["citations"][0]["date"] = "2026-05-02"

    assert metrics(payload)["source_attribution"] == 0.0


def test_evidence_label_metric_detects_confirmed_inferred_blur():
    payload = fixture("exact-title-confirmed")
    response = payload["response"]
    assert isinstance(response, dict)
    response["findings"][0]["label"] = "inferred"

    assert metrics(payload)["evidence_label_correctness"] == 0.0


def test_inferred_label_requires_an_explanation():
    payload = fixture("labeled-inference")
    response = payload["response"]
    assert isinstance(response, dict)
    del response["findings"][0]["reason"]

    assert metrics(payload)["evidence_label_correctness"] == 0.0


def test_missing_evidence_metric_detects_guessing():
    payload = fixture("missing-evidence")
    response = payload["response"]
    assert isinstance(response, dict)
    response["findings"] = [{"label": "confirmed", "citations": []}]

    assert metrics(payload)["missing_evidence_behavior"] == 0.0


def test_contradiction_metric_requires_both_sources_and_explicit_flag():
    payload = fixture("contradictory-dated-sources")
    response = payload["response"]
    assert isinstance(response, dict)
    response["contradiction"] = False

    assert metrics(payload)["contradiction_surfacing"] == 0.0


def test_ranking_metric_detects_changed_tie_order():
    payload = fixture("deterministic-tie-order")
    expected = payload["expected_order"]
    assert isinstance(expected, list)
    payload["expected_order"] = list(reversed(expected))

    assert metrics(payload)["ranking_accuracy"] == 0.0


@pytest.mark.parametrize("case", RECALL_SUITE.cases, ids=lambda item: item.case_id)
def test_every_recall_case_uses_inline_fictional_synthetic_data(case):
    assert case.fixture.synthetic is True
    assert case.fixture.path is None
    assert case.fixture.data is not None
