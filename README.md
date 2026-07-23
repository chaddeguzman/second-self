# Main Brain

Main Brain is a private-data, public-architecture personal knowledge system for
Obsidian, Codex, and Claude.

The Git repository contains schemas, templates, agent rules, skills, and local
automation. Personal notes are stored outside Git and linked into the vault at
runtime.

## Layers

- **Layer 1 - Strategy & Storage:** identity, strategy, notes, journals,
  knowledge, reviews, decisions, imports, and history.
- **Layer 2 - Skills & Projects:** reusable public agent skills and private
  records for external project repositories.

## Quick Start

Requirements: Windows, Git, Python 3.12+, Obsidian, and `age`.

```powershell
.\scripts\bootstrap.ps1
.\scripts\brain.ps1 validate
```

Bootstrap creates `%USERPROFILE%\MainBrainData`, writes an ignored local
configuration file, and assembles the vault with directory junctions. It never
commits personal data.

See [Operating Model](system/OPERATING-MODEL.md) and
[Security Model](system/SECURITY.md) before granting an agent write access.

## Common Commands

```powershell
.\scripts\brain.ps1 capture --title "Idea"
.\scripts\brain.ps1 ingest "C:\path\document.pdf"
.\scripts\brain.ps1 indexes
.\scripts\brain.ps1 register-project "C:\path\project" --name "Project Name"
.\scripts\backup.ps1 -Destination "E:\MainBrainBackups"
.\scripts\restore.ps1 -Archive "E:\MainBrainBackups\main-brain-....tar.age" -Destination "C:\restore"
```

## Privacy

Do not store passwords, API keys, recovery codes, or private keys anywhere in
the brain. The repository includes local and CI privacy checks, but no hook can
replace device encryption and careful review.

