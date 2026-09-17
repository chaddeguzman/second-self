from __future__ import annotations

import sqlite3

import pytest

from second_self.reads.semantic import (
    FastEmbedder,
    SemanticDocument,
    SemanticError,
    SemanticIndex,
    layer1_documents,
)
from second_self.reads.recall import hybrid_recall_layer1


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
