# OPS-001 Hardened Backup and Restore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden encrypted backup and restore with atomic replacement, archive traversal checks, authenticated manifests, and a disposable restore drill.

**Architecture:** Keep backup and restore as explicit PowerShell operations over the resolved configured data root. Backup creates a temporary archive outside the destination, writes an authenticated manifest and checksum only after successful archive creation, then atomically publishes the final set. Restore verifies checksum, decrypts to a temporary directory, validates archive members and manifest/schema before extraction, and atomically moves the validated data tree into an empty destination. Tests use disposable synthetic data and mocked `age`/`tar` boundaries; no real private vault or destructive live restore is allowed.

**Tech Stack:** PowerShell 7-compatible scripts, `tar`, `age`, SHA-256, JSON manifests, Pester or repository-supported subprocess tests, pytest for policy/fixture coverage.

**Spec:** `log/2026-09-19-systemic-architecture-audit.md`, OPS-001 queue row and acceptance gate.

## Global Constraints

- Resolve `.second-self.local.json` and data roots safely; never hard-code or log private paths.
- Restore must refuse non-empty destinations, path traversal, absolute archive members, symlinks/reparse points, invalid schema versions, checksum mismatches, and incomplete temporary output.
- Encryption remains passphrase-based through `age`; plaintext temporary archives are deleted in `finally` blocks.
- Manifests authenticate the archive identity, schema version, file inventory/digests, and creation metadata without including private note contents.
- The restore drill must use a disposable synthetic vault and prove source data is unchanged after success and failure.

## Review Focus

- An archive member such as `../../outside.txt` must be rejected before extraction, tested with a crafted tar listing.
- A symlink/reparse member must not escape the destination, tested where the platform tool exposes that metadata.
- A valid archive with a changed manifest or checksum must fail closed, tested by tampering each artifact independently.
- A failed restore after partial extraction must leave the existing destination unchanged, tested with injected extraction failure.
- Backup failure must not leave plaintext tar files or a misleading final manifest, tested by inspecting the disposable destination/temp directory.

### Task 1: Define authenticated manifest and archive policy

**Files:**
- Create: `90-system/automation/scripts/backup-manifest.ps1` or a focused shared PowerShell module beside the scripts
- Create: `90-system/tests/test_backup_restore_policy.py`
- Modify: `90-system/automation/scripts/backup.ps1` only after policy tests exist

- [ ] **Step 1: Add failing policy tests** for manifest fields, canonical serialization, file inventory digesting, allowed archive roots, and rejection reasons.
- [ ] **Step 2: Run the focused tests and verify the shared policy boundary is absent.**
- [ ] **Step 3: Implement deterministic manifest generation and archive-member validation with no raw note content in the manifest.**
- [ ] **Step 4: Run the focused policy tests and inspect redacted errors.**

### Task 2: Make backup publication atomic

**Files:**
- Modify: `90-system/automation/scripts/backup.ps1`
- Modify: `90-system/automation/scripts/backup-manifest.ps1` or the selected shared module
- Test: `90-system/tests/test_backup_restore_policy.py`

- [ ] **Step 1: Add failure-injection tests** for tar failure, encryption failure, hash failure, manifest write failure, and destination collision.
- [ ] **Step 2: Run them and verify current backup behavior can leave incomplete artifacts or lacks the expected authenticated inventory.**
- [ ] **Step 3: Write archive, checksum, and manifest to uniquely named temporary files; atomically rename the complete set only after all checks pass; always delete plaintext tar output.**
- [ ] **Step 4: Run the focused backup tests and confirm no partial final artifact remains after injected failure.**

### Task 3: Harden restore with validate-then-replace

**Files:**
- Modify: `90-system/automation/scripts/restore.ps1`
- Test: `90-system/tests/test_backup_restore_policy.py`

- [ ] **Step 1: Add tests** for checksum mismatch, manifest mismatch, invalid schema, traversal, absolute member, symlink/reparse member, non-empty destination, extraction failure, and successful replacement.
- [ ] **Step 2: Run the restore tests and verify the current script does not yet enforce all boundaries.**
- [ ] **Step 3: Decrypt and extract only into a disposable staging directory, validate the listing and manifest inventory, then atomically move the validated root to the empty destination; clean staging material in `finally`.**
- [ ] **Step 4: Run the focused restore tests and prove the existing destination remains unchanged after each failure.**

### Task 4: Execute the disposable restore drill and document operations

**Files:**
- Create: `90-system/tests/fixtures/backup-restore-synthetic/README.md`
- Modify: `90-system/docs/OPERATING-MODEL.md`
- Modify: `90-system/docs/SECURITY.md` if backup/restore guarantees need recording

- [ ] **Step 1: Add a deterministic drill fixture** containing public synthetic Markdown, schema metadata, an empty ignored-cache placeholder, and a file with a same-size replacement case.
- [ ] **Step 2: Run the drill through mocked tool boundaries and assert restored inventory/digests match the source without logging file contents or absolute paths.**
- [ ] **Step 3: Document backup creation, checksum/manifest verification, restore refusal conditions, and disposable-drill commands.**
- [ ] **Step 4: Run full pytest, privacy validation, generator check, wiki lint, and complete diff review; confirm no real private backup was created.**
