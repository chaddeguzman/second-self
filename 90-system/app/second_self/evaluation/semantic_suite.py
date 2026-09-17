"""Synthetic semantic-recall quality cases using a deterministic fake embedder."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

from ..core.paths import SecondSelfPaths
from ..reads.recall import hybrid_recall_layer1
from ..reads.semantic import SemanticError, SemanticIndex, layer1_documents
from .models import EvalAssertion, EvalCase, EvalFixture, EvalSuite


class _SyntheticEmbedder:
    model_id = "synthetic-semantic-v1"

    def __init__(self, vectors: Mapping[str, Sequence[float]], query: Sequence[float], query_text: str):
        self._vectors = vectors
        self._query = tuple(float(value) for value in query)
        self._query_text = query_text

    def embed(self, text: str) -> Sequence[float]:
        if text == self._query_text:
            return self._query
        return tuple(float(value) for value in self._vectors[text])


class _UnavailableEmbedder:
    model_id = "unavailable"

    def embed(self, _text: str) -> Sequence[float]:
        raise SemanticError("synthetic model unavailable")


def _evaluate(fixture: Mapping[str, object]) -> Mapping[str, object]:
    notes = fixture.get("notes")
    query = fixture.get("query")
    query_vector = fixture.get("query_vector")
    expected = fixture.get("expected_sources")
    conflict_expected = fixture.get("conflict_expected", False)
    if not isinstance(notes, list) or not isinstance(query, str):
        raise ValueError("synthetic semantic fixture is invalid")
    if not isinstance(query_vector, list) or not isinstance(expected, list):
        raise ValueError("synthetic semantic fixture is invalid")

    with TemporaryDirectory(prefix="second-self-semantic-eval-") as temp:
        root = Path(temp)
        paths = SecondSelfPaths(root / "repo", root / "data")
        vectors: dict[str, Sequence[float]] = {}
        for note in notes:
            if not isinstance(note, Mapping):
                raise ValueError("synthetic semantic fixture is invalid")
            relative = note.get("path")
            body = note.get("body")
            vector = note.get("vector")
            if not all(isinstance(value, str) for value in (relative, body)):
                raise ValueError("synthetic semantic fixture is invalid")
            if not isinstance(vector, list):
                raise ValueError("synthetic semantic fixture is invalid")
            target = paths.layer1 / Path(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n"
                f"# {target.stem}\n\n{body}\n",
                encoding="utf-8",
            )
        documents = layer1_documents(paths)
        for document in documents:
            note = next(
                item for item in notes if document.path.endswith(str(item["path"]))
            )
            vectors[document.text] = note["vector"]
        embedder = _SyntheticEmbedder(vectors, query_vector, query)
        index = SemanticIndex(paths.cache / "semantic" / "index.sqlite3")
        index.refresh(documents, embedder)
        results = hybrid_recall_layer1(
            paths,
            query,
            semantic_index=index,
            embedder=embedder,
            max_results=len(expected),
        )
        returned = [str(item["path"]) for item in results]
        repeated = [
            str(item["path"])
            for item in hybrid_recall_layer1(
                paths,
                query,
                semantic_index=index,
                embedder=embedder,
                max_results=len(expected),
            )
        ]
    conflict_ok = (
        any(bool(item.get("conflict_review")) for item in results)
        if conflict_expected
        else not any(bool(item.get("conflict_review")) for item in results)
    )
    return {
        "top_match": returned[0] if returned else "",
        "returned_sources": returned,
        "expected_sources": expected,
        "top_match_ok": bool(returned) and returned[0] == expected[0],
        "coverage_ok": all(source in returned for source in expected),
        "deterministic_ok": returned == repeated,
        "conflict_ok": conflict_ok,
        "_metrics": {
            "top_match_accuracy": float(bool(returned) and returned[0] == expected[0]),
            "source_coverage": (
                sum(source in returned for source in expected) / len(expected)
                if expected
                else 1.0
            ),
        },
    }


def _evaluate_index_health(fixture: Mapping[str, object]) -> Mapping[str, object]:
    """Exercise aggregate freshness and corrupt-vector safety with synthetic data."""
    if fixture.get("body") != "synthetic index health":
        raise ValueError("synthetic semantic fixture is invalid")
    with TemporaryDirectory(prefix="second-self-semantic-health-") as temp:
        root = Path(temp)
        paths = SecondSelfPaths(root / "repo", root / "data")
        target = paths.layer1 / "00 Memory" / "Health.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("synthetic index health", encoding="utf-8")
        documents = layer1_documents(paths)
        embedder = _SyntheticEmbedder(
            {document.text: (1.0,) for document in documents}, (1.0,), "health"
        )
        index = SemanticIndex(paths.cache / "semantic" / "index.sqlite3")
        index.refresh(documents, embedder)
        target.write_text("synthetic index health changed", encoding="utf-8")
        stale = index.status(layer1_documents(paths), model_id=embedder.model_id)
        connection = sqlite3.connect(paths.cache / "semantic" / "index.sqlite3")
        connection.execute(
            "INSERT INTO semantic_documents VALUES (?, ?, ?, ?, ?)",
            ("corrupt.md", "synthetic", "hash", embedder.model_id, b"bad"),
        )
        connection.commit()
        connection.close()
        corrupt_safe = all(match.path != "corrupt.md" for match in index.search((1.0,)))
        return {
            "stale_detected": stale.changed == 1,
            "corrupt_safe": corrupt_safe,
            "status_safe": set(stale.as_dict()) == {
                "indexed", "expected", "changed", "missing", "model_mismatch",
                "ready", "fallback_reason",
            },
            "_metrics": {
                "stale_detection": float(stale.changed == 1),
                "corrupt_index_safety": float(corrupt_safe),
            },
        }


def _evaluate_fallback(fixture: Mapping[str, object]) -> Mapping[str, object]:
    notes = fixture.get("notes")
    expected = fixture.get("expected_sources")
    if not isinstance(notes, list) or not isinstance(expected, list):
        raise ValueError("synthetic semantic fixture is invalid")
    with TemporaryDirectory(prefix="second-self-semantic-fallback-") as temp:
        root = Path(temp)
        paths = SecondSelfPaths(root / "repo", root / "data")
        for note in notes:
            if not isinstance(note, Mapping):
                raise ValueError("synthetic semantic fixture is invalid")
            relative = note.get("path")
            body = note.get("body")
            if not isinstance(relative, str) or not isinstance(body, str):
                raise ValueError("synthetic semantic fixture is invalid")
            target = paths.layer1 / Path(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n"
                f"# {target.stem}\n\n{body}\n",
                encoding="utf-8",
            )
        results = hybrid_recall_layer1(
            paths,
            str(fixture.get("query", "")),
            semantic_index=SemanticIndex(paths.cache / "semantic" / "index.sqlite3"),
            embedder=_UnavailableEmbedder(),
        )
        returned = [str(item["path"]) for item in results]
    return {
        "fallback_ok": bool(returned) and returned[0] == expected[0],
        "_metrics": {"fallback_accuracy": float(bool(returned) and returned[0] == expected[0])},
    }


def _case(case_id: str, fixture: dict[str, object], evaluator=_evaluate) -> EvalCase:
    if evaluator is _evaluate:
        fields = ("top_match_ok", "coverage_ok", "deterministic_ok")
        if fixture.get("conflict_expected"):
            fields += ("conflict_ok",)
    elif evaluator is _evaluate_fallback:
        fields = ("fallback_ok",)
    else:
        fields = ("stale_detected", "corrupt_safe", "status_safe")
    return EvalCase(
        case_id,
        EvalFixture(True, data=fixture),
        evaluator,
        tuple(EvalAssertion(field, True) for field in fields),
    )


SEMANTIC_SUITE = EvalSuite(
    "semantic",
    (
        _case(
            "paraphrase",
            {
                "query": "__query__",
                "query_vector": [1.0, 0.0],
                "notes": [
                    {"path": "00 Memory/Identity Delay.md", "body": "I freeze when work feels tied to identity.", "vector": [1.0, 0.0]},
                    {"path": "02 Journal/Unrelated.md", "body": "A fictional unrelated note.", "vector": [0.0, 1.0]},
                ],
                "expected_sources": ["01-strategy-storage/00 Memory/Identity Delay.md"],
            },
        ),
        _case(
            "related-concept",
            {
                "query": "__query__",
                "query_vector": [0.95, 0.05],
                "notes": [
                    {"path": "03 Strategy/High Stakes.md", "body": "Important projects can trigger avoidance.", "vector": [1.0, 0.0]},
                    {"path": "05 Reviews/Old Review.md", "body": "A fictional old review.", "vector": [0.0, 1.0]},
                ],
                "expected_sources": ["01-strategy-storage/03 Strategy/High Stakes.md"],
            },
        ),
        _case(
            "weak-match-rejection",
            {
                "query": "__query__",
                "query_vector": [1.0, 0.0],
                "notes": [
                    {"path": "00 Memory/Short Plans.md", "body": "I prefer short plans.", "vector": [1.0, 0.0]},
                    {"path": "04 References/Weak.md", "body": "A weakly related note.", "vector": [0.0, 1.0]},
                ],
                "expected_sources": ["01-strategy-storage/00 Memory/Short Plans.md"],
            },
        ),
        _case(
            "contradictory-sources-preserved",
            {
                "query": "__query__",
                "query_vector": [1.0, 0.0],
                "notes": [
                    {"path": "02 Journal/Morning.md", "body": "I prefer mornings.", "vector": [1.0, 0.0]},
                    {"path": "02 Journal/Night.md", "body": "I now prefer nights.", "vector": [0.8, 0.6]},
                ],
                "expected_sources": [
                    "01-strategy-storage/02 Journal/Morning.md",
                    "01-strategy-storage/02 Journal/Night.md",
                ],
            },
        ),
        _case(
            "model-unavailable-keyword-fallback",
            {
                "query": "identity",
                "notes": [
                    {"path": "00 Memory/Identity.md", "body": "Identity is important context."},
                    {"path": "02 Journal/Other.md", "body": "An unrelated note."},
                ],
                "expected_sources": ["01-strategy-storage/00 Memory/Identity.md"],
            },
            _evaluate_fallback,
        ),
        _case(
            "exact-keyword-beats-weak-semantic",
            {
                "query": "identity",
                "query_vector": [0.0, 1.0],
                "notes": [
                    {"path": "00 Memory/Identity.md", "body": "Identity is important context.", "vector": [1.0, 0.0]},
                    {"path": "04 References/Weak.md", "body": "A weakly related note.", "vector": [0.0, 1.0]},
                ],
                "expected_sources": ["01-strategy-storage/00 Memory/Identity.md"],
            },
        ),
        _case(
            "conflict-review-flag",
            {
                "query": "mornings",
                "query_vector": [1.0, 0.0],
                "notes": [
                    {"path": "03 Strategy/01 Conflicts/Morning.md", "body": "I prefer mornings.", "vector": [1.0, 0.0]},
                    {"path": "03 Strategy/01 Conflicts/Night.md", "body": "I now prefer nights.", "vector": [0.9, 0.1]},
                ],
                "expected_sources": ["01-strategy-storage/03 Strategy/01 Conflicts/Morning.md"],
                "conflict_expected": True,
            },
        ),
        _case(
            "stale-and-corrupt-index-safety",
            {"body": "synthetic index health"},
            _evaluate_index_health,
        ),
    ),
)
