# SEC-003 Broker Transaction Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Owner:** Charlie (Development/Coding)

**Coordinator:** ECHO

**Complexity:** High. This changes a protected-write security boundary and must be treated as a transactional-systems change, not a routine refactor.

**Goal:** Generalize broker staging and rollback so every multi-file protected operation leaves no partial mutation after an injected failure, and recover stale wiki processing locks without deleting a lock held by an active transaction.

**Architecture:** Introduce one broker transaction journal and staging area under the private audit/runtime root. Each operation records its intended file effects, creates backups or staged replacements before mutation, records per-effect application progress atomically, and rolls back in reverse order on failure. `wiki_process` keeps its existing source-specific validation and move semantics but uses the shared recovery contract. Wiki lock acquisition will write ownership metadata, detect active journals first, and remove only locks that exceed a bounded stale threshold with no active transaction evidence.

**Tech Stack:** Python 3.12, dataclasses, `pathlib`, JSON journals, atomic `os.replace`, `shutil`, pytest failure injection, and the existing `SecondSelfPaths`/broker APIs.

**Spec:** `log/2026-09-19-systemic-architecture-audit.md`, action item SEC-003; architectural constraints in `90-system/docs/SECURITY.md` and `90-system/docs/OPERATING-MODEL.md`.

## Global Constraints

- Protected operations remain approval-gated and proposal-digest-bound; SEC-003 must not weaken SEC-001 or SEC-002 behavior.
- Markdown and user files remain authoritative; transaction journals, backups, and staging files are private rebuildable runtime state.
- Never expose absolute private paths, file contents, credentials, or raw exception payloads in proposal results, audit events, or error messages.
- A failed multi-file operation must restore the exact pre-operation state, including missing-versus-existing files and move destinations.
- Recovery must fail closed when journal data is malformed, a target has unrelated concurrent edits, or an active transaction is present.
- Recovery must be idempotent: rerunning recovery after a completed rollback must not mutate user files again.
- Preserve the existing `approve(...) -> dict[str, Any]` result shape and operation names unless a compatibility-preserving field is required for recovery state.
- No live private-vault data may be used in tests; use temporary `SecondSelfPaths` fixtures and synthetic contents only.
- Use tests-first failure injection, then focused tests, privacy validation, full pytest, and the protected Git workflow.

## Review Focus

- Two-file edit/migration/link-fix failure after the first replacement must restore the first file and leave the second file unchanged.
- Move/delete failure after one item has moved must restore both source and destination paths, including empty parent cleanup.
- Export failure must not leave a partial destination file and must not delete a pre-existing destination.
- A malformed or tampered transaction journal must refuse recovery rather than guessing which content is safe to restore.
- A stale `.processing.lock` may be removed only when it is older than the configured threshold and no `staging`/`applying` journal proves an active transaction; a fresh lock or active journal must remain protected.

---

### Task 1: Map operation effects and add failing failure-injection tests

**Files:**
- Modify: `90-system/tests/test_broker.py`
- Modify: `90-system/tests/test_wiki.py`
- Read: `90-system/app/second_self/broker/broker.py:131-157, 333-541, 544-604`

**Interfaces:**
- Consumes: existing `propose()`, `approve()`, `recover_wiki_transactions()`, and temporary `SecondSelfPaths` fixtures.
- Produces: regression tests that fail against sequential broker writes and define the exact pre-operation state that recovery must restore.

- [x] **Step 1: Add an edit failure test with two changed files.**

  Build an `edit` proposal containing two existing notes. Inject an `os.replace` or write failure on the second mutation. Assert approval raises, both original byte contents remain unchanged, no transaction remains in `staging`/`applying`, and no partial proposal result is reported as applied.

- [x] **Step 2: Add migration and link-fix rollback coverage.**

  Create multi-file `migration` and `link_fix` proposals, fail after the first target is applied, and assert every original target is restored byte-for-byte. Use separate tests or parametrization only when the setup and expected rollback are identical.

- [x] **Step 3: Add move/delete rollback coverage.**

  For a multi-item `move`, fail after the first `shutil.move` and assert every source returns and no destination remains. For a multi-item `delete`, fail after the first trash move and assert all originals return and no partial trash state is treated as a successful deletion.

- [x] **Step 4: Add export safety coverage.**

  Inject a write/replace failure during an export and assert a partial destination is removed when it did not exist before. Add a pre-existing destination case and assert the broker refuses it without overwriting or deleting the original.

- [x] **Step 5: Add stale-lock and active-lock tests.**

  Create a fresh `.processing.lock` and assert wiki approval refuses with the existing active-transaction error. Create an old lock with no active journal and assert the next approval removes it and proceeds. Create an old lock with an `applying` journal and assert recovery refuses to remove the lock until the journal is recovered.

- [x] **Step 6: Run the new tests and confirm the expected red failures.**

  Run:

  ```powershell
  python -m pytest 90-system/tests/test_broker.py 90-system/tests/test_wiki.py -k "rollback or recovery or lock or export" -q
  ```

  Expected: the injected multi-file failures expose partial mutations or missing rollback, and stale-lock tests expose the current unconditional lock refusal/no-recovery behavior.

### Task 2: Implement the generic transaction journal and rollback engine

**Files:**
- Modify: `90-system/app/second_self/broker/broker.py:333-604`
- Test: `90-system/tests/test_broker.py`

**Interfaces:**
- Consumes: operation specifications and resolved paths from `_affected()`/`_apply()`.
- Produces: private helpers with an explicit transaction lifecycle, for example:

  ```python
  def _begin_transaction(paths: SecondSelfPaths, proposal_id: str) -> BrokerTransaction: ...
  def _apply_transaction(paths: SecondSelfPaths, transaction: BrokerTransaction) -> list[str]: ...
  def _rollback_transaction(paths: SecondSelfPaths, transaction: BrokerTransaction) -> None: ...
  def _recover_transactions(paths: SecondSelfPaths) -> list[str]: ...
  ```

  Exact internal names may follow the existing broker naming style, but the journal must record transaction id, status, operation, per-path original state, staged/backup path, and applied state.

- [x] **Step 1: Define the private journal schema and atomic journal writer.**

  Store journals under a private transaction root resolved from `SecondSelfPaths`. Use `status` values `staging`, `applying`, `committed`, and `rolled-back`. Write every progress update through a temporary file followed by `os.replace`; reject malformed or unknown schema/status during recovery.

- [x] **Step 2: Build a path-effect plan before mutating user files.**

  Resolve and validate every source, destination, backup, and staged replacement before the first mutation. Record whether each target existed and its hash. Refuse duplicate/conflicting paths and pre-existing move/export destinations before mutation begins.

- [x] **Step 3: Implement backup/stage helpers for replacement operations.**

  For `edit`, `migration`, and `link_fix`, stage new content privately, back up existing targets, then atomically replace targets while updating the journal after each effect. On failure, restore existing targets from backups and delete newly created targets only when their current hash still matches the journaled applied content.

- [x] **Step 4: Implement recoverable move/delete effects.**

  Stage originals inside the transaction directory before moving them to final destinations or trash. Record both source and destination paths. Roll back in reverse order and refuse to overwrite unrelated concurrent content.

- [x] **Step 5: Implement export and assemble-layer1 rollback adapters.**

  Treat a newly created export destination as removable only when its hash matches the journaled content; never overwrite a pre-existing destination. Preserve `_assemble_layer1()`’s Windows junction safeguards behind an operation-specific adapter that restores the scaffold/pending junction state on failure.

- [x] **Step 6: Route all non-wiki operations through the transaction engine.**

  Replace direct sequential branches in `_apply()` with effect plans handled by the shared engine. Keep `wiki_process` on its existing validated path temporarily, but make its journal schema and rollback calls compatible with the shared recovery contract.

- [x] **Step 7: Run focused tests and confirm green rollback behavior.**

  Run:

  ```powershell
  python -m pytest 90-system/tests/test_broker.py 90-system/tests/test_wiki.py -q
  ```

  Expected: all injected failures restore the pre-operation state, successful operations preserve existing result/audit behavior, and no transaction is left in an applying state after a handled failure.

### Task 3: Harden wiki lock acquisition and recovery integration

**Files:**
- Modify: `90-system/app/second_self/broker/broker.py:387-541, 639-681`
- Modify: `90-system/app/second_self/wiki/wiki.py:175-240` only if the shared recovery status requires it
- Modify: `90-system/tests/test_broker.py`
- Modify: `90-system/tests/test_wiki.py`

**Interfaces:**
- Consumes: the transaction journal schema from Task 2 and existing `recover_wiki_transactions()` callers.
- Produces: bounded, idempotent lock recovery that distinguishes fresh locks, stale orphan locks, and locks backed by active journals.

- [x] **Step 1: Define stale-lock policy and ownership metadata.**

  Add a named stale threshold and write a small JSON ownership payload containing transaction/proposal id and creation time. On contention, inspect active `staging`/`applying` journals before considering age; do not infer liveness from age alone.

- [x] **Step 2: Protect active interrupted journals before acquiring a new wiki lock.**

  Run shared recovery for eligible interrupted transactions. If rollback detects unrelated target content, leave the journal and lock intact and raise a path-safe recovery error. If rollback succeeds, mark the journal `rolled-back`, then remove its orphaned lock.

- [x] **Step 3: Make lock cleanup exception-safe and idempotent.**

  Ensure lock handles close in every branch, transaction locks are not removed by another proposal, and a second recovery call returns no duplicate work. Preserve the existing proposal lock cleanup behavior.

- [x] **Step 4: Run wiki recovery and contention tests.**

  Run:

  ```powershell
  python -m pytest 90-system/tests/test_wiki.py 90-system/tests/test_broker.py -q
  ```

  Expected: active locks still block, stale orphan locks recover, active journals are never bypassed, and interrupted wiki transactions restore sources/pages without a second mutation.

### Task 4: Acceptance validation, security review, and delivery

**Files:**
- Modify: `log/2026-09-19-systemic-architecture-audit.md` (ignored local audit log)
- Modify: `90-system/.echo/subagents/charlie/log.md`

- [x] **Step 1: Run all required validation.**

  Run:

  ```powershell
  .\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only
  python -m pytest
  git diff --check
  ```

  Expected: privacy validation and the full suite pass; no whitespace errors are present.

- [x] **Step 2: Review security invariants in the complete diff.**

  Confirm proposal digest/approval checks are unchanged, all protected operations are transaction-wrapped, rollback refuses unrelated concurrent content, journals are private and redacted, stale-lock removal requires orphan evidence, and no private content or runtime cache is staged.

- [x] **Step 3: Update status to `ready-for-validation` pending protected delivery.**

  Mark Charlie `Done` with the test and confidence summary. Change SEC-003 from `queued` to `done` only after the protected commit, PR, CI, merge, and final `main` verification succeed. If implementation is validated but delivery awaits approval, use `ready-for-validation` and record the reason.

- [ ] **Step 4: Finalize through `02-skills-projects/skills/second-self-commit/SKILL.md` after Chad's approval.**

  Produce one coherent commit, one PR, and one merge. Do not create a checkpoint or status-only closeout commit.

## ECHO recommendation

SEC-003 was assigned to Charlie after plan approval. ECHO remains coordinator and security-boundary reviewer; Sherlock was not required because the existing broker consumers were sufficient. Implementation is validated locally; protected delivery remains approval-gated.
