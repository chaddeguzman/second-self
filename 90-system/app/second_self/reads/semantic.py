"""Local, rebuildable semantic index primitives.

The Markdown sources remain authoritative.  This module stores only private
derived metadata and vectors; callers provide the text to an embedder and the
index never persists that text.
"""

from __future__ import annotations

import hashlib
import math
import os
import sqlite3
import struct
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class SemanticError(RuntimeError):
    """Safe error raised at the semantic-memory boundary."""


class Embedder(Protocol):
    """Minimal embedding interface used by the derived index."""

    @property
    def model_id(self) -> str: ...

    def embed(self, text: str) -> Sequence[float]: ...


@dataclass(frozen=True, slots=True)
class SemanticDocument:
    """Private source text supplied transiently while rebuilding the index."""

    path: str
    source: str
    text: str
    content_hash: str

    @classmethod
    def from_text(cls, path: str, source: str, text: str) -> SemanticDocument:
        if not path or not source or not isinstance(text, str):
            raise ValueError("semantic document is invalid")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return cls(path, source, text, digest)


@dataclass(frozen=True, slots=True)
class SemanticMatch:
    """A ranked result containing no source text."""

    path: str
    source: str
    score: float


@dataclass(frozen=True, slots=True)
class SemanticIndexStatus:
    """Aggregate freshness state without exposing indexed source details."""

    indexed: int
    expected: int
    changed: int
    missing: int
    model_mismatch: bool
    fallback_reason: str = "semantic-index-ready"

    @property
    def ready(self) -> bool:
        return (
            self.expected > 0
            and self.indexed == self.expected
            and self.changed == 0
            and self.missing == 0
            and not self.model_mismatch
            and self.fallback_reason == "semantic-index-ready"
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "indexed": self.indexed,
            "expected": self.expected,
            "changed": self.changed,
            "missing": self.missing,
            "model_mismatch": self.model_mismatch,
            "ready": self.ready,
            "fallback_reason": self.fallback_reason,
        }


def _pack_vector(vector: Sequence[float]) -> bytes:
    values = tuple(float(value) for value in vector)
    if not values or any(not math.isfinite(value) for value in values):
        raise SemanticError("embedding vector is invalid")
    return struct.pack(f"<{len(values)}f", *values)


def _unpack_vector(payload: bytes) -> tuple[float, ...]:
    if not payload or len(payload) % 4:
        raise SemanticError("stored embedding vector is invalid")
    size = len(payload) // 4
    return struct.unpack(f"<{size}f", payload)


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return -1.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return -1.0
    return dot / (left_norm * right_norm)


class SemanticIndex:
    """SQLite-backed private index that can always be rebuilt from sources."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        self._initialize(connection)
        return connection

    @staticmethod
    def _initialize(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS semantic_documents (
                path TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                model_id TEXT NOT NULL,
                vector BLOB NOT NULL
            )
            """
        )
        connection.commit()

    def _read_connection(self) -> sqlite3.Connection | None:
        """Open existing state without creating or modifying it."""
        if not self.database_path.is_file():
            return None
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                f"file:{self.database_path.as_posix()}?mode=ro", uri=True
            )
            connection.execute(
                "SELECT path, content_hash, model_id FROM semantic_documents LIMIT 0"
            )
            return connection
        except sqlite3.Error:
            if connection is not None:
                connection.close()
            raise SemanticError("semantic index is corrupt") from None

    def refresh(
        self, documents: Iterable[SemanticDocument], embedder: Embedder
    ) -> int:
        """Replace indexed documents atomically without persisting source text."""
        if not isinstance(embedder.model_id, str) or not embedder.model_id.strip():
            raise SemanticError("embedding model is invalid")
        materialized = tuple(documents)
        paths = [document.path for document in materialized]
        if len(paths) != len(set(paths)):
            raise SemanticError("semantic document paths are duplicated")

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.NamedTemporaryFile(
            prefix=f"{self.database_path.stem}-", suffix=".sqlite3", dir=self.database_path.parent,
            delete=False,
        )
        temporary_path = Path(temporary.name)
        temporary.close()
        connection = sqlite3.connect(temporary_path)
        failed = False
        try:
            self._initialize(connection)
            with connection:
                for document in materialized:
                    vector = _pack_vector(embedder.embed(document.text))
                    connection.execute(
                        """
                        INSERT INTO semantic_documents
                            (path, source, content_hash, model_id, vector)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(path) DO UPDATE SET
                            source=excluded.source,
                            content_hash=excluded.content_hash,
                            model_id=excluded.model_id,
                            vector=excluded.vector
                        """,
                        (
                            document.path,
                            document.source,
                            document.content_hash,
                            embedder.model_id,
                            vector,
                        ),
                    )
                if paths:
                    placeholders = ",".join("?" for _ in paths)
                    connection.execute(
                        f"DELETE FROM semantic_documents WHERE path NOT IN ({placeholders})",
                        paths,
                    )
                else:
                    connection.execute("DELETE FROM semantic_documents")
        except Exception:
            failed = True
        finally:
            connection.close()
        if failed:
            temporary_path.unlink(missing_ok=True)
            raise SemanticError("semantic index refresh failed") from None
        try:
            os.replace(temporary_path, self.database_path)
        except OSError:
            temporary_path.unlink(missing_ok=True)
            raise SemanticError("semantic index replacement failed") from None
        return len(materialized)

    def search(
        self,
        query_vector: Sequence[float],
        *,
        max_results: int = 50,
        min_score: float = -1.0,
    ) -> list[SemanticMatch]:
        """Return metadata-only cosine matches in deterministic order."""
        if max_results < 1:
            return []
        query = tuple(float(value) for value in query_vector)
        connection = self._read_connection()
        if connection is None:
            return []
        try:
            rows = connection.execute(
                "SELECT path, source, vector FROM semantic_documents"
            ).fetchall()
        except sqlite3.Error:
            raise SemanticError("semantic index read failed") from None
        finally:
            connection.close()

        matches: list[SemanticMatch] = []
        for path, source, payload in rows:
            try:
                score = _cosine(query, _unpack_vector(payload))
            except (SemanticError, TypeError, ValueError):
                continue
            if score >= min_score:
                matches.append(SemanticMatch(str(path), str(source), score))
        matches.sort(key=lambda item: (-item.score, item.path.casefold()))
        return matches[:max_results]

    def count(self) -> int:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT COUNT(*) FROM semantic_documents"
            ).fetchone()
            return int(row[0]) if row else 0
        except sqlite3.Error:
            raise SemanticError("semantic index status failed") from None
        finally:
            connection.close()

    def status(
        self,
        documents: Iterable[SemanticDocument],
        *,
        model_id: str | None = None,
    ) -> SemanticIndexStatus:
        """Compare current source hashes to the private index by aggregate only."""
        expected = tuple(documents)
        current = {document.path: document for document in expected}
        try:
            connection = self._read_connection()
        except SemanticError:
            return SemanticIndexStatus(
                indexed=0,
                expected=len(current),
                changed=0,
                missing=len(current),
                model_mismatch=False,
                fallback_reason="semantic-index-corrupt",
            )
        if connection is None:
            return SemanticIndexStatus(
                indexed=0,
                expected=len(current),
                changed=0,
                missing=len(current),
                model_mismatch=False,
                fallback_reason="semantic-index-empty",
            )
        try:
            rows = connection.execute(
                "SELECT path, content_hash, model_id FROM semantic_documents"
            ).fetchall()
        except sqlite3.Error:
            return SemanticIndexStatus(
                indexed=0,
                expected=len(current),
                changed=0,
                missing=len(current),
                model_mismatch=False,
                fallback_reason="semantic-index-corrupt",
            )
        finally:
            connection.close()

        indexed = {str(path): (str(content_hash), str(index_model)) for path, content_hash, index_model in rows}
        changed = sum(
            1
            for path, document in current.items()
            if path in indexed and indexed[path][0] != document.content_hash
        )
        missing = sum(1 for path in current if path not in indexed)
        model_mismatch = bool(
            model_id
            and indexed
            and any(index_model != model_id for _hash, index_model in indexed.values())
        )
        reason = "semantic-index-ready"
        if model_mismatch:
            reason = "semantic-model-mismatch"
        elif changed or missing or len(indexed) != len(current):
            reason = "semantic-index-stale"
        elif not indexed:
            reason = "semantic-index-empty"
        return SemanticIndexStatus(
            indexed=len(indexed),
            expected=len(current),
            changed=changed,
            missing=missing,
            model_mismatch=model_mismatch,
            fallback_reason=reason,
        )


def _iter_markdown(root: Path) -> Iterable[tuple[Path, str]]:
    """Yield Markdown files below a private root without following links."""
    if not root.is_dir():
        return
    for directory, _directories, files in os.walk(root, followlinks=False):
        for name in files:
            if name.casefold().endswith(".md"):
                path = Path(directory) / name
                try:
                    yield path, path.relative_to(root).as_posix()
                except ValueError:
                    continue


def layer1_documents(paths) -> tuple[SemanticDocument, ...]:
    """Read Layer 1 source text transiently for a semantic rebuild."""
    documents: list[SemanticDocument] = []
    skipped = {"98-trash", "99-audit"}
    for path, relative in _iter_markdown(paths.layer1):
        if relative.split("/", 1)[0].casefold() in skipped:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        documents.append(
            SemanticDocument.from_text(f"layer1/{relative}", "layer1", text)
        )
    return tuple(documents)


def memory_store_documents(repo_root: Path) -> tuple[SemanticDocument, ...]:
    """Read durable ECHO memory only; staging and sessions are excluded."""
    root = repo_root / "90-system" / ".echo" / "memory"
    documents: list[SemanticDocument] = []
    for path, relative in _iter_markdown(root):
        if relative.casefold().startswith(("staging/", "sessions/")):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        documents.append(
            SemanticDocument.from_text(f"memory/{relative}", "memory", text)
        )
    return tuple(documents)


class FastEmbedder:
    """Optional in-process FastEmbed adapter using a small CPU model."""

    def __init__(self, model_id: str = "BAAI/bge-small-en-v1.5") -> None:
        self._model_id = model_id
        self._model = None

    @property
    def model_id(self) -> str:
        return self._model_id

    def _load(self):
        if self._model is None:
            try:
                try:
                    import truststore

                    truststore.inject_into_ssl()
                except ImportError:
                    pass
                from fastembed import TextEmbedding

                self._model = TextEmbedding(model_name=self._model_id)
            except Exception:
                raise SemanticError("embedded semantic model unavailable") from None
        return self._model

    def embed(self, text: str) -> Sequence[float]:
        if not isinstance(text, str) or not text.strip():
            raise SemanticError("semantic text is invalid")
        try:
            vector = next(iter(self._load().embed([text])))
            return tuple(float(value) for value in vector)
        except SemanticError:
            raise
        except Exception:
            raise SemanticError("embedded semantic model failed") from None
