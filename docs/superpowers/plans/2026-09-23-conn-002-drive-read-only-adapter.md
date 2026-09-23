# CONN-002 Drive Read-Only Adapter Implementation Plan

**Assignment:** CONN-002
**Owner:** Charlie
**Endorsement:** ECHO
**Status:** Implemented and locally validated; protected delivery pending approval

## Goal

Add an explicitly enabled, read-only, on-demand Google Drive adapter that
maps bounded file metadata into the DOC-002 provider-neutral connector
contract. Drive must remain disabled by default and must never upload, move,
rename, delete, download content, synchronize, or write to the vault.

## Design

```text
drive auth/search CLI
  -> explicit enablement and bounded request
  -> Drive read-only OAuth credential store in the OS keyring
  -> Drive v3 files.list with metadata fields only
  -> ConnectorResult<Drive metadata>
  -> transient redacted output; no broker or vault write
```

- Use the Drive metadata-only OAuth scope in a Drive-specific keyring entry.
- Request only `files.list` metadata fields: id, name, mimeType, modifiedTime,
  webViewLink, size, and parents.
- Cap query and metadata values, reject malformed provider payloads, and
  redact provider exceptions.
- Keep `SECOND_SELF_DRIVE_ENABLED` opt-in and add `drive auth` plus
  `drive search` CLI routes mirroring the Gmail safety boundary.
- Preserve the capability registry state as `disabled`; implementation does
  not authorize or activate Drive by itself.

## Acceptance criteria

- Unit tests prove disabled mode never constructs or calls the provider.
- Fake-service tests prove bounded fields, limits, source attribution, and no
  file content/download methods.
- Auth tests prove the Drive scope is exact, credentials stay in the injected
  keyring, and errors are redacted.
- CLI tests prove disabled-by-default behavior, explicit enablement, and no
  client-config path or credential leakage.
- Privacy validation, focused tests, full pytest, targeted Ruff, and mypy
  pass. No account, token, network call, or private vault data is required.

## Out of scope

- Live Google authentication or Drive API calls.
- File content retrieval, export, upload, move, rename, delete, sharing,
  background sync, indexing, or automatic Raw capture.

## Validation result

- Focused Drive tests: 12 passed.
- Full test suite: 664 passed.
- Privacy validation: passed.
- Targeted Ruff and import-order checks: passed.
- Mypy: passed.
- No Google account, OAuth consent, token, network call, or private vault
  data was used.
