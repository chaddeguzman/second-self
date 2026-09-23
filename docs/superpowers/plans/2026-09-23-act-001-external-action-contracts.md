# ACT-001 Approval-Gated External Action Contracts

**Assignment:** ACT-001
**Owner:** Charlie
**Endorsement:** ECHO
**Status:** Implemented and locally validated; protected delivery pending approval

## Goal

Define a provider-neutral contract for future external actions while keeping
all external execution disabled. The contract must make the approval boundary
visible and auditable before any future adapter can draft, send, or upload.

## Design

```text
intent -> typed action request -> exact payload digest
       -> explicit human approval -> bounded audit record
       -> future adapter boundary (not implemented here)
```

- Support only the planned action kinds: `draft_email`, `send_email`, and
  `upload_file`.
- Represent payloads by a SHA-256 digest and bounded redacted preview; never
  persist raw bodies, file content, credentials, or provider objects.
- Require an allowlisted scope for each action and reject scope escalation.
- Bind approval to request ID, action kind, scope, and exact payload digest.
- Require an expiry timestamp and status transition; expired or mismatched
  approvals are unusable.
- Record audit metadata only: actor, action, scope, result status, request ID,
  payload digest, and timestamps.
- Keep the capability `planned` and provide no execute/send/upload method.

## Acceptance criteria

- Typed request, approval, and audit models validate bounded, credential-free
  data and serialize stably.
- Invalid action kinds, scopes, digests, previews, and expired approvals fail
  closed.
- Approval cannot be reused for a different payload, action, scope, or request.
- Tests demonstrate that the contract has no provider/network execution path.
- Capability and security documentation explain that ACT-001 defines a guard
  rail only; it does not authorize or perform external actions.
- Privacy validation, full pytest, Ruff, mypy, and diff review pass.

## Out of scope

- Gmail, Drive, Calendar, or any other provider adapter.
- Sending, drafting, uploading, sharing, deleting, or modifying external data.
- OAuth, credentials, network calls, background jobs, or automatic retries.
- Wiring the contract into the broker's file mutation operations.

## Validation result

- Focused ACT-001 and capability tests: passed.
- Full test suite: 673 passed.
- Privacy validation: passed.
- Ruff: passed.
- Mypy: passed.
- No provider, network, credential, broker execution, draft, send, or upload
  action was invoked.
