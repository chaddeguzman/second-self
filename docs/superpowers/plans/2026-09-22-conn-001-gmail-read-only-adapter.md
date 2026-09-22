# CONN-001 Gmail Read-Only Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicitly enabled, read-only, on-demand Gmail adapter that returns bounded provider-neutral metadata while keeping OAuth credentials in the operating-system keyring and leaving Gmail disabled by default.

**Architecture:** Keep `ConnectorRequest` and `ConnectorResult` as the provider-neutral boundary. Add a Gmail authentication seam that owns OAuth consent and keyring storage, a Gmail adapter that maps only bounded message metadata into `ConnectorItem`, and a CLI route that refuses to run unless the capability is explicitly enabled. Tests use injected fake services and synthetic payloads; no network or real credentials are used in CI.

**Tech Stack:** Python 3.12, Google API Python Client, `google-auth-oauthlib`, `keyring`, pytest, existing Second Self CLI and capability registry.

**Spec:** `90-system/.echo/subagents/charlie/DOC-002.md`

## Global Constraints

- Gmail remains disabled by default and never becomes available merely because OAuth dependencies are installed.
- Requests are read-only, on-demand, bounded metadata/search requests with a limit from 1 through 100.
- No send, draft, label, delete, upload, background synchronization, or automatic vault write is allowed.
- OAuth tokens belong only in the operating-system keyring and never in Git, logs, CI output, capability summaries, or error messages.
- Provider failures return a redacted degraded or unavailable result and leave local Second Self recall operational.
- Explicit saves, if added later, must use the existing broker-reviewed Raw capture flow; this assignment does not add saving.
- CI and tests must not call Gmail or require a Google account.

## Review Focus

- Missing or malformed OAuth client configuration must fail closed without exposing the configured path.
- Expired or revoked keyring credentials must degrade safely and require explicit reauthorization.
- Gmail messages with missing headers, unusual Unicode, or large bodies must produce bounded metadata only.
- Provider errors, rate limits, and malformed API payloads must not leak raw responses or credential-like values.
- Attempts to use write-like Gmail scopes or unsupported request fields must be rejected before provider execution.

---

### Task 1: Add the credential and OAuth boundary

**Files:**
- Create: `90-system/app/second_self/connectors/gmail_auth.py`
- Modify: `90-system/app/second_self/connectors/__init__.py`
- Test: `90-system/tests/test_gmail_auth.py`

**Interfaces:**
- Consumes: an explicit OAuth client configuration path and a keyring service name; no repository-private paths are embedded in output.
- Produces: `GmailAuthStatus`, `GmailCredentialStore`, and `authorize_gmail()` for the adapter and CLI.

- [ ] **Step 1: Write the failing tests** for keyring round-trip, missing client configuration, read-only scope declaration, and redacted authentication errors.
- [ ] **Step 2: Run the focused tests** with `python -m pytest 90-system/tests/test_gmail_auth.py -q` and confirm they fail because the authentication boundary does not exist.
- [ ] **Step 3: Implement the minimal authentication boundary** using `keyring` for serialized refresh credentials, `InstalledAppFlow` for explicit user consent, the Gmail read-only scope only, and redacted exception messages. Never print or persist access tokens in the repository.
- [ ] **Step 4: Run the focused tests** and confirm all authentication tests pass without network access.

### Task 2: Implement bounded Gmail metadata search

**Files:**
- Create: `90-system/app/second_self/connectors/gmail.py`
- Modify: `90-system/app/second_self/connectors/__init__.py`
- Test: `90-system/tests/test_gmail_connector.py`

**Interfaces:**
- Consumes: `ConnectorRequest`, `ConnectorResult`, an authenticated service factory, and a capability-enabled predicate.
- Produces: `GmailConnector.search(request: ConnectorRequest) -> ConnectorResult`.

- [ ] **Step 1: Write the failing tests** for bounded query/limit forwarding, provider-neutral item mapping, missing-header handling, malformed payload rejection, disabled capability refusal, and redacted provider failure.
- [ ] **Step 2: Run the focused tests** with `python -m pytest 90-system/tests/test_gmail_connector.py -q` and confirm they fail because `GmailConnector` does not exist.
- [ ] **Step 3: Implement the minimal adapter** using only Gmail `users.messages.list` and `users.messages.get` metadata requests, requesting `id`, `threadId`, `labelIds`, `internalDate`, and selected headers. Do not request message bodies, attachments, or write-capable methods.
- [ ] **Step 4: Map results** to `ConnectorItem` with a stable Gmail source URI and bounded metadata; return `UNAVAILABLE` or `DEGRADED` without items when credentials, provider access, or payload shape is invalid.
- [ ] **Step 5: Run the focused tests** and confirm all adapter tests pass with fake services only.

### Task 3: Add explicit CLI enablement and capability reporting

**Files:**
- Modify: `90-system/app/second_self/cli.py`
- Modify: `90-system/app/second_self/capabilities.py`
- Modify: `90-system/.echo/CAPABILITIES.md`
- Modify: `90-system/.echo/CAPABILITY-LIST.md`
- Modify: `90-system/.echo/COMMANDS.md`
- Test: `90-system/tests/test_gmail_cli.py`

**Interfaces:**
- Consumes: `GmailConnector`, `authorize_gmail()`, local configuration loaded through the existing path resolver, and the existing capability registry.
- Produces: explicit `second-self gmail auth` and `second-self gmail search <query> [--limit N]` routes that remain disabled unless configured and explicitly requested.

- [ ] **Step 1: Write the failing tests** for disabled-by-default behavior, safe human and JSON output, limit validation, auth routing, and refusal of write-like command names or scopes.
- [ ] **Step 2: Run the focused tests** with `python -m pytest 90-system/tests/test_gmail_cli.py -q` and confirm they fail because the Gmail routes do not exist.
- [ ] **Step 3: Implement the CLI routes** with explicit capability gating, redacted status messages, no token/path output, and transient result handling. Keep Gmail disabled when configuration is absent.
- [ ] **Step 4: Update capability documentation** to show Gmail as disabled until explicit enablement, explain the read-only boundary, and document the manual OAuth consent step without including secrets or personal paths.
- [ ] **Step 5: Run focused CLI tests** and confirm both text and JSON output remain privacy-safe.

### Task 4: Full validation and assignment closeout

**Files:**
- Modify: `90-system/.echo/subagents/charlie/log.md`
- Test: existing repository validation and full test suite

**Interfaces:**
- Consumes: the completed Gmail auth, adapter, CLI, and documentation surfaces.
- Produces: a completed CONN-001 log entry with exact changed-file, test, validation, and limitation reporting.

- [ ] **Step 1: Run focused connector, CLI, and contract tests.**
- [ ] **Step 2: Run `python -m pytest`.**
- [ ] **Step 3: Run `./90-system/automation/scripts/second-self.ps1 validate --privacy --tracked-only`, Ruff, and mypy gates applicable to changed files.**
- [ ] **Step 4: Inspect the complete diff** for credentials, private paths, body/content capture, write methods, and accidental activation of Gmail.
- [ ] **Step 5: Update Charlie’s log to `Done` only if all gates pass; report manual OAuth setup as a separate optional runtime step, not as a test prerequisite.**
