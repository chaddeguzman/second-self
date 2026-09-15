"""Fictional recall-quality suite that exercises the real ranked recall path."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

from ..core.paths import SecondSelfPaths
from ..reads.recall import recall_layer1
from .models import EvalAssertion, EvalCase, EvalFixture, EvalSuite

RECALL_THRESHOLDS = {
    "retrieval_precision": 0.5,
    "expected_source_coverage": 1.0,
    "source_attribution": 1.0,
    "evidence_label_correctness": 1.0,
    "missing_evidence_behavior": 1.0,
    "contradiction_surfacing": 1.0,
    "ranking_accuracy": 1.0,
}
METRIC_ASSERTIONS = tuple(
    EvalAssertion(f"{name}_ok", True) for name in RECALL_THRESHOLDS
)
ALLOWED_FOLDERS = {
    "00 Memory",
    "01 Capture",
    "02 Journal",
    "03 Strategy",
    "04 References",
    "05 Reviews",
}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError("synthetic recall fixture is invalid")
    return value


def _write_notes(paths: SecondSelfPaths, notes: object) -> dict[str, str]:
    if not isinstance(notes, list):
        raise ValueError("synthetic recall fixture is invalid")
    dates: dict[str, str] = {}
    for note in notes:
        if not isinstance(note, Mapping):
            raise ValueError("synthetic recall fixture is invalid")
        relative = note.get("path")
        created = note.get("created")
        body = note.get("body")
        tags = note.get("tags", [])
        if not all(isinstance(value, str) for value in (relative, created, body)):
            raise ValueError("synthetic recall fixture is invalid")
        assert isinstance(relative, str) and isinstance(created, str)
        assert isinstance(body, str)
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or len(pure.parts) < 2:
            raise ValueError("synthetic recall fixture is invalid")
        if pure.parts[0] not in ALLOWED_FOLDERS or pure.suffix != ".md":
            raise ValueError("synthetic recall fixture is invalid")
        date.fromisoformat(created)
        tag_values = _string_list(tags)
        full_relative = f"01-strategy-storage/{pure.as_posix()}"
        target = paths.layer1 / Path(*pure.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "---\n"
            "type: note\n"
            f"created: {created}\n"
            f"tags: [{', '.join(tag_values)}]\n"
            "---\n\n"
            f"# {pure.stem}\n\n{body}\n",
            encoding="utf-8",
        )
        dates[full_relative] = created
    return dates


def _score_ratio(expected: set[object], observed: set[object]) -> float:
    if not expected and not observed:
        return 1.0
    union = expected | observed
    return len(expected & observed) / len(union) if union else 1.0


def evaluate_recall_fixture(fixture: Mapping[str, object]) -> Mapping[str, object]:
    """Run actual recall on a temporary fictional vault and score representation."""
    query = fixture.get("query")
    today_raw = fixture.get("today")
    response = fixture.get("response")
    if not isinstance(query, str) or not isinstance(today_raw, str):
        raise ValueError("synthetic recall fixture is invalid")
    if not isinstance(response, Mapping):
        raise ValueError("synthetic recall fixture is invalid")
    expected_sources = _string_list(fixture.get("expected_sources"))
    expected_order = _string_list(fixture.get("expected_order", expected_sources))
    expected_labels = _string_list(fixture.get("expected_labels"))
    contradiction_expected = fixture.get("contradiction_expected", False)
    if not isinstance(contradiction_expected, bool):
        raise ValueError("synthetic recall fixture is invalid")

    with TemporaryDirectory(prefix="second-self-synthetic-eval-") as temp:
        root = Path(temp)
        paths = SecondSelfPaths(root / "repo", root / "data")
        dates = _write_notes(paths, fixture.get("notes"))
        results = recall_layer1(paths, query, today=date.fromisoformat(today_raw))

    returned = [str(item["path"]) for item in results]
    relevant = set(expected_sources)
    returned_set = set(returned)
    precision = len(relevant & returned_set) / len(returned) if returned else float(not relevant)
    coverage = len(relevant & returned_set) / len(relevant) if relevant else float(not returned)

    findings = response.get("findings")
    if not isinstance(findings, list):
        raise ValueError("synthetic recall fixture is invalid")
    labels: list[str] = []
    inference_reasons_valid = True
    citations: set[tuple[str, str]] = set()
    for finding in findings:
        if not isinstance(finding, Mapping) or not isinstance(finding.get("label"), str):
            raise ValueError("synthetic recall fixture is invalid")
        labels.append(str(finding["label"]))
        if finding["label"] == "inferred" and (
            not isinstance(finding.get("reason"), str)
            or not str(finding["reason"]).strip()
        ):
            inference_reasons_valid = False
        raw_citations = finding.get("citations", [])
        if not isinstance(raw_citations, list):
            raise ValueError("synthetic recall fixture is invalid")
        for citation in raw_citations:
            if not isinstance(citation, Mapping):
                raise ValueError("synthetic recall fixture is invalid")
            path_value = citation.get("path")
            date_value = citation.get("date")
            if not isinstance(path_value, str) or not isinstance(date_value, str):
                raise ValueError("synthetic recall fixture is invalid")
            citations.add((path_value, date_value))

    expected_citations = {(path, dates[path]) for path in expected_sources}
    attribution = _score_ratio(expected_citations, citations)
    label_score = float(labels == expected_labels and inference_reasons_valid)
    missing_score = 1.0
    if not relevant:
        missing_score = float(
            not returned and labels == ["not_found"] and not citations
        )
    contradiction_value = response.get("contradiction", False)
    contradiction_score = float(
        isinstance(contradiction_value, bool)
        and contradiction_value is contradiction_expected
        and (
            not contradiction_expected
            or all(path in {item[0] for item in citations} for path in relevant)
        )
    )
    ranking_score = (
        sum(
            index < len(returned) and returned[index] == expected
            for index, expected in enumerate(expected_order)
        )
        / len(expected_order)
        if expected_order
        else 1.0
    )
    metrics = {
        "retrieval_precision": precision,
        "expected_source_coverage": coverage,
        "source_attribution": attribution,
        "evidence_label_correctness": label_score,
        "missing_evidence_behavior": missing_score,
        "contradiction_surfacing": contradiction_score,
        "ranking_accuracy": ranking_score,
    }
    return {
        **{f"{name}_ok": value >= RECALL_THRESHOLDS[name] for name, value in metrics.items()},
        "_metrics": metrics,
    }


def _citation(path: str, created: str) -> dict[str, str]:
    return {"path": path, "date": created}


def _case(case_id: str, fixture: dict[str, object]) -> EvalCase:
    return EvalCase(
        case_id,
        EvalFixture(True, data=fixture),
        evaluate_recall_fixture,
        METRIC_ASSERTIONS,
    )


RECALL_SUITE = EvalSuite(
    "recall",
    (
        _case(
            "exact-title-confirmed",
            {
                "query": "starling protocol",
                "today": "2026-06-01",
                "notes": [{"path": "00 Memory/Starling Protocol.md", "created": "2026-05-01", "tags": [], "body": "The fictional protocol uses amber cards."}],
                "expected_sources": ["01-strategy-storage/00 Memory/Starling Protocol.md"],
                "expected_labels": ["confirmed"],
                "response": {"findings": [{"label": "confirmed", "citations": [_citation("01-strategy-storage/00 Memory/Starling Protocol.md", "2026-05-01")]}], "contradiction": False},
            },
        ),
        _case(
            "folder-priority",
            {
                "query": "lumen map",
                "today": "2026-06-01",
                "notes": [
                    {"path": "00 Memory/Lumen Memory.md", "created": "2026-05-01", "tags": [], "body": "The lumen map uses teal squares."},
                    {"path": "04 References/03 research/Lumen Reference.md", "created": "2026-05-01", "tags": [], "body": "The lumen map uses a fictional grid."},
                ],
                "expected_sources": ["01-strategy-storage/04 References/03 research/Lumen Reference.md", "01-strategy-storage/00 Memory/Lumen Memory.md"],
                "expected_order": ["01-strategy-storage/04 References/03 research/Lumen Reference.md", "01-strategy-storage/00 Memory/Lumen Memory.md"],
                "expected_labels": ["confirmed", "confirmed"],
                "response": {"findings": [
                    {"label": "confirmed", "citations": [_citation("01-strategy-storage/04 References/03 research/Lumen Reference.md", "2026-05-01")]},
                    {"label": "confirmed", "citations": [_citation("01-strategy-storage/00 Memory/Lumen Memory.md", "2026-05-01")]},
                ], "contradiction": False},
            },
        ),
        _case(
            "tagged-with-weak-competition",
            {
                "query": "quartz-route",
                "today": "2026-06-01",
                "notes": [
                    {"path": "02 Journal/Tagged Route.md", "created": "2026-05-20", "tags": ["quartz-route"], "body": "A fictional tagged decision."},
                    {"path": "04 References/03 research/Weak Route.md", "created": "2024-01-01", "tags": [], "body": "A weak mention of quartz-route."},
                ],
                "expected_sources": ["01-strategy-storage/02 Journal/Tagged Route.md"],
                "expected_order": [],
                "expected_labels": ["confirmed"],
                "response": {"findings": [{"label": "confirmed", "citations": [_citation("01-strategy-storage/02 Journal/Tagged Route.md", "2026-05-20")]}], "contradiction": False},
            },
        ),
        _case(
            "deterministic-tie-order",
            {
                "query": "ember signal",
                "today": "2026-06-01",
                "notes": [
                    {"path": "05 Reviews/Alpha Record.md", "created": "2026-05-01", "tags": [], "body": "A fictional ember signal record."},
                    {"path": "05 Reviews/Zeta Record.md", "created": "2026-05-01", "tags": [], "body": "Another fictional ember signal record."},
                ],
                "expected_sources": ["01-strategy-storage/05 Reviews/Zeta Record.md", "01-strategy-storage/05 Reviews/Alpha Record.md"],
                "expected_order": ["01-strategy-storage/05 Reviews/Zeta Record.md", "01-strategy-storage/05 Reviews/Alpha Record.md"],
                "expected_labels": ["confirmed", "confirmed"],
                "response": {"findings": [
                    {"label": "confirmed", "citations": [_citation("01-strategy-storage/05 Reviews/Zeta Record.md", "2026-05-01")]},
                    {"label": "confirmed", "citations": [_citation("01-strategy-storage/05 Reviews/Alpha Record.md", "2026-05-01")]},
                ], "contradiction": False},
            },
        ),
        _case(
            "recent-date-order",
            {
                "query": "violet beacon",
                "today": "2026-06-01",
                "notes": [
                    {"path": "02 Journal/Old Beacon.md", "created": "2024-01-01", "tags": [], "body": "A violet beacon note."},
                    {"path": "02 Journal/New Beacon.md", "created": "2026-05-30", "tags": [], "body": "A violet beacon update."},
                ],
                "expected_sources": ["01-strategy-storage/02 Journal/New Beacon.md", "01-strategy-storage/02 Journal/Old Beacon.md"],
                "expected_order": ["01-strategy-storage/02 Journal/New Beacon.md", "01-strategy-storage/02 Journal/Old Beacon.md"],
                "expected_labels": ["confirmed", "confirmed"],
                "response": {"findings": [
                    {"label": "confirmed", "citations": [_citation("01-strategy-storage/02 Journal/New Beacon.md", "2026-05-30")]},
                    {"label": "confirmed", "citations": [_citation("01-strategy-storage/02 Journal/Old Beacon.md", "2024-01-01")]},
                ], "contradiction": False},
            },
        ),
        _case(
            "labeled-inference",
            {
                "query": "cobalt garden",
                "today": "2026-06-01",
                "notes": [{"path": "03 Strategy/Cobalt Garden.md", "created": "2026-04-12", "tags": [], "body": "The fictional cobalt garden favors quiet paths."}],
                "expected_sources": ["01-strategy-storage/03 Strategy/Cobalt Garden.md"],
                "expected_labels": ["inferred"],
                "response": {"findings": [{"label": "inferred", "reason": "The quiet paths suggest, but do not directly state, a preference.", "citations": [_citation("01-strategy-storage/03 Strategy/Cobalt Garden.md", "2026-04-12")]}], "contradiction": False},
            },
        ),
        _case(
            "missing-evidence",
            {
                "query": "nonexistent silver orchard",
                "today": "2026-06-01",
                "notes": [{"path": "00 Memory/Unrelated.md", "created": "2026-05-01", "tags": [], "body": "Only an unrelated fictional note."}],
                "expected_sources": [],
                "expected_labels": ["not_found"],
                "response": {"findings": [{"label": "not_found", "citations": []}], "contradiction": False},
            },
        ),
        _case(
            "contradictory-dated-sources",
            {
                "query": "orbit plan",
                "today": "2026-06-01",
                "notes": [
                    {"path": "02 Journal/Orbit Earlier.md", "created": "2026-03-01", "tags": [], "body": "The orbit plan uses a blue gate."},
                    {"path": "02 Journal/Orbit Later.md", "created": "2026-05-25", "tags": [], "body": "The orbit plan does not use a blue gate."},
                ],
                "expected_sources": ["01-strategy-storage/02 Journal/Orbit Later.md", "01-strategy-storage/02 Journal/Orbit Earlier.md"],
                "expected_order": ["01-strategy-storage/02 Journal/Orbit Later.md", "01-strategy-storage/02 Journal/Orbit Earlier.md"],
                "expected_labels": ["confirmed", "confirmed"],
                "contradiction_expected": True,
                "response": {"findings": [
                    {"label": "confirmed", "citations": [_citation("01-strategy-storage/02 Journal/Orbit Later.md", "2026-05-25")]},
                    {"label": "confirmed", "citations": [_citation("01-strategy-storage/02 Journal/Orbit Earlier.md", "2026-03-01")]},
                ], "contradiction": True},
            },
        ),
    ),
)
