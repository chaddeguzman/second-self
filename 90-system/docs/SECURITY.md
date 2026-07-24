# Security Model

## Boundary

The public Git repository contains architecture only. Private data lives outside
the worktree and is linked into the Obsidian vault through ignored directory
junctions.

This boundary includes `03-wiki`, Raw sources, Processed archives, wiki
transaction journals, and generated source pages. Only empty scaffolds and
reusable instructions may be tracked.

This boundary includes `03-wiki`, Raw sources, Processed archives, wiki
transaction journals, and generated source pages. Only empty scaffolds and
reusable instructions may be tracked.

The active private directory is plaintext so Obsidian and local search can read
it. Protect the Windows account and system drive with BitLocker or Windows
device encryption.

## Prohibited Content

Never store:

- passwords
- API keys or access tokens
- recovery codes
- private cryptographic keys

Use an appropriate credential manager instead.

## Agent Trust

Only trusted Codex and Claude sessions running locally may search the full
Second Self context.
Project registration installs local, Git-ignored adapters. Remote automation,
CI, and public repository workflows receive synthetic fixtures only.

Client hooks and the edit broker reduce accidental protected changes. They are
not an operating-system security boundary and can be bypassed by direct
filesystem access.

## Protected Operations

Require one approval for identity or strategy edits, private-context exports,
deletion, move or rename operations, changes to five or more existing files,
and schema migrations.

Show the intent, affected paths, and exact diff or payload in one proposal.
Accept `Y` or `Yes` to apply and `N` or `No` to reject, case-insensitively.
Never require an approval phrase, proposal ID, timestamp, or second approval.
Input hash changes invalidate the approval. Default deletion moves data to
dated private trash.

Raw-to-Processed moves use the same single approval as other protected changes.
Transaction journals store private-relative paths and hashes, not source
contents or reusable absolute user paths. A failed or interrupted transaction
must roll back or be recovered before new processing begins.
