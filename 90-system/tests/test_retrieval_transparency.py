"""Tests for explainable, privacy-safe recall summaries."""

from second_self.retrieval_transparency import build_report


def test_report_explains_evidence_retrieval_uncertainty_and_next_action():
    report = build_report(
        [
            {
                "title": "Decision note",
                "provenance": "layer1",
                "retrieval": "hybrid",
                "score": 42,
                "conflict_review": True,
            }
        ],
        fallback=False,
    )

    assert report["version"] == "retrieval-explanation/v1"
    assert report["answer"] == "Found 1 relevant source-backed result."
    assert report["retrieval_mode"] == "hybrid"
    assert report["capability_status"] == "available"
    assert report["uncertainty"] == "Conflicting claims require review."
    assert report["next_action"] == (
        "Prepare a conflict review before treating the result as settled."
    )
    assert report["evidence"] == [
        {
            "title": "Decision note",
            "provenance": "layer1",
            "retrieval": "hybrid",
            "score": 42,
            "conflict_review": True,
        }
    ]


def test_empty_fallback_report_is_explicit_and_payload_free():
    report = build_report(
        [],
        fallback=True,
    )

    assert report["answer"] == "No matching evidence was found."
    assert report["retrieval_mode"] == "keyword"
    assert report["capability_status"] == "degraded"
    assert report["next_action"] == "Broaden the query or verify the source manually."
    assert "path" not in report


def test_report_handles_multiple_modes_without_exposing_raw_results():
    report = build_report(
        [
            {"title": "A", "provenance": "layer1", "retrieval": "keyword"},
            {"title": "B", "provenance": "memory", "retrieval": "semantic"},
        ],
        fallback=False,
    )

    assert report["retrieval_mode"] == "hybrid"
    assert "results" not in report
    assert "snippet" not in str(report)
