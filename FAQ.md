# Frequently Asked Questions

## Where is my private data stored?

By default, bootstrap creates `%USERPROFILE%\SecondSelfData` and links its
private folders into the repository. The ignored `.second-self.local.json`
records the active location.

## Is my personal content uploaded to GitHub?

No. Layer 1, project records, the LLM Wiki, local configuration, caches,
backups, and recovery history are ignored. Always run the privacy validation
and review `git status` before publishing changes.

## Can I use Second Self without Obsidian or an AI agent?

Yes. The files are Markdown and can be edited with another text editor. The
local dashboard also works without an AI agent. Obsidian and trusted agents
provide the intended full experience.

## Can I use macOS or Linux?

Not with the current bootstrap and launcher. The supported setup targets
Windows PowerShell and Windows directory junctions.

## What should I never store in Second Self?

Never store passwords, API keys, access tokens, recovery codes, or private
cryptographic keys. Use a credential manager instead.

## How do I back up my Second Self?

Second Self supports two backup modes:

- **Encrypted backup** — creates an `age`-encrypted `.tar.age` archive for
  disaster recovery. Requires `age`. Use `backup.ps1 -Destination "<path>"`.
- **Obsidian-readable sync backup** — creates a plain `second-self\` folder you
  can open directly in Obsidian, copy to another machine, or push to GitHub.
  Use `backup.ps1 -SyncTo "<parent-folder>"`.

For the plain sync, the new folder keeps the last 5 backups and excludes caches
(`node_modules`, `__pycache__`, `.second-self-cache`, etc.) while including
`.git` for full GitHub history.

## How do I restore or move to a new machine?

For **encrypted backups**, run `restore.ps1` with the archive and an empty
destination.

For **plain sync backups**, copy the `second-self\` backup folder to the new
machine, then update `.second-self.local.json` so `data_root` points to that
location. No decryption is needed.

## What is the difference between encrypted and sync backups?

Encrypted backups are `.tar.age` archives meant for offline storage and disaster
recovery. Sync backups are plain unencrypted folders meant for portability,
Obsidian access, and Git operations. Choose encrypted for security; choose sync
when you need to open the backup directly or move it between machines quickly.

## Why do I sometimes see "missing required parameter" errors in Cline?

That error comes from Cline rejecting a tool call (for example `write_to_file`,
`replace_in_file`, or `execute_command`) where a required field was absent,
empty, or cut off mid-transmission. It is an adapter-side truncation or parsing
issue, not a Second Self defect, and Second Self does not register any Cline
hooks or MCP servers. Retry the same call and verify the file on disk. You can
reduce how often this happens by splitting very large writes into smaller
calls and reading big audit, JSONL, or log files selectively instead of
wholesale — see the Agent Tool Hygiene section of `AGENTS.md`.
