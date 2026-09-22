# CI-001 Expanded Validation Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand protected-branch CI so every automation PR runs semantic evaluation, safety/recall baselines, Hermes static readiness, and wiki lint where applicable.

**Architecture:** Keep one deterministic Windows test job for package installation, pytest, privacy validation, and applicable wiki lint. Add separate bounded evaluation and Hermes-readiness steps that emit redacted machine-readable results and fail on regression, while allowing explicitly optional runtime services to remain unconfigured. CI must validate the same generated-contract and wiki rules developers run locally.

**Tech Stack:** GitHub Actions, Windows runners, Python 3.12, pytest, `second_self` CLI, evaluation runner, Hermes certification script.

**Spec:** `log/2026-09-19-systemic-architecture-audit.md`, CI-001 queue row and acceptance gate.

## Global Constraints

- CI must never read or upload private Layer 1 content, local configuration, tokens, or absolute user paths.
- Synthetic evaluation fixtures remain inline or checked-in public fixtures; private roots are rejected.
- `static_ready` is not runtime Hermes certification; do not claim runtime proof from static checks.
- A missing optional local model or scheduler state is a bounded warning unless the specific gate requires it.
- Preserve the existing PR-opening workflow and do not add duplicate PR creation logic.

## Review Focus

- A regression in one evaluation suite must fail CI while preserving redacted case reasons, tested with a deliberate synthetic failure.
- Missing `hermes-ready/` output must produce the documented static-readiness result rather than a path leak or false runtime claim.
- Wiki lint must run against the public checkout without requiring private vault configuration.
- A dependency or tool failure must identify the failed gate without exposing runner paths or secrets.
- Repeated CI runs must be deterministic and avoid mutable baseline writes, tested by comparing JSON output.

### Task 1: Map current gates and add local gate tests

**Files:**
- Create: `90-system/tests/test_ci_gates.py`
- Modify: `90-system/app/second_self/evaluation/runner.py` only if a stable gate helper is missing
- Test: existing `90-system/tests/test_evaluation_harness.py`, `test_recall_evaluation.py`, `test_safety_evaluation.py`, `test_certify_hermes.py`

- [ ] **Step 1: Add tests** for the exact commands/results CI will consume: all suites pass, failure returns nonzero, Hermes report remains static-only, and wiki lint is valid on the public scaffold.
- [ ] **Step 2: Run the focused tests and record any missing stable command contract.**
- [ ] **Step 3: Add only the smallest redacted command/report adapter required for CI to consume existing evaluation and certification code.**
- [ ] **Step 4: Run focused evaluation, Hermes, and wiki tests.**

### Task 2: Add evaluation and readiness workflow steps

**Files:**
- Modify: `.github/workflows/validate.yml`
- Test: `90-system/tests/test_ci_gates.py`

- [ ] **Step 1: Add a workflow assertion test** that checks required commands appear once, use Python 3.12, and do not reference private paths or live credentials.
- [ ] **Step 2: Run the workflow assertion test before editing and confirm it fails for missing gates.**
- [ ] **Step 3: Add steps for full pytest, privacy validation, semantic/recall/safety evaluation, Hermes static readiness, generated front-matter contract check, and wiki lint with explicit step names.**
- [ ] **Step 4: Run local equivalents in the same order and verify nonzero propagation.**

### Task 3: Verify failure isolation and CI output

**Files:**
- Modify: `.github/workflows/validate.yml`
- Modify: `90-system/docs/HERMES-READINESS.md` if the gate interpretation needs clarification
- Test: `90-system/tests/test_ci_gates.py`

- [ ] **Step 1: Add redacted-output assertions** for evaluation JSON, Hermes JSON, and wiki lint JSON/text.
- [ ] **Step 2: Run them and verify they fail against path-bearing or runtime-overclaiming output.**
- [ ] **Step 3: Ensure each command writes only supported summaries, uses `--json` where available, and does not mutate baselines or private state.**
- [ ] **Step 4: Run the complete local gate set and inspect the workflow diff for duplicate or contradictory conditions.**

### Task 4: Final validation and handoff

**Files:**
- Modify: `90-system/tests/test_ci_gates.py` only if additional regression coverage is needed

- [ ] **Step 1: Run `python -m pytest`, privacy validation, generator check, wiki lint, every evaluation suite, and Hermes static certification.**
- [ ] **Step 2: Confirm reports contain no private paths, source values, credentials, or runtime-certification claims unsupported by live proof.**
- [ ] **Step 3: Review the full workflow diff and leave the plan marked ready for protected delivery.**
