from __future__ import annotations

import sqlite3

import pytest

from second_self.reads.semantic import (
    FastEmbedder,
    SemanticDocument,
    SemanticError,
    SemanticIndex,
    layer1_documents,
    memory_store_documents,
)
from second_self.reads.recall import hybrid_recall, hybrid_recall_layer1


class FakeEmbedder:
    model_id = "synthetic-v1"

    def __init__(self, vectors: dict[str, tuple[float, ...]]) -> None:
        self.vectors = vectors

    def embed(self, text: str) -> tuple[float, ...]:
        return self.vectors[text]


def document(path: str, text: str) -> SemanticDocument:
    return SemanticDocument.from_text(path, "synthetic", text)


def test_refresh_and_search_store_metadata_only(tmp_path):
    index = SemanticIndex(tmp_path / "semantic" / "index.sqlite3")
    embedder = FakeEmbedder({"identity delay": (1.0, 0.0), "morning work": (0.0, 1.0)})

    assert index.refresh(
        [document("00 Memory/identity.md", "identity delay"), document("04 References/work.md", "morning work")],
        embedder,
    ) == 2
    matches = index.search((1.0, 0.0))

    assert [match.path for match in matches] == ["00 Memory/identity.md", "04 References/work.md"]
    assert matches[0].score == pytest.approx(1.0)
    assert index.count() == 2
    raw = (tmp_path / "semantic" / "index.sqlite3").read_bytes()
    assert b"identity delay" not in raw


def test_refresh_removes_deleted_sources(tmp_path):
    index = SemanticIndex(tmp_path / "index.sqlite3")
    embedder = FakeEmbedder({"one": (1.0,), "two": (0.0,)})
    index.refresh([document("one.md", "one"), document("two.md", "two")], embedder)
    index.refresh([document("one.md", "one")], embedder)

    assert index.count() == 1
    assert [match.path for match in index.search((1.0,))] == ["one.md"]


def test_refresh_rejects_duplicate_paths(tmp_path):
    index = SemanticIndex(tmp_path / "index.sqlite3")
    embedder = FakeEmbedder({"one": (1.0,)})

    with pytest.raises(SemanticError):
        index.refresh([document("same.md", "one"), document("same.md", "one")], embedder)


def test_status_is_read_only_when_index_is_absent(tmp_path):
    index_path = tmp_path / "missing" / "index.sqlite3"
    index = SemanticIndex(index_path)

    status = index.status([document("one.md", "one")], model_id="synthetic-v1")

    assert status.fallback_reason == "semantic-index-empty"
    assert not index_path.exists()


def test_failed_refresh_preserves_previous_index(tmp_path):
    index = SemanticIndex(tmp_path / "index.sqlite3")
    good = FakeEmbedder({"one": (1.0,)})
    index.refresh([document("one.md", "one")], good)

    class FailingEmbedder(FakeEmbedder):
        def embed(self, text):
            if text == "two":
                raise RuntimeError("synthetic failure")
            return super().embed(text)

    with pytest.raises(SemanticError):
        index.refresh(
            [document("one.md", "one"), document("two.md", "two")],
            FailingEmbedder({"one": (1.0,), "two": (0.0,)}),
        )

    assert [match.path for match in index.search((1.0,))] == ["one.md"]


def test_malformed_vectors_are_skipped(tmp_path):
    index_path = tmp_path / "index.sqlite3"
    index = SemanticIndex(index_path)
    assert index.count() == 0
    connection = sqlite3.connect(index_path)
    connection.execute(
        "INSERT INTO semantic_documents VALUES (?, ?, ?, ?, ?)",
        ("bad.md", "synthetic", "hash", "synthetic-v1", b"bad"),
    )
    connection.commit()
    connection.close()

    assert index.search((1.0,)) == []


def test_fastembedder_fails_safely_when_optional_dependency_is_missing(monkeypatch):
    embedder = FastEmbedder()
    monkeypatch.setattr(embedder, "_load", lambda: (_ for _ in ()).throw(SemanticError("unavailable")))

    with pytest.raises(SemanticError, match="unavailable"):
        embedder.embed("synthetic text")


def test_hybrid_recall_can_return_a_semantic_only_layer1_match(second_self):
    note_path = second_self.layer1 / "00 Memory" / "Identity Delay.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(
        "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n"
        "# Identity Delay\n\nI freeze when a project feels tied to my identity.\n",
        encoding="utf-8",
    )
    docs = layer1_documents(second_self)
    embedder = FakeEmbedder(
        {
            doc.text: ((1.0, 0.0) if doc.path.endswith("Identity Delay.md") else (0.0, 1.0))
            for doc in docs
        }
        | {"why freeze": (1.0, 0.0)}
    )
    index = SemanticIndex(second_self.cache / "semantic" / "index.sqlite3")
    index.refresh(docs, embedder)

    results = hybrid_recall_layer1(
        second_self,
        "why freeze",
        semantic_index=index,
        embedder=embedder,
    )

    assert results[0]["path"].endswith("00 Memory/Identity Delay.md")
    assert results[0]["retrieval"] == "semantic"


def test_status_reports_changed_missing_and_model_mismatch(tmp_path):
    index = SemanticIndex(tmp_path / "index.sqlite3")
    embedder = FakeEmbedder({"one": (1.0,), "two": (1.0,)})
    index.refresh([document("one.md", "one"), document("two.md", "two")], embedder)

    status = index.status(
        [document("one.md", "changed"), document("three.md", "one")],
        model_id="other-model",
    )

    assert status.indexed == 2
    assert status.expected == 2
    assert status.changed == 1
    assert status.missing == 1
    assert status.model_mismatch is True
    assert status.ready is False


def test_memory_store_documents_excludes_staging_and_sessions(tmp_path):
    root = tmp_path / "90-system" / ".echo" / "memory"
    (root / "staging").mkdir(parents=True)
    (root / "sessions").mkdir(parents=True)
    (root / "durable.md").write_text("durable", encoding="utf-8")
    (root / "staging" / "pending.md").write_text("private pending", encoding="utf-8")
    (root / "sessions" / "session.md").write_text("private session", encoding="utf-8")

    documents = memory_store_documents(tmp_path)

    assert [item.path for item in documents] == ["memory/durable.md"]


def test_unified_hybrid_recall_returns_memory_provenance_and_conflict_flag(second_self):
    layer1_note = second_self.layer1 / "00 Memory" / "Identity Delay.md"
    layer1_note.parent.mkdir(parents=True, exist_ok=True)
    layer1_note.write_text(
        "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n"
        "# Identity Delay\n\nA semantic-only Layer 1 match.\n",
        encoding="utf-8",
    )
    memory = second_self.repo_root / "90-system" / ".echo" / "memory"
    memory.mkdir(parents=True, exist_ok=True)
    (memory / "conflict-note.md").write_text("identity and delay", encoding="utf-8")
    docs = layer1_documents(second_self) + memory_store_documents(second_self.repo_root)
    embedder = FakeEmbedder(
        {
            doc.text: ((1.0, 0.0) if doc.path.endswith(("Identity Delay.md", "conflict-note.md")) else (0.0, 1.0))
            for doc in docs
        }
        | {"why delay": (1.0, 0.0)}
    )
    index = SemanticIndex(second_self.cache / "semantic" / "index.sqlite3")
    index.refresh(docs, embedder)

    results = hybrid_recall(second_self, "why delay", semantic_index=index, embedder=embedder)

    layer1_results = [item for item in results if item["provenance"] == "layer1"]
    memory_results = [item for item in results if item["provenance"] == "memory"]
    assert any(item["retrieval"] == "semantic" for item in layer1_results)
    assert memory_results
    assert any("semantic_score" in item for item in memory_results)
    assert memory_results[0]["conflict_review"] is True


def test_unified_recall_falls_back_to_keyword_when_index_is_stale(second_self):
    note_path = second_self.layer1 / "00 Memory" / "Freshness.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(
        "---\ntype: note\ncreated: 2026-08-01\nstatus: active\n---\n\n"
        "# Freshness\n\nIndex freshness matters.\n",
        encoding="utf-8",
    )
    docs = layer1_documents(second_self)
    embedder = FakeEmbedder({doc.text: (1.0,) for doc in docs} | {"freshness": (1.0,)})
    index = SemanticIndex(second_self.cache / "semantic" / "index.sqlite3")
    index.refresh(docs, embedder)
    note_path.write_text(note_path.read_text(encoding="utf-8") + "Changed.", encoding="utf-8")

    results = hybrid_recall(second_self, "freshness", semantic_index=index, embedder=embedder)

    assert results[0]["retrieval"] == "keyword"
    assert all("semantic_score" not in result for result in results)


def test_unified_recall_flags_natural_language_conflicting_claims(second_self):
    memory = second_self.repo_root / "90-system" / ".echo" / "memory"
    memory.mkdir(parents=True, exist_ok=True)
    (memory / "morning.md").write_text("I prefer orbitalpha mornings.", encoding="utf-8")
    (memory / "night.md").write_text("I now prefer orbitalpha nights.", encoding="utf-8")

    results = hybrid_recall(second_self, "orbitalpha", max_results=50)
    flagged = [result for result in results if result["conflict_review"]]

    assert len(flagged) == 2
    assert all(result["conflict_reason"] == "conflicting claims require review" for result in flagged)
