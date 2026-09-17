"""Ranked recall search across Layer 1 notes.

Scores results by folder priority, recency, tag strength (frontmatter tags
and body ``#tag`` mentions), and title match.  Higher score = more relevant.
"""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path
from typing import Any

from ..core.frontmatter import read_note
from ..core.paths import SecondSelfPaths
from .semantic import (
    Embedder,
    SemanticError,
    SemanticIndex,
    layer1_documents,
    memory_store_documents,
)

MAX_FILE_BYTES = 2 * 1024 * 1024
SNIPPET_RADIUS = 60
SKIPPED_DIRECTORIES = {"98-trash", "99-audit"}
EXCLUDED_FILES = {"tag registry.md"}

# Folder priority weights (higher = more important).
# 04 References ranks highest because most personal recall lives there;
# 00 Memory remains high for identity/values questions.
FOLDER_PRIORITY = {
    "04 references": 40,
    "00 memory": 30,
    "03 strategy": 25,
    "02 journal": 20,
    "05 reviews": 10,
    "01 capture": 5,
}

# Recency weights based on age in days.
RECENCY_BANDS = [
    (7, 30),
    (30, 20),
    (90, 10),
    (365, 5),
]

# Inline #tag mention in body text.
_INLINE_TAG_RE = re.compile(r"#([A-Za-z0-9_-]+)")
_CLAIM_RE = re.compile(
    r"\b(?:i|we)\s+(?:(?P<neg>do not|don't|never|cannot|can't)\s+)?"
    r"(?:now\s+)?(?P<verb>prefer|like|avoid|want|choose|dislike|hate)\s+"
    r"(?P<object>[^.!?\n]+)",
    re.IGNORECASE,
)


def _folder_priority(relative_path: str) -> int:
    """Return the folder priority weight for a Layer 1 note path."""
    first = relative_path.split("/", 1)[0].casefold()
    return FOLDER_PRIORITY.get(first, 0)


def _recency_score(created: date | None, today: date) -> int:
    """Return the recency weight based on note age."""
    if created is None:
        return 0
    age = (today - created).days
    if age < 0:
        return 0
    for days, weight in RECENCY_BANDS:
        if age <= days:
            return weight
    return 0


def _tag_score(tags: tuple[str, ...], body: str, query: str) -> int:
    """Return the tag strength weight.

    Exact frontmatter tag match = 20, partial frontmatter tag match = 10,
    body ``#tag`` mention = 5.
    """
    needle = query.casefold()
    for tag in tags:
        if tag.casefold() == needle:
            return 20
    for tag in tags:
        if needle in tag.casefold() or tag.casefold() in needle:
            return 10
    for match in _INLINE_TAG_RE.finditer(body):
        if match.group(1).casefold() == needle:
            return 5
    return 0


def _title_score(title: str, query: str) -> int:
    """Return 10 if the query appears in the title, else 0."""
    return 10 if query.casefold() in title.casefold() else 0


def _keyword_evidence(result: dict[str, Any]) -> float:
    """Return bounded lexical evidence, excluding folder and recency priority."""
    breakdown = result.get("score_breakdown", {})
    if isinstance(breakdown, dict) and (
        float(breakdown.get("title", 0)) > 0 or float(breakdown.get("tag", 0)) > 0
    ):
        return 1.0
    return 0.35 if result.get("matched") else 0.0


def _claim_profiles(text: str) -> list[tuple[str, bool, str]]:
    """Extract conservative preference/action claims for conflict flagging."""
    profiles: list[tuple[str, bool, str]] = []
    for match in _CLAIM_RE.finditer(text):
        obj = " ".join(match.group("object").casefold().split())
        profiles.append((match.group("verb").casefold(), bool(match.group("neg")), obj))
    return profiles


def _mark_conflicts(paths: SecondSelfPaths, results: list[dict[str, Any]]) -> None:
    """Mark returned results whose conservative claims conflict."""
    texts: dict[str, str] = {}
    for entry in results:
        public_path = str(entry.get("path", ""))
        if public_path.startswith("01-strategy-storage/"):
            source = paths.layer1 / Path(public_path.removeprefix("01-strategy-storage/"))
            try:
                texts[public_path] = source.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
        elif public_path.startswith("90-system/.echo/memory/"):
            source = paths.repo_root / public_path
            try:
                texts[public_path] = source.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue

    profiles = {
        path: _claim_profiles(text)
        for path, text in texts.items()
    }
    conflict_paths: set[str] = set()
    items = list(profiles.items())
    for index, (left_path, left_claims) in enumerate(items):
        for right_path, right_claims in items[index + 1 :]:
            for left_verb, left_neg, left_object in left_claims:
                for right_verb, right_neg, right_object in right_claims:
                    if left_verb != right_verb:
                        continue
                    objects_conflict = left_object != right_object
                    polarity_conflict = left_object == right_object and left_neg != right_neg
                    if objects_conflict or polarity_conflict:
                        conflict_paths.update((left_path, right_path))
    for entry in results:
        if str(entry.get("path", "")) in conflict_paths:
            entry["conflict_review"] = True
            entry["conflict_reason"] = "conflicting claims require review"


def _snippet(text: str, match_start: int, match_end: int) -> str:
    start = max(0, match_start - SNIPPET_RADIUS)
    end = min(len(text), match_end + SNIPPET_RADIUS)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


def _iter_layer1_notes(paths: SecondSelfPaths) -> list[tuple[Path, str]]:
    """Walk Layer 1 and return (path, relative_to_layer1) for each .md note."""
    root = paths.layer1
    if not root.is_dir():
        return []
    notes: list[tuple[Path, str]] = []
    try:
        walker = os.walk(root, followlinks=False)
        for directory, directories, files in walker:
            current = Path(directory)
            relative = current.relative_to(root)
            if relative == Path("."):
                directories[:] = [
                    name
                    for name in directories
                    if name.casefold() not in SKIPPED_DIRECTORIES
                ]
            for name in files:
                if not name.lower().endswith(".md"):
                    continue
                if name.casefold() in EXCLUDED_FILES:
                    continue
                path = current / name
                notes.append((path, path.relative_to(root).as_posix()))
    except OSError:
        return notes
    return notes


def recall_layer1(
    paths: SecondSelfPaths,
    query: str,
    *,
    max_results: int = 50,
    min_score: int = 0,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Ranked recall search across Layer 1 notes.

    Returns a list of result dicts sorted by score descending, then title.
    """
    query = query.strip()
    if not query:
        return []
    today = today or date.today()
    needle = query.casefold()

    results: list[dict[str, Any]] = []
    for path, relative in _iter_layer1_notes(paths):
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue

        # Parse frontmatter for tags and created date.
        tags: tuple[str, ...] = ()
        created: date | None = None
        try:
            metadata, body = read_note(path)
            raw_tags = metadata.get("tags")
            if isinstance(raw_tags, list):
                tags = tuple(
                    sorted(
                        {
                            str(tag).strip()
                            for tag in raw_tags
                            if isinstance(tag, str) and tag.strip()
                        }
                    )
                )
            created_raw = metadata.get("created")
            if isinstance(created_raw, date):
                created = created_raw
            elif isinstance(created_raw, str):
                try:
                    created = date.fromisoformat(created_raw[:10])
                except ValueError:
                    created = None
        except (OSError, UnicodeError, ValueError):
            body = text

        # Determine if the query matches anywhere.
        title_hit = needle in Path(relative).stem.casefold()
        tag_hit = _tag_score(tags, body, query) > 0
        body_index = body.casefold().find(needle)
        if not (title_hit or tag_hit or body_index != -1):
            continue

        folder = _folder_priority(relative)
        recency = _recency_score(created, today)
        tag = _tag_score(tags, body, query)
        title = _title_score(Path(relative).stem, query)
        score = folder + recency + tag + title

        if score < min_score:
            continue

        snippet = ""
        matched = ""
        if body_index != -1:
            snippet = _snippet(body, body_index, body_index + len(query))
            matched = body[body_index : body_index + len(query)]

        results.append(
            {
                "path": f"01-strategy-storage/{relative}",
                "title": Path(relative).stem,
                "score": score,
                "score_breakdown": {
                    "folder": folder,
                    "recency": recency,
                    "tag": tag,
                    "title": title,
                },
                "snippet": snippet,
                "matched": matched,
            }
        )

    results.sort(
        key=lambda entry: (entry["score"], str(entry["title"]).casefold()),
        reverse=True,
    )
    return results[:max_results]


def hybrid_recall_layer1(
    paths: SecondSelfPaths,
    query: str,
    *,
    semantic_index: SemanticIndex | None = None,
    embedder: Embedder | None = None,
    max_results: int = 50,
    min_score: int = 0,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Combine keyword recall with optional semantic index results.

    The keyword path remains authoritative when semantic dependencies are
    unavailable.  Semantic-only results are metadata-only until callers read
    the cited source through the normal evidence workflow.
    """
    keyword_results = recall_layer1(
        paths,
        query,
        max_results=max_results,
        min_score=min_score,
        today=today,
    )
    if semantic_index is None or embedder is None or not query.strip():
        return keyword_results
    try:
        status = semantic_index.status(
            layer1_documents(paths), model_id=embedder.model_id
        )
        if not status.ready:
            return keyword_results
        semantic_matches = semantic_index.search(
            embedder.embed(query), min_score=0.35
        )
    except (SemanticError, ValueError, TypeError):
        return keyword_results

    by_path = {str(item["path"]): item for item in keyword_results}
    current = today or date.today()
    for match in semantic_matches:
        if match.source != "layer1" or not match.path.startswith("layer1/"):
            continue
        path = match.path.removeprefix("layer1/")
        public_path = f"01-strategy-storage/{path}"
        existing = by_path.get(public_path)
        semantic_norm = max(0.0, min(1.0, float(match.score)))
        if existing is not None:
            keyword_score = float(existing["score"])
            keyword_norm = _keyword_evidence(existing)
            existing["semantic_score"] = round(match.score, 6)
            existing["keyword_score"] = round(keyword_score, 6)
            existing["score"] = round(keyword_norm * 70.0 + semantic_norm * 25.0, 6)
            existing["retrieval"] = "hybrid"
            existing["score_breakdown"]["semantic"] = round(semantic_norm * 25.0, 6)
            continue
        source_path = paths.layer1 / Path(path)
        try:
            metadata, _body = read_note(source_path)
        except (OSError, UnicodeError, ValueError):
            continue
        created = metadata.get("created")
        if isinstance(created, str):
            try:
                created = date.fromisoformat(created[:10])
            except ValueError:
                created = None
        recency = _recency_score(created if isinstance(created, date) else None, current)
        folder = _folder_priority(path)
        by_path[public_path] = {
            "path": public_path,
            "title": Path(path).stem,
            "score": round(semantic_norm * 25.0, 6),
            "score_breakdown": {
                "folder": folder,
                "recency": recency,
                "tag": 0,
                "title": 0,
                "keyword": 0,
                "semantic": round(semantic_norm * 25.0, 6),
            },
            "keyword_score": 0,
            "semantic_score": round(match.score, 6),
            "retrieval": "semantic",
            "snippet": "",
            "matched": "",
        }
    results = list(by_path.values())
    for entry in results:
        entry["conflict_review"] = "conflict" in str(entry.get("path", "")).casefold()
    results.sort(key=lambda entry: (float(entry["score"]), str(entry["title"]).casefold()), reverse=True)
    return results[:max_results]


def _memory_keyword_results(repo_root: Path, query: str, max_results: int) -> list[dict[str, Any]]:
    """Return metadata-only keyword hits from durable ECHO memory."""
    terms = tuple(term for term in re.findall(r"[\w-]+", query.casefold()) if term)
    results: list[dict[str, Any]] = []
    for document in memory_store_documents(repo_root):
        lowered = document.text.casefold()
        exact = query.casefold() in lowered
        overlap = sum(term in lowered for term in terms)
        if not exact and overlap == 0:
            continue
        keyword_score = 70.0 if exact else min(60.0, overlap * 12.0)
        results.append(
            {
                "path": f"90-system/.echo/memory/{document.path.removeprefix('memory/')}",
                "title": Path(document.path).stem,
                "score": round(keyword_score * 0.7, 6),
                "keyword_score": keyword_score,
                "score_breakdown": {"keyword": round(keyword_score * 0.7, 6), "semantic": 0},
                "retrieval": "keyword",
                "provenance": "memory",
                "conflict_review": "conflict" in document.path.casefold(),
                "snippet": "",
                "matched": "",
            }
        )
    results.sort(key=lambda entry: (float(entry["score"]), str(entry["title"]).casefold()), reverse=True)
    return results[:max_results]


def hybrid_recall(
    paths: SecondSelfPaths,
    query: str,
    *,
    semantic_index: SemanticIndex | None = None,
    embedder: Embedder | None = None,
    max_results: int = 50,
    min_score: int = 0,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Unified Layer 1 and durable ECHO-memory recall with safe fallback."""
    all_documents = layer1_documents(paths) + memory_store_documents(paths.repo_root)
    semantic_ready = semantic_index is not None and embedder is not None
    if semantic_ready:
        try:
            semantic_ready = semantic_index.status(
                all_documents, model_id=embedder.model_id
            ).ready
        except (SemanticError, ValueError, TypeError):
            semantic_ready = False
    active_index = semantic_index if semantic_ready else None
    active_embedder = embedder if semantic_ready else None
    results = hybrid_recall_layer1(
        paths,
        query,
        semantic_index=active_index,
        embedder=active_embedder,
        max_results=max_results,
        min_score=min_score,
        today=today,
    )
    for entry in results:
        entry.setdefault("provenance", "layer1")
        entry.setdefault("retrieval", "keyword")
        entry["conflict_review"] = "conflict" in str(entry.get("path", "")).casefold()
    memory_results = _memory_keyword_results(paths.repo_root, query, max_results)
    if active_index is not None and active_embedder is not None and query.strip():
        try:
            semantic_matches = active_index.search(active_embedder.embed(query), min_score=0.35)
        except (SemanticError, ValueError, TypeError):
            semantic_matches = []
        by_path = {str(entry["path"]): entry for entry in memory_results}
        for match in semantic_matches:
            if match.source != "memory" or not match.path.startswith("memory/"):
                continue
            relative = match.path.removeprefix("memory/")
            public_path = f"90-system/.echo/memory/{relative}"
            semantic_norm = max(0.0, min(1.0, float(match.score)))
            existing = by_path.get(public_path)
            if existing is None:
                by_path[public_path] = {
                    "path": public_path,
                    "title": Path(relative).stem,
                    "score": round(semantic_norm * 25.0, 6),
                    "keyword_score": 0,
                    "score_breakdown": {"keyword": 0, "semantic": round(semantic_norm * 25.0, 6)},
                    "semantic_score": round(match.score, 6),
                    "retrieval": "semantic",
                    "provenance": "memory",
                    "conflict_review": "conflict" in public_path.casefold(),
                    "snippet": "",
                    "matched": "",
                }
            else:
                keyword_score = float(existing.get("keyword_score", 0))
                existing["score"] = round(_keyword_evidence(existing) * 70.0 + semantic_norm * 25.0, 6)
                existing["semantic_score"] = round(match.score, 6)
                existing["score_breakdown"]["semantic"] = round(semantic_norm * 25.0, 6)
                existing["retrieval"] = "hybrid"
        memory_results = list(by_path.values())
    combined = results + memory_results
    _mark_conflicts(paths, combined)
    combined.sort(key=lambda entry: (float(entry["score"]), str(entry["path"]).casefold()), reverse=True)
    return combined[:max_results]
