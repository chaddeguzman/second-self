"""Payload-free explanations for evidence-aware recall results."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _retrieval_mode(results: Sequence[Mapping[str, object]], *, fallback: bool) -> str:
    modes = {str(item.get("retrieval", "none")) for item in results}
    modes.discard("none")
    if len(modes) > 1:
        return "hybrid"
    return next(iter(modes), "keyword" if fallback else "none")


def _evidence(results: Sequence[Mapping[str, object]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for item in results:
        score = item.get("score")
        evidence.append(
            {
                "title": str(item.get("title", "Untitled source")),
                "provenance": str(item.get("provenance", "unknown")),
                "retrieval": str(item.get("retrieval", "unknown")),
                "score": score if isinstance(score, (int, float)) else None,
                "conflict_review": bool(item.get("conflict_review", False)),
            }
        )
    return evidence


def build_report(
    results: Sequence[Mapping[str, object]], *, fallback: bool
) -> dict[str, Any]:
    evidence = _evidence(results)
    conflicts = any(item["conflict_review"] for item in evidence)
    result_count = len(evidence)
    if result_count == 0:
        answer = "No matching evidence was found."
        uncertainty = "The available sources did not support an answer."
        next_action = "Broaden the query or verify the source manually."
    else:
        noun = "result" if result_count == 1 else "results"
        answer = f"Found {result_count} relevant source-backed {noun}."
        uncertainty = (
            "Conflicting claims require review."
            if conflicts
            else "No unresolved conflict was detected in the returned evidence."
        )
        next_action = (
            "Prepare a conflict review before treating the result as settled."
            if conflicts
            else "Review cited evidence before treating the result as confirmed."
        )
    return {
        "version": "retrieval-explanation/v1",
        "answer": answer,
        "evidence": evidence,
        "retrieval_mode": _retrieval_mode(results, fallback=fallback),
        "capability_status": "degraded" if fallback else "available",
        "uncertainty": uncertainty,
        "next_action": next_action,
    }
