# RET-001 Unified Semantic Recall Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Owner:** Charlie (Development/Coding)

**Coordinator:** ECHO

**Goal:** Fix unified semantic recall so one fresh combined index can return semantic matches from both Layer 1 and durable ECHO memory.

**Architecture:** Keep `hybrid_recall_layer1()` responsible for Layer 1-only callers and its existing Layer 1 freshness contract. Refactor unified `hybrid_recall()` so it performs one freshness check against `layer1_documents(paths) + memory_store_documents(paths.repo_root)`, performs one semantic search, partitions matches by provenance, and merges each partition into its keyword results. Keyword recall remains the safe fallback whenever the combined index is unavailable, stale, corrupt, or the query is blank.

**Tech Stack:** Python 3.12, pytest, the existing `SemanticIndex`, `SemanticMatch`, `SemanticDocument`, and deterministic fake embedders in `90-system/tests/test_semantic.py`.

**Spec:** `log/2026-09-19-systemic-architecture-audit.md`, action item RET-001.

## Global Constraints

- Markdown remains canonical; the semantic SQLite index remains rebuildable derived state.
- Do not persist source text in the semantic index or expose private values in errors, logs, or test output.
- Preserve keyword fallback when semantic dependencies are unavailable or the combined index is not ready.
- Preserve the public result fields and provenance values: `layer1` and `memory`.
- Keep `hybrid_recall_layer1()` behavior compatible for its existing CLI, evaluation, and unit-test callers.
- Use tests-first changes, then run focused tests, privacy validation, and the full suite.
- Update the audit queue from `queued` to `done` only after the acceptance gate passes, including commit/PR and validation evidence.

## Review Focus

- A combined index containing both provenance sets must return semantic-only matches from both sets; this is the primary regression test.
- A combined index that is stale because either a Layer 1 or memory document changed must disable semantic matching for both sets and retain keyword results only.
- A corrupt or unavailable semantic index must not prevent unified keyword recall.
- A blank query must not call the embedder or semantic index and must preserve current keyword behavior.
- Layer 1-only semantic recall and the deterministic semantic evaluation suite must remain unchanged.

---

### Task 1: Add the failing unified-recall regression test

**Files:**
- Modify: `90-system/tests/test_semantic.py` near `test_unified_hybrid_recall_returns_memory_provenance_and_conflict_flag`
- Read: `90-system/app/second_self/reads/recall.py:451-524`
- Read: `90-system/app/second_self/reads/semantic.py:277-348`

**Interfaces:**
- Consumes: `hybrid_recall()`, `layer1_documents()`, `memory_store_documents()`, `SemanticIndex`, and the existing `FakeEmbedder` fixture helper.
- Produces: A regression test that fails against the current double-validation behavior and proves both provenance sets receive semantic results.

- [ ] **Step 1: Extend the unified fixture with a Layer 1 semantic-only note.**

  Add a Layer 1 note whose body does not contain the query terms, keep the existing durable-memory note, and build one index from the combined document list. Give both target documents the same vector as the query while assigning unrelated vectors to the remaining documents.

- [ ] **Step 2: Call unified recall and assert both semantic result types.**

  Call:

  ```python
  results = hybrid_recall(
      second_self,
      "why delay",
      semantic_index=index,
      embedder=embedder,
      max_results=50,
  )
  ```

  Assert that one result with `provenance == "layer1"` and one result with `provenance == "memory"` have `retrieval == "semantic"`, and retain the existing conflict-review assertion for the memory result.

- [ ] **Step 3: Run the regression test and confirm it fails for the reported reason.**

  Run:

  ```powershell
  python -m pytest 90-system/tests/test_semantic.py -k unified -q
  ```

  Expected: the new assertion fails because `hybrid_recall()` passes the combined index into `hybrid_recall_layer1()`, which rechecks freshness using Layer 1 documents only and suppresses the Layer 1 semantic path.

### Task 2: Centralize the combined semantic readiness and search path

**Files:**
- Modify: `90-system/app/second_self/reads/recall.py:328-524`
- Test: `90-system/tests/test_semantic.py`

**Interfaces:**
- Consumes: `SemanticIndex.status(documents, model_id=...)`, `SemanticIndex.search(vector, min_score=...)`, and the existing Layer 1/memory keyword result builders.
- Produces: A unified path that performs one combined freshness check and one semantic search, then merges matches by provenance.

- [ ] **Step 1: Extract a private semantic-search helper with an explicit document set.**

  Add a helper with this contract:

  ```python
  def _ready_semantic_matches(
      semantic_index: SemanticIndex,
      embedder: Embedder,
      documents: Sequence[SemanticDocument],
      query: str,
  ) -> list[SemanticMatch]:
      """Return semantic matches only when the supplied index is fresh and usable."""
  ```

  The helper returns an empty list for a blank query, a non-ready status, or the existing `SemanticError`, `ValueError`, and `TypeError` failure cases. When ready, it embeds the query once and calls `search(..., min_score=0.35)` once.

- [ ] **Step 2: Preserve Layer 1-only behavior through the helper.**

  Update `hybrid_recall_layer1()` to pass `layer1_documents(paths)` to the helper, then merge only matches with `source == "layer1"` and a `layer1/` path using the existing score and metadata rules. Do not pass combined documents into this Layer 1-only function.

- [ ] **Step 3: Make unified recall use one combined helper call.**

  In `hybrid_recall()`, build the existing combined document list once. Replace the outer readiness check and the later second `active_index.search(...)` call with one helper call over the combined list. Partition the returned matches by `source` and merge Layer 1 matches into Layer 1 keyword results and memory matches into memory keyword results. Keep `_mark_conflicts()`, sorting, and `max_results` truncation after both partitions are merged.

- [ ] **Step 4: Keep failure behavior explicit and metadata-only.**

  Ensure semantic-only results still contain their existing path, title, score breakdown, `semantic_score`, `retrieval`, `provenance`, `snippet`, and `matched` fields. Do not read source bodies during semantic matching beyond the existing metadata read used to construct Layer 1 semantic-only results.

- [ ] **Step 5: Run focused tests and confirm the bug is fixed.**

  Run:

  ```powershell
  python -m pytest 90-system/tests/test_semantic.py -q
  python -m pytest 90-system/tests/test_recall.py -q
  ```

  Expected: all focused tests pass, including the new unified Layer 1 + memory regression, stale-index fallback, corrupt-index safety, and existing Layer 1 semantic-only tests.

### Task 3: Verify the acceptance gate and update the queue

**Files:**
- Modify: `log/2026-09-19-systemic-architecture-audit.md` (ignored local audit log)
- Read: `02-skills-projects/skills/second-self-commit/SKILL.md` and relevant policy files before implementation

- [ ] **Step 1: Run the semantic evaluation suite.**

  Run:

  ```powershell
  python -m pytest 90-system/tests/test_evaluation_reporting.py -q
  python -m second_self eval semantic
  ```

  Expected: the existing deterministic semantic cases pass with no regression in top-match accuracy, source coverage, determinism, fallback behavior, or conflict flags.

- [ ] **Step 2: Run repository validation.**

  Run:

  ```powershell
  .\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only
  python -m pytest
  git diff --check
  ```

  Expected: privacy validation passes, the full suite passes, and the diff has no whitespace errors.

- [ ] **Step 3: Review the complete diff.**

  Confirm only the planned recall implementation, semantic regression tests, and the audit status update changed. Confirm no private Layer 1 content, generated cache, or semantic SQLite file is staged.

- [ ] **Step 4: Update the audit item only after validation.**

  Change RET-001 from `queued` to `done` and record the actual commit/PR and test evidence. If validation fails, set it to `ready-for-validation` or `blocked` with the concrete reason instead of claiming completion.

- [ ] **Step 5: Finalize through the existing Second Self commit workflow.**

  Charlie follows `02-skills-projects/skills/second-self-commit/SKILL.md`; no status-only closeout commit is allowed.

## Charlie endorsement

Charlie is endorsed to implement RET-001 after Chad approves this plan. ECHO owns coordination, scope protection, and status reporting; Charlie owns the code, tests, self-review, validation, and final delivery workflow. No implementation has started from this plan.
