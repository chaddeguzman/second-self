# PERF-001 Incremental Document Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build one privacy-safe incremental document manifest that can be reused by dashboard, search, recall, due, recent, and wiki status reads without repeatedly walking and hashing the same files.

**Architecture:** Add a read-only manifest module owned by `second_self.reads` that records bounded file metadata and content fingerprints for approved roots. Consumers receive an immutable snapshot and must preserve their existing output contracts; a changed file is re-read, while unchanged files reuse the prior metadata entry. The cache is in-memory for one process/request lifecycle unless an existing ignored runtime cache boundary is explicitly proven safe.

**Tech Stack:** Python 3.12, `pathlib`, `os.walk`, dataclasses, SHA-256, pytest, existing `SecondSelfPaths` and front-matter parser.

**Spec:** `log/2026-09-19-systemic-architecture-audit.md`, PERF-001 queue row and acceptance gate.

**Implementation status:** Complete. Manifest, reader integrations, benchmark coverage, full tests, privacy validation, and wiki lint passed. Protected Git delivery is pending finalization.

## Global Constraints

- Markdown remains authoritative; the manifest is a derived read model and never writes notes.
- Private roots resolve through `SecondSelfPaths`; no absolute private path, note body, or raw content may enter logs or public output.
- Preserve existing scan limits, skipped directories, bounded note sizes, malformed-note handling, and current dashboard/search/recall result shapes.
- Symlinks and paths outside approved roots are rejected or skipped consistently with existing readers.
- A stale or unavailable manifest must degrade to a safe fresh scan, never return stale private content as current.

## Review Focus

- A file modified without a size change must invalidate by fingerprint, tested with same-size content replacement.
- A file deleted or renamed must disappear from the next snapshot, tested with a two-scan temporary vault.
- A symlink escaping an approved root must never be indexed, tested with a supported Windows-safe skip or guarded test.
- A malformed or oversized note must preserve existing exclusion/error behavior, tested through dashboard and search consumers.
- A repeated read must not leak cached content across different `SecondSelfPaths`, tested with two isolated roots.

### Task 1: Define the manifest contract

**Files:**
- Create: `90-system/app/second_self/reads/manifest.py`
- Test: `90-system/tests/test_manifest.py`

**Interfaces:**
- Produces `ManifestEntry(relative_path: str, size_bytes: int, mtime_ns: int, digest: str, metadata: dict[str, object] | None, body: str | None, readable: bool, error: str = "")`.
- Produces `DocumentManifest(root_kind: str, root: Path, entries: tuple[ManifestEntry, ...], scanned_files: int, errors: int)`.
- Produces `build_manifest(paths: SecondSelfPaths, previous: DocumentManifest | None = None) -> DocumentManifest`.

- [ ] **Step 1: Write failing tests** for stable ordering, same-size content changes, deleted files, skipped directories, bounded files, and root isolation.
- [ ] **Step 2: Run `python -m pytest 90-system/tests/test_manifest.py -q` and verify the new module/API is missing or failing.**
- [ ] **Step 3: Implement bounded enumeration and reuse only when root identity, size, mtime, and digest agree; use `read_note` only for eligible Markdown files.**
- [ ] **Step 4: Run the focused tests and verify all manifest invariants pass.**

### Task 2: Integrate dashboard and list readers

**Files:**
- Modify: `90-system/app/second_self/reads/dashboard.py`
- Modify: `90-system/app/second_self/reads/due.py`
- Modify: `90-system/app/second_self/reads/recent.py`
- Test: `90-system/tests/test_dashboard.py`, `90-system/tests/test_due.py`, `90-system/tests/test_recent.py`

- [ ] **Step 1: Add regression tests** proving dashboard, due, and recent use one supplied manifest and preserve current queue/order/output behavior.
- [ ] **Step 2: Run the focused reader tests and capture the failing call path.**
- [ ] **Step 3: Thread an optional manifest/snapshot parameter through the internal scan boundary without changing public result schemas.**
- [ ] **Step 4: Run focused dashboard/due/recent tests and the existing read tests.**

### Task 3: Integrate search, recall, and wiki status

**Files:**
- Modify: `90-system/app/second_self/reads/search.py`
- Modify: `90-system/app/second_self/reads/recall.py`
- Modify: `90-system/app/second_self/wiki/wiki.py`
- Test: `90-system/tests/test_search.py`, `90-system/tests/test_recall.py`, `90-system/tests/test_wiki.py`

- [ ] **Step 1: Add tests** proving repeated calls reuse unchanged manifest entries, changed files are re-read, and wiki status never resolves outside the wiki root.
- [ ] **Step 2: Run the focused tests and verify the new reuse behavior fails before integration.**
- [ ] **Step 3: Adapt each consumer at its existing enumeration boundary; keep semantic freshness checks based on current file fingerprints.**
- [ ] **Step 4: Run focused tests, full pytest, privacy validation, and wiki lint.**

### Task 4: Review and benchmark the completed read model

**Files:**
- Modify: `90-system/tests/test_manifest.py`
- Create: `90-system/tests/test_manifest_benchmark.py`

- [ ] **Step 1: Add a deterministic benchmark fixture with repeated dashboard/search/recall/wiki reads and assert the second pass performs fewer file-content reads or hashes.**
- [ ] **Step 2: Run `python -m pytest 90-system/tests/test_manifest.py 90-system/tests/test_manifest_benchmark.py -q`.**
- [ ] **Step 3: Run `python -m pytest`, `.\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only`, and `python -m second_self wiki lint`.**
- [ ] **Step 4: Review the complete diff for private paths, stale-cache behavior, and unchanged public output contracts; leave the assignment ready for protected delivery.**
