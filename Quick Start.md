# Quick Start

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

## Create Your Own Second Self

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
