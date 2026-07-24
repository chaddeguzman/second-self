# Second Self

## What Is Second Self?

Second Self is a private personal-context and knowledge system for you and your
trusted local AI agents. It brings together your identity, values, memories,
experiences, knowledge, strategy, projects, reviews, decisions, and learned
ways of working.

Its purpose is to help you:

- remember important personal context across time;
- capture thoughts, notes, documents, and experiences;
- review goals, commitments, projects, and lessons;
- give trusted agents relevant context without rebuilding it every session; and
- turn what you know and care about into consistent action.

The design separates public architecture from private data. This repository can
be cloned or forked, while your personal content remains local and excluded
from Git.

## How Second Self Works

Second Self supports five connected functions:

1. **Capture** — Add thoughts, notes, documents, links, web clippings, and
   corrections to an inbox or the appropriate personal folder.
2. **Organize** — Keep memories, notes, journals, strategy, references, reviews,
   and projects in a predictable structure.
3. **Recall** — Retrieve task-relevant evidence instead of relying on an AI
   agent's assumptions or loading the entire archive.
4. **Review** — Reassess captures, priorities, conflicts, commitments, and
   lessons through weekly and quarterly reviews.
5. **Act and learn** — Use personal context to guide project work, then return
   important decisions, progress, and reusable lessons to Second Self.

Markdown files remain the source of truth. The local dashboard, Obsidian, and
trusted agents are different ways to view and work with that same system.

## Architecture

### Layer 1 — Strategy and Storage

`01-strategy-storage` holds your durable whole-person context:

- `00 Memory` — confirmed, durable personal context;
- `01 Notes` — ideas, observations, working knowledge, and source intake;
- `02 Journal` — dated experiences and reflections;
- `03 Strategy` — purpose, values, goals, priorities, and decisions;
- `04 References` — research, books, quotations, guides, and documents; and
- `05 Reviews` — weekly, quarterly, project, and other review records.

Layer 1 is private, stored locally, and excluded from GitHub.

### Layer 2 — Skills and Projects

`02-skills-projects` turns context into repeatable action:

- `skills` contains reusable workflows for Codex, Claude, and other agents; and
- `projects` contains private project context or independent project
  repositories.

Reusable skills may be versioned in Git. The contents of `projects` stay local.

### LLM Wiki

`03-wiki` is a private, agent-maintained navigation and synthesis layer. It
connects topics, entities, sources, analyses, and open questions without
replacing the underlying evidence.

New source material enters `01-strategy-storage/01 Notes/00 Raw`. After a
reviewed processing transaction, the original source moves to the immutable
`01-strategy-storage/01 Notes/99 Processed` archive and the wiki receives
traceable derived pages.

### System Area

`90-system` contains the technical machinery:

- `app` — the local Python application;
- `automation` — launchers, scripts, agent hooks, and Git hooks;
- `docs` — operating, security, schema, and template documentation;
- `migrations` — controlled structure changes; and
- `tests` — automated verification.

Users normally work in Layers 1 and 2. Agents and developers maintain the
system area.

## System Layout

```text
second-self/
|-- 01-strategy-storage/       Private personal context (Layer 1)
|   |-- 00 Memory/
|   |-- 01 Notes/
|   |-- 02 Journal/
|   |-- 03 Strategy/
|   |-- 04 References/
|   `-- 05 Reviews/
|-- 02-skills-projects/        Skills and private projects (Layer 2)
|   |-- skills/
|   `-- projects/
|-- 03-wiki/                   Private derived knowledge links
|-- 90-system/                 Application, automation, docs, and tests
|-- AGENTS.md                  Agent operating rules
`-- Start-Second-Self.cmd      One-click local launcher
```

Bootstrap keeps private content outside the public Git worktree and connects it
back into this layout through ignored Windows directory junctions. The
repository therefore looks like one Obsidian vault while preserving the
public/private boundary.

## Information and Folder Flow

```text
Capture or import
        |
        v
01 Notes/00 Raw or another Layer 1 folder
        |
        +--> Weekly and quarterly review
        |         |
        |         +--> confirmed Memory or Strategy updates
        |         +--> priorities, commitments, and resolved conflicts
        |
        +--> reviewed wiki processing
                  |
                  +--> original source archived in 01 Notes/99 Processed
                  `--> derived, traceable pages added to 03-wiki

Relevant Layer 1 context
        |
        v
Skills and project work in Layer 2
        |
        v
Decisions, progress, and reusable lessons return through review/writeback
```

Primary evidence remains in Memory, Notes, Journal, Strategy, References,
Reviews, processed sources, and project records. Wiki pages help navigate and
synthesize that evidence but do not silently replace it.

## Before You Clone

Second Self currently targets Windows.

| Prerequisite | Status | Why it is needed |
| --- | --- | --- |
| Windows 10 or 11 with Windows PowerShell 5.1 | Required | Runs the bootstrap, launcher, validation, backup, and restore scripts and supports the directory-junction layout. |
| [Git for Windows](https://git-scm.com/download/win) | Required | Clones the repository and manages versioned architecture and workflows. |
| [Python 3.12 or newer](https://www.python.org/downloads/windows/) | Required | Runs the local application and installs its locked dependencies. Select **Add Python to PATH** if offered. |
| Internet connection | Required for initial setup | Downloads the repository and Python packages. |
| [Visual Studio Code](https://code.visualstudio.com/) | Recommended | Provides the documented editing, terminal, Source Control, and project workflow. Another Git-aware editor can be used. |
| [Obsidian](https://obsidian.md/download) | Recommended | Provides the intended Markdown knowledge-base interface. |
| [Obsidian Web Clipper](https://obsidian.md/clipper) | Optional | Adds one-click browser capture for web pages, highlights, links, and metadata. |
| BitLocker or Windows device encryption | Strongly recommended | Protects the private plaintext data on the local system drive. |
| [`age`](https://github.com/FiloSottile/age) | Required for backup and restore | Encrypts manual Second Self snapshots; it is not required for basic local use. |
| GitHub account | Optional | Needed to fork, publish changes, use the automated pull-request workflow, or clone GitHub-hosted projects. |
| Codex or Claude | Optional | A trusted local agent can retrieve context and run workflows, but Obsidian and the dashboard work without one. |

### Install the Tools

With Windows Package Manager, open PowerShell and run:

```powershell
winget install --id Git.Git --exact
winget install --id Python.Python.3.12 --exact
winget install --id Microsoft.VisualStudioCode --exact
winget install --id Obsidian.Obsidian --exact
winget install --id FiloSottile.age --exact
```

Restart PowerShell, then verify the required command-line tools:

```powershell
git --version
python --version
```

Python must report version 3.12 or newer. If it opens the Microsoft Store or
reports an older version, fix the Python installation or `PATH` before
continuing. If you will use encrypted backups, also run `age --version`.

`winget` is an installation convenience, not a Second Self requirement. You can
use the linked official installers instead.

## Quick Start: Create Your Own Second Self

### 1. Clone or Fork the Repository

Clone the original repository:

```powershell
git clone https://github.com/chaddeguzman/second-self.git
cd second-self
```

To maintain your own public architecture, fork the repository on GitHub first
and clone your fork instead.

### 2. Run First-Time Setup

From the repository root:

```powershell
.\90-system\automation\scripts\bootstrap.ps1
.\90-system\automation\scripts\second-self.ps1 validate
```

Bootstrap:

- creates a Python virtual environment and installs locked dependencies;
- creates `%USERPROFILE%\SecondSelfData` for private content;
- writes the ignored `.second-self.local.json` configuration;
- connects private folders into the repository as directory junctions;
- configures the privacy and protected-Git hooks; and
- checks whether device encryption is enabled.

The setup script checks for Git, Python, Obsidian, and `age` and may offer
`winget` commands for missing tools.

### 3. Open Your Vault

Open the repository root as an Obsidian vault. Begin adding personal content to
the six folders under `01-strategy-storage`; keep project work under
`02-skills-projects/projects`.

Read the [Operating Model](90-system/docs/OPERATING-MODEL.md) and
[Security Model](90-system/docs/SECURITY.md) before granting an agent write
access.

### 4. Optional: Add Obsidian Web Clipper

Install the [Obsidian Web Clipper](https://obsidian.md/clipper) browser
extension to quickly capture articles, YouTube links, highlighted passages,
short snippets, and other useful material from the internet.

Web Clipper saves pages and metadata as durable Markdown files in your vault so
you can keep, search, and read them offline. Its templates let you customize
the note location, filename, content, and properties for different websites.
For example, a template can preserve the page title, source URL, author,
published date, capture date, and tags.

For the Second Self workflow, configure your general web-capture template to
save new clips to:

```text
01-strategy-storage/01 Notes/00 Raw
```

This keeps incoming web material in the review queue. A trusted agent can later
process it into the LLM Wiki, preserve the original under `99 Processed`, and
create traceable topic or source pages. Use additional Web Clipper templates
when a site or content type needs a different format.

### 5. Start the Local Home

Double-click `Start-Second-Self.cmd` for one-click startup. On the first run it
performs bootstrap if needed, starts the private local server, and opens the
dashboard.

You can also launch it from PowerShell:

```powershell
.\90-system\automation\scripts\second-self.ps1 web
```

The Home page opens on `http://127.0.0.1:8765/` and tries ports through `8774`
if needed. It uses only loopback access and no remote assets. Stop it with
`Ctrl+C`.

For read-only mode or a custom port:

```powershell
.\90-system\automation\scripts\second-self.ps1 web --read-only
.\90-system\automation\scripts\second-self.ps1 web --port 9000
```

## Everyday Commands

```powershell
# Capture and retrieve local work
.\90-system\automation\scripts\second-self.ps1 capture --title "Idea"
.\90-system\automation\scripts\second-self.ps1 ingest "C:\path\document.pdf"
.\90-system\automation\scripts\second-self.ps1 indexes

# Maintain the private LLM Wiki
.\90-system\automation\scripts\second-self.ps1 wiki init
.\90-system\automation\scripts\second-self.ps1 wiki add "C:\path\source.pdf"
.\90-system\automation\scripts\second-self.ps1 wiki status
.\90-system\automation\scripts\second-self.ps1 wiki lint

# Register a project
.\90-system\automation\scripts\second-self.ps1 register-project "C:\path\project" --name "Project Name"

# Create or restore an encrypted snapshot
.\90-system\automation\scripts\backup.ps1 -Destination "E:\SecondSelfBackups"
.\90-system\automation\scripts\restore.ps1 -Archive "E:\SecondSelfBackups\second-self-....tar.age" -Destination "C:\restore"
```

## Working with Project Repositories

A project can be a normal folder or an independent Git repository inside
`02-skills-projects/projects`:

```text
second-self/
`-- 02-skills-projects/
    `-- projects/
        `-- my-project/
            |-- .git/
            `-- project files
```

To clone a project from the Second Self root:

```powershell
cd "02-skills-projects/projects"
git clone https://github.com/<username>/<project>.git
cd <project>
git remote -v
```

The nested repository has its own history and remote. Second Self ignores the
entire project folder, including its `.git` metadata.

Keep the repositories separate:

- run project Git commands from the nested project's root;
- run Second Self Git commands from the Second Self root;
- open a nested project in its own VS Code window when possible;
- confirm the active repository before staging, committing, or pushing; and
- never commit a private project through the Second Self repository.

Normal VS Code **Sync Changes** may be appropriate for an independent project.
Do not use **Sync Changes** from the Second Self repository window; Second Self
uses its protected `automation/main` pull-request workflow.

## Frequently Asked Questions

### Where is my private data stored?

By default, bootstrap creates `%USERPROFILE%\SecondSelfData` and links its
private folders into the repository. The ignored `.second-self.local.json`
records the active location.

### Is my personal content uploaded to GitHub?

No. Layer 1, project records, the LLM Wiki, local configuration, caches,
backups, and recovery history are ignored. Always run the privacy validation
and review `git status` before publishing changes.

### Can I use Second Self without Obsidian or an AI agent?

Yes. The files are Markdown and can be edited with another text editor. The
local dashboard also works without an AI agent. Obsidian and trusted agents
provide the intended full experience.

### Can I use macOS or Linux?

Not with the current bootstrap and launcher. The supported setup targets
Windows PowerShell and Windows directory junctions.

### What should I never store in Second Self?

Never store passwords, API keys, access tokens, recovery codes, or private
cryptographic keys. Use a credential manager instead.

### How do I back up my Second Self?

Install `age`, connect a removable backup drive, and run the backup command
shown under [Everyday Commands](#everyday-commands). Keep the backup and its
encryption passphrase in appropriately protected, separate locations.

## Essential Guidelines

- **Protect privacy.** Enable BitLocker or Windows device encryption because
  active private data is readable plaintext for Obsidian and local search.
- **Keep evidence traceable.** Treat stored notes as evidence, preserve dates
  and sources, and surface contradictions instead of silently choosing a
  version.
- **Respect the folder structure.** Use the six approved Layer 1 folders and
  keep technical machinery under `90-system`.
- **Separate projects from Second Self Git.** Each nested project uses its own
  repository and remote.
- **Use protected changes.** Identity or strategy edits, private exports,
  deletion, moves, renames, and broad changes require reviewed approval through
  the Second Self broker.
- **Validate before committing.**

  ```powershell
  .\90-system\automation\scripts\second-self.ps1 validate --privacy
  ```

- **Follow the protected `main` workflow.** A local commit on `main` passes the
  privacy hook, publishes to `automation/main`, and opens or updates a GitHub
  pull request. Merge only after the required test passes, using **Create a
  merge commit**. Do not use rebase, squash, direct pushes to protected `main`,
  or VS Code **Sync Changes** for the Second Self repository.
