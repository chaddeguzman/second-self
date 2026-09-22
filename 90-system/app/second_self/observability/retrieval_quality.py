"""Redacted retrieval-quality events and deterministic feedback summaries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Mapping


class FeedbackRating(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RetrievalEvent:
    """Metrics-only retrieval observation; query and source contents are excluded."""

    event_id: str
    result_count: int
    top_rank: int
    top_provenance: str
    retrieval: str
    fallback: bool
    latency_ms: int
    feedback: FeedbackRating = FeedbackRating.UNKNOWN

    @classmethod
    def from_results(
        cls,
        *,
        result_count: int,
        results: list[Mapping[str, object]],
        fallback: bool,
        latency_ms: int,
        event_id: str = "event",
        feedback: FeedbackRating = FeedbackRating.UNKNOWN,
    ) -> "RetrievalEvent":
        first = results[0] if results else {}
        return cls(
            event_id=event_id,
            result_count=max(0, int(result_count)),
            top_rank=1 if results else 0,
            top_provenance=str(first.get("provenance", "none")) if results else "none",
            retrieval=str(first.get("retrieval", "none")) if results else "none",
            fallback=bool(fallback),
            latency_ms=max(0, int(latency_ms)),
            feedback=feedback,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "version": "retrieval-event/v1",
            "event_id": self.event_id,
            "result_count": self.result_count,
            "top_rank": self.top_rank,
            "top_provenance": self.top_provenance,
            "retrieval": self.retrieval,
            "fallback": self.fallback,
            "latency_ms": self.latency_ms,
            "feedback": self.feedback.value,
        }


def summarize_events(events: Iterable[RetrievalEvent]) -> dict[str, object]:
    values = list(events)
    counts = {rating.value: 0 for rating in FeedbackRating}
    for event in values:
        counts[event.feedback.value] += 1
    return {
        "version": "retrieval-quality/v1",
        "events": len(values),
        "feedback": counts,
        "fallback_events": sum(event.fallback for event in values),
        "average_result_count": round(
            sum(event.result_count for event in values) / len(values), 6
        ) if values else 0.0,
        "average_latency_ms": round(
            sum(event.latency_ms for event in values) / len(values), 6
        ) if values else 0.0,
    }


def append_event(path: Path, event: RetrievalEvent) -> None:
    """Append a metrics-only event to a caller-selected private cache path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event.as_dict(), sort_keys=True) + "\n")


def load_events(path: Path) -> tuple[RetrievalEvent, ...]:
    """Load only valid metrics records; malformed lines are ignored safely."""
    if not path.is_file():
        return ()
    events: list[RetrievalEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            payload = json.loads(line)
            if payload.get("version") != "retrieval-event/v1":
                continue
            events.append(
                RetrievalEvent(
                    event_id=str(payload["event_id"]),
                    result_count=int(payload["result_count"]),
                    top_rank=int(payload["top_rank"]),
                    top_provenance=str(payload["top_provenance"]),
                    retrieval=str(payload["retrieval"]),
                    fallback=bool(payload["fallback"]),
                    latency_ms=int(payload["latency_ms"]),
                    feedback=FeedbackRating(str(payload.get("feedback", "unknown"))),
                )
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return tuple(events)
