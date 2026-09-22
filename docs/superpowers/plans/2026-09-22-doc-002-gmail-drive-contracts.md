# DOC-002 Gmail and Drive Capability Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add provider-neutral typed contracts for future Gmail and Drive
read-only capability adapters while keeping both capabilities disabled.

**Architecture:** A small local contract module owns request validation,
source-attributed item metadata, and typed result status. Future provider
adapters will translate their payloads into these objects; they will not be
called by this change. The existing capability registry remains the gate that
keeps Gmail and Drive disabled.

**Tech Stack:** Python 3.11+, dataclasses, enums, typing, pytest, existing
Second Self privacy validator.

**Spec:** `docs/superpowers/specs/2026-09-22-doc-002-gmail-drive-contracts-design.md`

## Global Constraints

- Read-only and on-demand first.
- Disabled by default.
- No background synchronization or automatic ingestion.
- No external writes, sends, uploads, moves, renames, labels, or deletes.
- No OAuth, network calls, provider credentials, or private fixtures.
- Explicit saves remain separate broker-reviewed Raw captures.

## Review Focus

- Invalid request limits must fail closed rather than create an unbounded query.
- Provider attribution must survive translation into a transient result.
- Degraded/unavailable results must not look like successful empty results.
- Contract objects must not carry tokens, paths, raw payloads, or credentials.
- Gmail and Drive must remain disabled in the capability registry.

### Task 1: Define the provider-neutral contract

**Files:**
- Create: `90-system/app/second_self/connectors/__init__.py`
- Create: `90-system/app/second_self/connectors/contracts.py`
- Test: `90-system/tests/test_connector_contracts.py`

**Interfaces:**
- `ConnectorKind`: `GMAIL`, `DRIVE`
- `ConnectorState`: `AVAILABLE`, `DEGRADED`, `DISABLED`, `UNAVAILABLE`
- `ConnectorRequest(kind, query, limit=20)` validates a non-empty query and
  limit from 1 through 100.
- `ConnectorItem(provider, item_id, title, source_uri, metadata)` contains
  redacted metadata only.
- `ConnectorResult(kind, state, items=(), message="")` carries typed items,
  source status, and a transient-only contract.

- [ ] Write tests for valid Gmail/Drive requests, invalid limits, typed item
  attribution, degraded results, and credential/path exclusion.
- [ ] Run the focused tests and confirm they fail before implementation.
- [ ] Implement the minimal enums and frozen dataclasses with validation.
- [ ] Run focused tests until they pass.

### Task 2: Document the adapter boundary and capability behavior

**Files:**
- Modify: `90-system/.echo/CAPABILITY-LIST.md`
- Modify: `90-system/.echo/COMMANDS.md`
- Modify: `90-system/app/second_self/capabilities.py` only if the contract
  needs a redacted reason-code clarification.

**Interfaces:**
- Documentation names the shared contract as the future adapter boundary.
- Capability output continues to mark Gmail and Drive as disabled.

- [ ] Add the request → capability check → transient result → explicit Raw
  capture flow to the docs.
- [ ] State that OAuth/keyring and provider SDK work belongs to CONN-001 and
  CONN-002, not DOC-002.
- [ ] Run focused tests, privacy validation, and the full test suite.

### Task 3: Finalize the assignment record

**Files:**
- Modify: `90-system/.echo/subagents/charlie/log.md`

- [ ] Record DOC-002 as `Done` only after the implementation and validation
  pass.
- [ ] Include created, changed, deleted/renamed, and runtime/generated
  artifacts, tests, validation, limitations, confidence, and follow-up IDs.
- [ ] Review the complete diff and finalize through the protected workflow.
