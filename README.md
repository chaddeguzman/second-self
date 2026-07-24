# Second Self

Second Self is a private-data, public-architecture system that helps represent
you as a whole person for both personal use and trusted AI agents. It brings
together your identity, values, principles, knowledge, memories, experiences,
events, strategy, projects, reviews, and learned ways of working across
Obsidian, Codex, and Claude.

The repository is designed to be reusable. Its public code, documentation, and
workflows can be cloned or forked, while your personal context remains local
and excluded from Git.

## Before You Clone

Second Self currently targets Windows. Install or confirm the following tools
before cloning the repository:

| Prerequisite | Status | Why it is needed |
| --- | --- | --- |
| Windows 10 or 11 with Windows PowerShell 5.1 | Required | The bootstrap, launcher, validation, backup, and restore scripts use PowerShell and Windows directory junctions. Windows PowerShell is included with supported Windows installations. |
| [Git for Windows](https://git-scm.com/download/win) | Required | Clones the repository and manages its protected update workflow. |
| [Python 3.12 or newer](https://www.python.org/downloads/windows/) | Required | Runs the local application, creates the project virtual environment, and installs the locked Python dependencies. Select **Add Python to PATH** if the installer offers that option. |
| Internet connection | Required for initial setup | Downloads the repository and installs the locked Python packages during bootstrap. |
| [Visual Studio Code](https://code.visualstudio.com/) | Recommended | Provides the documented editing, terminal, Source Control, and nested-project workflow. Another Git-aware editor can be used instead. |
| [Obsidian](https://obsidian.md/download) | Recommended | Provides the intended Markdown knowledge-base interface. The repository root becomes the Obsidian vault after bootstrap. |
| BitLocker or Windows device encryption | Strongly recommended | Protects the private, plaintext Second Self data stored on the local system drive. Bootstrap checks for encryption and requires a risk acknowledgement if it cannot verify protection. |
| [`age`](https://github.com/FiloSottile/age) | Required for backup and restore | Encrypts manual Second Self snapshots. It is not needed to launch and use the local system without encrypted backups. |
| GitHub account | Optional | Needed to fork the repository, publish changes, use the automated pull-request workflow, or clone GitHub-hosted project repositories. It is not required for local-only use after obtaining the files. |
| Codex or Claude | Optional | A trusted local AI agent can retrieve context and run Second Self workflows, but the local dashboard and Obsidian vault can be used without one. |

### Install with Windows Package Manager

On a current Windows installation with `winget`, open PowerShell and run:

```powershell
winget install --id Git.Git --exact
winget install --id Python.Python.3.12 --exact
winget install --id Microsoft.VisualStudioCode --exact
winget install --id Obsidian.Obsidian --exact
winget install --id FiloSottile.age --exact
```

Restart PowerShell after installation so newly installed commands are available
on `PATH`, then verify the required command-line tools:

```powershell
git --version
python --version
```

If `python --version` reports a version older than 3.12 or opens the Microsoft
Store, fix the Python installation or its `PATH` entry before continuing. To
use encrypted backup and restore, also verify:

```powershell
age --version
```

`winget` is only an installation convenience; it is not required by Second
Self. You can use the linked official installers instead. During bootstrap, the
setup script checks for Git, Python, Obsidian, and `age` and can offer the same
`winget` installation commands when a tool is missing.

## Folder Guide

| Folder | Purpose | Maintained by |
| --- | --- | --- |
| `01-strategy-storage` | Private notes, journals, strategy, references, and reviews | You and your agents |
| `02-skills-projects` | Reusable skills and project context | You and your agents |
| `03-wiki` | Private LLM-maintained synthesis and knowledge links | Trusted agents |
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

### LLM Wiki

`01-strategy-storage/01 Notes/00 Raw` is the pending source queue.
Successfully reviewed sources move into the immutable
`01-strategy-storage/01 Notes/99 Processed` archive. The private root
`03-wiki` contains agent-generated source summaries, topics, entities,
analyses, an index, an append-only log, and open questions.

Existing Memory, Notes, Journal, Strategy, References, Reviews, and registered
project records remain in place. Wiki pages help navigate and synthesize that
evidence but do not replace it.

### System

`90-system` keeps technical internals out of the user workspace:

- `app`: Second Self Python application
- `automation`: scripts, hooks, and Git hooks
- `docs`: operating model, security guidance, schemas, and templates
- `migrations`: controlled structure changes
- `tests`: automated verification

## Working with Project Repositories

`02-skills-projects/projects` is the main local storage location for a user's
projects. A GitHub repository can be cloned directly into this folder and used
as an independent nested Git repository.

For example, a project named `lakbay-itinerary-creator` can live at:

```text
second-self/
`-- 02-skills-projects/
    `-- projects/
        `-- lakbay-itinerary-creator/
            |-- .git/
            `-- project files
```

The nested project has its own Git history and GitHub remote. Second Self
ignores the whole nested project directory, including its `.git` metadata, so
the project is never committed or pushed as part of the Second Self repository.

### Clone a Project Using the Terminal

From the Second Self repository root:

```powershell
cd "02-skills-projects/projects"
git clone https://github.com/<username>/lakbay-itinerary-creator.git
cd lakbay-itinerary-creator
git remote -v
```

The final command confirms which GitHub repository will receive the project's
commits.

To commit and push project work:

```powershell
git status
git add .
git commit -m "Describe the project change"
git push
```

Run these commands only from inside the nested project repository.

### Clone a Project Using VS Code

These steps assume the user is already signed in to GitHub through VS Code:

1. Open the Second Self repository in VS Code.
2. Press `Ctrl+Shift+P` to open the Command Palette.
3. Run `Git: Clone`.
4. Choose `Clone from GitHub`.
5. Search for and select the repository. For this example, select
   `lakbay-itinerary-creator`.
6. In the destination-folder picker, select
   `02-skills-projects\projects`. Select the `projects` folder itself; do not
   create a `lakbay-itinerary-creator` folder first because Git creates it
   during cloning.
7. After cloning finishes, choose `Open in New Window` when VS Code prompts
   you to open the repository. If no prompt appears, use **File > Open Folder**
   and open `02-skills-projects\projects\lakbay-itinerary-creator`.
8. In the new window, open Source Control with `Ctrl+Shift+G` and confirm that
   `lakbay-itinerary-creator` is the active repository.

Opening the project in its own VS Code window is recommended. If multiple
repositories appear in Source Control, use the repository selector and verify
the project name before staging or committing.

### Commit and Push a Project Using VS Code

From the VS Code window opened at the nested project:

1. Open Source Control with `Ctrl+Shift+G`.
2. Review the files listed under **Changes**.
3. Select the **+** beside individual files to stage them, or select the **+**
   beside **Changes** to stage all reviewed changes.
4. Enter a commit message in the Source Control message box.
5. Select **Commit**.
6. Select **Sync Changes** or **Push** to send the commit to that project's own
   GitHub repository. For a new local branch, VS Code may show
   **Publish Branch** instead.
7. Open the project on GitHub and confirm that the commit appears in the
   expected repository.

Normal VS Code **Sync Changes** may be used for an independent nested project
when its own repository rules allow it. Do not use **Sync Changes** from the
Second Self repository window: Second Self uses its protected
`automation/main` pull-request workflow.

### Keep the Two Repositories Separate

- Run project Git commands from the nested project's root.
- Run Second Self Git commands from the Second Self repository root.
- Confirm the active repository in VS Code before every commit.
- Each nested project follows its own branch protection, review, and deployment
  rules.
- Second Self may use project status and lessons through its controlled
  handoff and writeback workflows without tracking the project's files.

## Quick Start

Complete the [prerequisites](#before-you-clone), then clone or fork the
repository and open PowerShell in its root folder.

```powershell
.\90-system\automation\scripts\bootstrap.ps1
.\90-system\automation\scripts\second-self.ps1 validate
```

After cloning or forking the repository, bootstrap creates
`%USERPROFILE%\SecondSelfData`, writes an ignored local configuration file, and
assembles the vault with directory junctions. Your personal data remains local
and is never intentionally committed.

### Private local Home

On Windows, double-click `Start-Second-Self.cmd` in the repository root for
one-click startup. It performs first-time bootstrap when needed, starts the
local server, and opens the browser automatically.

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
python -m second_self wiki init
python -m second_self wiki add "C:\path\source.pdf"
python -m second_self wiki status
python -m second_self wiki lint
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
