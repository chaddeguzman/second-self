# Second Self

Second Self is a private-data, public-architecture system that helps represent
you as a whole person for both personal use and trusted AI agents. It brings
together your identity, values, principles, knowledge, memories, experiences,
events, strategy, projects, reviews, and learned ways of working across
Obsidian, Codex, and Claude.

The repository is designed to be reusable. Its public code, documentation, and
workflows can be cloned or forked, while your personal context remains local
and excluded from Git.

## Folder Guide

| Folder | Purpose | Maintained by |
| --- | --- | --- |
| `01-strategy-storage` | Private notes, journals, strategy, references, and reviews | You and your agents |
| `02-skills-projects` | Reusable skills and project context | You and your agents |
| `90-system` | Application code, automation, technical documentation, migrations, and tests | Agents and developers |

Your normal work belongs in Layers 1 and 2. You should not need to edit
`90-system`, hidden folders, or root configuration files during regular use.

### Layer 1

`01-strategy-storage` is local and excluded from GitHub. Its user-maintained
folders are:

- `00 Memory`
- `01 Notes`
- `02 Journal`
- `03 Strategy`
- `04 References`
- `05 Reviews`

You can copy existing documents directly into these folders. These six folders
are the approved top-level structure for Layer 1. Agents must receive your
approval before creating another top-level folder. Runtime indexes, audit
records, imports, and recoverable trash belong in Git-ignored system storage,
not alongside your core folders.

### Layer 2

`02-skills-projects` contains reusable agent skills and private project records.
Skills are versioned in Git. The `projects` folder is private and excluded from
GitHub.

### System

`90-system` keeps technical internals out of the user workspace:

- `app`: Second Self Python application
- `automation`: scripts, hooks, and Git hooks
- `docs`: operating model, security guidance, schemas, and templates
- `migrations`: controlled structure changes
- `tests`: automated verification

## Quick Start

Requirements: Windows, Git, Python 3.12+, Obsidian, and `age`.

```powershell
.\90-system\automation\scripts\bootstrap.ps1
.\90-system\automation\scripts\second-self.ps1 validate
```

After cloning or forking the repository, bootstrap creates
`%USERPROFILE%\SecondSelfData`, writes an ignored local configuration file, and
assembles the vault with directory junctions. Your personal data remains local
and is never intentionally committed.

### Private local Home

Launch the local dashboard after bootstrap:

```powershell
.\90-system\automation\scripts\second-self.ps1 web
```

Second Self opens a private Home page on `http://127.0.0.1:8765/`. If that
port is occupied, it tries through port `8774`. The dashboard shows structured
inbox work, recent imports, memories awaiting confirmation, conflicts, overdue
commitments, pending project writebacks, and active projects. Legacy notes that
lack structured metadata are reported as excluded instead of being guessed
into a queue.

Capture is the only write operation in this first release. Start in safe
read-only mode with:

```powershell
.\90-system\automation\scripts\second-self.ps1 web --read-only
```

Use `--no-browser` to print the local URL without opening it, or `--port 9000`
to request a specific local port. The server accepts only loopback requests,
uses no remote assets, and stops with `Ctrl+C`.

Read the [Operating Model](90-system/docs/OPERATING-MODEL.md) and
[Security Model](90-system/docs/SECURITY.md) before granting an agent write
access.

## Common Commands

```powershell
.\90-system\automation\scripts\second-self.ps1 capture --title "Idea"
.\90-system\automation\scripts\second-self.ps1 web
.\90-system\automation\scripts\second-self.ps1 ingest "C:\path\document.pdf"
.\90-system\automation\scripts\second-self.ps1 indexes
.\90-system\automation\scripts\second-self.ps1 register-project "C:\path\project" --name "Project Name"
.\90-system\automation\scripts\backup.ps1 -Destination "E:\SecondSelfBackups"
.\90-system\automation\scripts\restore.ps1 -Archive "E:\SecondSelfBackups\second-self-....tar.age" -Destination "C:\restore"
```

## Privacy

Do not store passwords, API keys, recovery codes, or private keys anywhere in
Second Self. Local and CI privacy checks reduce accidental exposure, but device
encryption and careful review remain required.

Before committing or publishing changes, run:

```powershell
.\90-system\automation\scripts\second-self.ps1 validate --privacy
```

Review `git status` before every commit. Your Layer 1 content, project records,
local configuration, caches, backups, and recovery history must remain
untracked.

## Protected Main Workflow

The bootstrap-configured Git hooks preserve the protected `main` workflow:

1. A commit on local `main` first passes the privacy validation hook.
2. The post-commit hook pushes the commit to `automation/main`.
3. GitHub Actions opens or updates a pull request into `main`.
4. The pull request can be merged after the required `test` check passes.

Set `SECOND_SELF_AUTO_PUBLISH=0` before committing to temporarily disable the
automatic push. Commits made on any branch other than `main` are not
automatically published.
