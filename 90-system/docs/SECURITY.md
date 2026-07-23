# Security Model

## Boundary

The public Git repository contains architecture only. Private data lives outside
the worktree and is linked into the Obsidian vault through ignored directory
junctions.

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

Only trusted Codex and Claude sessions running locally may search the full brain.
Project registration installs local, Git-ignored adapters. Remote automation,
CI, and public repository workflows receive synthetic fixtures only.

Client hooks and the edit broker reduce accidental protected changes. They are
not an operating-system security boundary and can be bypassed by direct
filesystem access.

## Protected Operations

Require two separate approvals for identity or strategy edits, private-context
exports, deletion, move or rename operations, changes to five or more existing
files, and schema migrations.

First approve intent and paths. Then approve the exact diff or payload. Input
hash changes invalidate the approval. Default deletion moves data to dated
private trash.

