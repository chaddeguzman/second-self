"""Tests for redacted retrieval-quality feedback and summaries."""

from second_self.observability.retrieval_quality import (
    FeedbackRating,
    RetrievalEvent,
    summarize_events,
)


def test_event_contains_metrics_but_never_query_or_result_content():
    event = RetrievalEvent.from_results(
        result_count=3,
        results=[{"provenance": "layer1", "retrieval": "hybrid"}],
        fallback=False,
        latency_ms=12,
    )
    payload = event.as_dict()
    assert payload["result_count"] == 3
    assert payload["top_provenance"] == "layer1"
    assert "query" not in payload
    assert "snippet" not in payload
    assert "content" not in payload


def test_summary_is_deterministic_and_feedback_is_bounded():
    events = [
        RetrievalEvent("a", 2, 1, "layer1", "keyword", False, 5, FeedbackRating.POSITIVE),
        RetrievalEvent("b", 0, 0, "none", "none", True, 9, FeedbackRating.NEGATIVE),
    ]
    assert summarize_events(events) == {
        "version": "retrieval-quality/v1",
        "events": 2,
        "feedback": {"negative": 1, "positive": 1, "unknown": 0},
        "fallback_events": 1,
        "average_result_count": 1.0,
        "average_latency_ms": 7.0,
    }
