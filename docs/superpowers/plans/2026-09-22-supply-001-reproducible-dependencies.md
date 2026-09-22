# SUPPLY-001 Reproducible Dependencies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Separate dependency profiles into reproducible core, semantic, Calendar, and development groups, use hash-verified lock groups, and pin GitHub Actions by immutable SHA.

**Architecture:** Keep `pyproject.toml` as the dependency source of truth with named extras/groups that match actual runtime boundaries. Regenerate or hand-maintain a checked-in lock file with hashes and a documented update command, then make local and CI installs select the smallest required profile. Replace floating GitHub Action tags in the validation workflow with reviewed commit SHAs and comments naming the action version.

**Tech Stack:** setuptools project metadata, pip requirements/lock files, GitHub Actions, Python 3.12, pytest.

**Spec:** `log/2026-09-19-systemic-architecture-audit.md`, SUPPLY-001 queue row and acceptance gate.

## Global Constraints

- Core install must remain usable without FastEmbed, Google Calendar extras, or optional local services.
- Lock entries must include hashes and resolve consistently on the supported Windows CI runner.
- Do not put credentials, private indexes, machine paths, or generated private state in dependency files.
- Action pinning must retain readable version comments and use immutable commit SHAs.
- Dependency changes require compatibility tests and must not silently broaden the production install.

## Review Focus

- A core-only install must import the CLI and run non-semantic tests without FastEmbed, tested in an isolated environment.
- Semantic install must expose FastEmbed only when selected, tested without making network/model calls.
- Calendar dependencies must remain isolated from core imports, tested by import and package metadata checks.
- A tampered or missing lock hash must fail installation or the lock verification test, tested with a synthetic lock entry.
- Workflow actions must have 40-character SHAs and readable version comments, tested by a YAML/text policy test.

### Task 1: Map runtime dependency profiles

**Files:**
- Create: `90-system/tests/test_dependency_profiles.py`
- Modify: `pyproject.toml` only after the failing profile tests exist
- Inspect: `90-system/.echo/scripts/connectors`, `90-system/app/second_self`, `requirements.lock`

- [ ] **Step 1: Add failing tests** for core, semantic, Calendar, and dev profile membership, forbidden cross-profile imports, and supported Python version.
- [ ] **Step 2: Run `python -m pytest 90-system/tests/test_dependency_profiles.py -q` and verify the profile contract is not yet represented.**
- [ ] **Step 3: Define named extras/groups with exact existing package floors and no unrequested provider dependencies.**
- [ ] **Step 4: Run the focused metadata/import tests.**

### Task 2: Produce and verify hash-locked dependency groups

**Files:**
- Modify: `requirements.lock`
- Create: `90-system/automation/scripts/verify-dependency-lock.py`
- Test: `90-system/tests/test_dependency_profiles.py`

- [ ] **Step 1: Add tests** requiring every locked distribution entry to carry hashes, every profile to be represented, and no duplicate conflicting versions.
- [ ] **Step 2: Run the tests and verify the existing lock fails the new policy where it lacks profile/hash coverage.**
- [ ] **Step 3: Regenerate the lock using the repository-approved offline/network-safe process, record the source profile, and implement deterministic lock verification.**
- [ ] **Step 4: Run the verifier and isolated metadata tests; do not install from untrusted or private indexes.**

### Task 3: Pin workflow actions

**Files:**
- Modify: `.github/workflows/validate.yml`
- Test: `90-system/tests/test_dependency_profiles.py`

- [ ] **Step 1: Add a policy test** that rejects floating action tags and accepts only immutable SHAs with version comments.
- [ ] **Step 2: Run it before editing and verify current tags are detected.**
- [ ] **Step 3: Replace each action tag with the reviewed immutable SHA and preserve the action/version comment.**
- [ ] **Step 4: Run the policy test and validate YAML structure without executing external actions locally.**

### Task 4: Complete reproducibility verification

**Files:**
- Modify: `90-system/tests/test_dependency_profiles.py`
- Modify: `90-system/docs/OPERATING-MODEL.md` if the install commands need documentation

- [ ] **Step 1: Add tests** for core-only package metadata, semantic opt-in, Calendar isolation, and lock verification failure on changed hashes.
- [ ] **Step 2: Run the focused suite, full pytest, privacy validation, generator check, and wiki lint.**
- [ ] **Step 3: Review the complete dependency/workflow diff for supply-chain surprises, private URLs, and unintended transitive expansion.**
- [ ] **Step 4: Leave the assignment ready for protected delivery with the exact profile install commands recorded in the plan’s implementation notes.**
