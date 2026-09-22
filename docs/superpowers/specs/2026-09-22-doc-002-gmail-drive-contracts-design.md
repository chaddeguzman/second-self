# DOC-002 Gmail and Drive Capability Contracts

## Goal

Define a provider-neutral, future-proof contract for Gmail and Drive so ECHO
can later perform bounded read-only searches without weakening local recall,
privacy, evidence, or approval boundaries.

## Scope

This change defines typed request, item, and result metadata plus the rules
future Gmail and Drive adapters must follow. It does not authenticate, call
Google APIs, inspect credentials, access the network, ingest cloud content, or
enable either capability.

## Contract

1. Requests are explicit, on-demand, bounded, and provider-scoped.
2. Results are transient typed metadata with source attribution.
3. Result payloads do not become Layer 1 evidence automatically.
4. A future save must be an explicit, separate broker-reviewed Raw capture.
5. Adapters are replaceable and must map provider payloads into the shared
   contract rather than exposing provider-specific objects to ECHO.
6. Gmail is limited to read-only message metadata/search in its first adapter.
7. Drive is limited to read-only file metadata/search in its first adapter.
8. No send, draft, upload, move, rename, label, delete, sync, or background
   ingestion operation is represented by this contract.
9. Provider failures return a typed degraded result; local Second Self recall
   remains independent and operational.
10. Credentials are outside the contract and must never appear in results,
    logs, tests, or capability summaries.

## Data flow

```text
ECHO request
  -> capability check
  -> disabled/unavailable: explain and stop
  -> enabled adapter: bounded read-only request
  -> ConnectorResult with typed metadata and source attribution
  -> transient answer
  -> explicit save only: broker-reviewed Raw capture
```

## Non-goals

- OAuth, keyring access, Google SDK dependencies, or network calls.
- Gmail or Drive fixtures containing private or real provider data.
- Automatic synchronization, indexing, or replacement of the local vault.
- External actions such as sending, drafting, uploading, or deleting.

## Acceptance criteria

- The shared contract can represent Gmail message metadata and Drive file
  metadata without provider-specific payload types.
- Every result identifies its provider/source and whether it is transient,
  degraded, or unavailable.
- Invalid limits and unsupported write-oriented operations fail closed.
- The existing capability registry continues to report Gmail and Drive as
  disabled future connectors.
- Tests prove the contract is credential-free and has no network behavior.
