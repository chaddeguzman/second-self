# Second Self

Second Self is a private-data, public-architecture system that represents Chad
as a whole person for both personal use and trusted AI agents. It brings
together identity, values, principles, knowledge, memories, experiences,
events, strategy, projects, reviews, and learned ways of working across
Obsidian, Codex, and Claude.

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

You can copy existing documents directly into these folders. Agents may create
additional support folders for indexes, audit records, imports, and trash; those
are system-managed.

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

Bootstrap creates `%USERPROFILE%\SecondSelfData`, writes an ignored local
configuration file, and assembles the vault with directory junctions. It never
commits personal data.

Read the [Operating Model](90-system/docs/OPERATING-MODEL.md) and
[Security Model](90-system/docs/SECURITY.md) before granting an agent write
access.

## Common Commands

```powershell
.\90-system\automation\scripts\second-self.ps1 capture --title "Idea"
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
