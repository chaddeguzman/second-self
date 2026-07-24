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

Install `age`, connect a removable backup drive, and run the backup command
shown under [Everyday Commands](<Quick Start.md#everyday-commands>). Keep the
backup and its encryption passphrase in appropriately protected, separate
locations.
