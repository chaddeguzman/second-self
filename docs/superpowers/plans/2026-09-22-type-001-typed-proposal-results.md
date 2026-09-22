# TYPE-001 Typed Proposal and Result Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace unbounded `dict[str, Any]` broker and wiki proposal/result payloads with validated typed models so malformed shapes fail before protected mutation.

**Architecture:** Introduce small frozen dataclasses or equivalent validated models at the broker/wiki boundary, with explicit serialization methods for existing CLI/web payloads. Keep the broker as the only mutation authority; models validate paths, operations, content metadata, and result status before the broker or wiki executor sees them. Preserve backward-compatible external JSON keys where callers already depend on them.

**Tech Stack:** Python 3.12, dataclasses, `typing`, existing broker/wiki validation, pytest, CI static-check tooling.

**Spec:** `log/2026-09-19-systemic-architecture-audit.md`, TYPE-001 queue row and acceptance gate.

**Implementation status:** Complete. Typed broker/wiki models, fail-closed boundary validation, Ruff, mypy, full tests, privacy validation, and wiki lint passed. Protected Git delivery is pending finalization.

## Global Constraints

- Protected operations remain proposal → approval → broker; typing must not bypass approval or broker checks.
- Models contain relative/public identifiers only; absolute private paths, secrets, raw private content, and exception text are prohibited in serialized results.
- Invalid input fails closed before file mutation, transaction journaling, or provider calls.
- Existing CLI/web consumers must either use typed models directly or consume an explicitly tested `as_dict()` projection.
- Add Ruff plus mypy or pyright gates only at a scope the repository can install and run deterministically.

## Review Focus

- Unknown operation names must be rejected, tested before any broker dispatch.
- Absolute, traversal, and private-root paths must be rejected or normalized only by the existing path boundary, tested with malicious payloads.
- Missing, extra, or wrong-typed proposal fields must fail with stable redacted errors, tested through the public proposal entry point.
- A typed result must not expose private content or exception text, tested through JSON serialization.
- Legacy valid payloads must retain their public keys and behavior, tested with existing broker/wiki fixtures.

### Task 1: Inventory and specify boundary models

**Files:**
- Create: `90-system/app/second_self/broker/models.py`
- Create: `90-system/app/second_self/wiki/models.py`
- Test: `90-system/tests/test_typed_models.py`

**Interfaces:**
- Produce `BrokerProposal.from_payload(payload: Mapping[str, object]) -> BrokerProposal` and `BrokerProposal.as_dict() -> dict[str, object]`.
- Produce `BrokerResult.as_dict() -> dict[str, object]` with redacted stable fields.
- Produce `WikiProposal.from_payload(payload: Mapping[str, object]) -> WikiProposal` and `WikiResult.as_dict() -> dict[str, object]`.

- [ ] **Step 1: Add failing construction/serialization tests** for every current broker and wiki operation, required fields, unknown fields, path safety, and redaction.
- [ ] **Step 2: Run `python -m pytest 90-system/tests/test_typed_models.py -q` and verify the model imports/API fail.**
- [ ] **Step 3: Implement the smallest validated immutable models using existing allowlists and path helpers rather than duplicating policy.**
- [ ] **Step 4: Run the focused model tests and verify deterministic serialization.**

### Task 2: Route broker payloads through typed models

**Files:**
- Modify: `90-system/app/second_self/broker/broker.py`
- Modify: `90-system/app/second_self/cli.py` if broker commands require adaptation
- Test: `90-system/tests/test_broker.py`

- [ ] **Step 1: Add regression tests** proving malformed edit/move/delete/export/link-fix proposals fail before journal creation or mutation.
- [ ] **Step 2: Run the broker tests and record the pre-integration failure.**
- [ ] **Step 3: Parse incoming payloads once into `BrokerProposal`, use typed fields internally, and project typed results at existing public boundaries.**
- [ ] **Step 4: Run broker, CLI, privacy, and transaction-recovery tests.**

### Task 3: Route wiki payloads through typed models

**Files:**
- Modify: `90-system/app/second_self/wiki/wiki.py`
- Modify: `90-system/app/second_self/wiki/web_process.py`
- Test: `90-system/tests/test_wiki.py`, `90-system/tests/test_web_process_raw.py`

- [ ] **Step 1: Add tests** for malformed wiki process payloads, unsupported destinations, unsafe links, and valid payload compatibility.
- [ ] **Step 2: Run the focused wiki tests and verify the new typed boundary is not yet enforced.**
- [ ] **Step 3: Parse wiki proposals into `WikiProposal` before validation/execution and return `WikiResult` projections without changing transaction semantics.**
- [ ] **Step 4: Run focused wiki tests and `python -m second_self wiki lint`.**

### Task 4: Add static gates and complete verification

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.lock`
- Modify: `.github/workflows/validate.yml`
- Test: `90-system/tests/test_typed_models.py`

- [ ] **Step 1: Add a small typed boundary fixture that Ruff and the selected checker can analyze without private imports.**
- [ ] **Step 2: Run the new checker command before configuration and confirm the gate is absent or fails as expected.**
- [ ] **Step 3: Pin compatible checker versions, configure only the repository package/tests scope, and add CI commands with stable failure output.**
- [ ] **Step 4: Run the checker, full pytest, privacy validation, wiki lint, and complete diff review.**
