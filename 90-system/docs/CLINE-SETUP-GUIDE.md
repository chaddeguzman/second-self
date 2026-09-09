# Cline Setup Guide — First-Time Users

> A step-by-step guide for installing Cline, integrating it with Second Self, and
> using it to build AI-assisted products, systems, and services.

This guide assumes a **Windows 10 or 11** workstation, which is Second Self's
current target platform (see [Quick Start](../Quick%20Start.md) for rationale).

---

## Table of Contents

1. [Prerequisites — Install the Foundation](#1-prerequisites--install-the-foundation)
2. [Install Cline in VS Code](#2-install-cline-in-vs-code)
3. [Clone and Bootstrap Second Self](#3-clone-and-bootstrap-second-self)
4. [Open the Workspace in VS Code](#4-open-the-workspace-in-vs-code)
5. [Verify Cline Can See Second Self](#5-verify-cline-can-see-second-self)
6. [Using Cline with Second Self](#6-using-cline-with-second-self)
7. [Building AI-Assisted Products](#7-building-ai-assisted-products)
8. [Best Practices](#8-best-practices)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisites — Install the Foundation

Second Self is a personal-context system. Cline is one of the trusted local AI
agents that can work with it. Before installing Cline, you need the core
toolchain.

### Required

| Tool | Why | Install command |
|------|-----|-----------------|
| **Windows 10/11** | Runs PowerShell, directory junctions, and the bootstrap scripts. | Pre-installed |
| **Git for Windows** | Clones the repo and manages Git operations. | `winget install --id Git.Git --exact` |
| **Python 3.12+** | Runs the local app, validates privacy, and powers Cline's Python tooling. | `winget install --id Python.Python.3.12 --exact` |
| **Visual Studio Code** | The primary editor and Cline host. | `winget install --id Microsoft.VisualStudioCode --exact` |

> **After installing:** restart PowerShell and verify:
> ```powershell
> git --version
> python --version   # must report 3.12 or newer
> code --version
> ```

### Strongly Recommended

| Tool | Why | Install command |
|------|-----|-----------------|
| **BitLocker or Windows device encryption** | Second Self stores private data as readable plaintext locally. Encryption protects it. | Windows Security ▸ Device encryption (or Control Panel ▸ BitLocker) |
| **Obsidian** | The intended Markdown interface for browsing the knowledge vault. | `winget install --id Obsidian.Obsidian --exact` |

### Optional (useful for backups and publishing)

| Tool | Why | Install command |
|------|-----|-----------------|
| **`age`** | Encrypts manual backup snapshots. | `winget install --id FiloSottile.age --exact` |
| **GitHub account** | Needed to fork, publish changes, or clone GitHub-hosted projects. | [github.com](https://github.com/join) |

---

## 2. Install Cline in VS Code

Cline is an open-source agent that runs inside VS Code. It does **not** register
any hooks or special configuration with Second Self — it simply reads
`AGENTS.md`, `CLAUDE.md`, and other rules files (see
[CLAUDE.md](../CLAUDE.md)).

### Step 1 — Install the Extension

1. Open VS Code.
2. Go to the **Extensions** view (`Ctrl+Shift+X`).
3. Search for **Cline** (publisher: `cline`).
4. Click **Install**.

   Alternatively from PowerShell:
   ```powershell
   code --install-extension cline.cline
   ```

### Step 2 — Sign In to Cline

1. After installation, press `Ctrl+Shift+P` and run **Cline: Sign In**.
2. Choose your authentication method:
   - **Cline Account** (recommended for most users) — sign in with GitHub, Google,
     or email.
   - **Bring Your Own Key (BYOK)** — if you have an OpenAI, Anthropic, Gemini,
     or OpenRouter API key, you can configure Cline to use it directly.
3. Select a model. The default recommendation is a capable reasoning model
   (e.g., Claude 3.7 Sonnet or equivalent).

> **Tip:** Cline's settings are stored in VS Code's `settings.json`. You can
> configure the default model, context size limits, and tool permissions there.
> Open it via **Settings** (`Ctrl+,`) → search "Cline".

### Step 3 — Configure Cline Preferences

In VS Code Settings (`Ctrl+,` → "Cline"), set:

| Setting | Recommended value | Purpose |
|---------|-------------------|---------|
| `cline.model` | Your preferred model | Sets the default LLM |
| `cline.maxTokens` | `16000`–`32000` | Controls response length |
| `cline.enableCheckpoints` | `true` | Saves/resumes conversation state |
| `cline.autoApprove` | `false` (at first) | Review every tool call until you're comfortable |

> See [Cline's official docs](https://docs.cline.ai/) for advanced configuration,
> custom instructions, and MCP server integration.

---

## 3. Clone and Bootstrap Second Self

These steps mirror the [Quick Start](../Quick%20Start.md) but are included here
for completeness.

### Option A — Use the existing repo (if you already forked it)

```powershell
git clone https://github.com/<your-username>/second-self.git
cd second-self
```

### Option B — Use the original (read-only)

```powershell
git clone https://github.com/chaddeguzman/second-self.git
cd second-self
```

### Run the bootstrap

```powershell
.\90-system\automation\scripts\bootstrap.ps1
```

This will:

- Create a Python virtual environment and install locked dependencies.
- Create `%USERPROFILE%\SecondSelfData` for your private content.
- Write the git-ignored `.second-self.local.json` (records your `data_root`).
- Connect private folders into the repo as directory junctions.
- Configure privacy and protected-Git hooks.
- Check whether BitLocker or device encryption is enabled.

### Validate

```powershell
.\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only
python -m pytest
```

---

## 4. Open the Workspace in VS Code

The entire repository root is the VS Code workspace. The private Layer 1 folders
(`01-strategy-storage/...`, `02-skills-projects/projects/...`, `03-wiki/...`) are
connected as directory junctions, so they appear in VS Code just like any other
folder — but their contents remain excluded from Git.

```powershell
code .
```

> **Important:** Open the **repository root** as the workspace, not a subfolder.
> Cline/Claude Code needs the root-level `AGENTS.md` and `CLAUDE.md` to load the
> correct operating rules.

---

## 5. Verify Cline Can See Second Self

1. In VS Code, open the Cline panel (click the Cline icon in the Activity Bar, or
   press `Ctrl+Shift+P` → **Cline: Open Cline**.
2. At the Cline chat prompt, type:

   ```
   Hello — are you in the Second Self workspace? Please check AGENTS.md.
   ```

3. Cline will read `AGENTS.md`, `CLAUDE.md`, and `90-system/docs/OPERATING-MODEL.md`
   to orient itself. It should respond that it sees the rules files and understand
   the startup sequence, privacy model, and protected-change workflow.

---

## 6. Using Cline with Second Self

### How Cline Reads Context

When Cline starts a new session in the Second Self workspace, it follows the
**agent startup sequence** defined in `AGENTS.md`:

1. Reads `01-strategy-storage/00 Memory/00 Second Self Context.md` — the system's
   purpose, architecture, and privacy model.
2. Reads `AGENTS.md` — the canonical agent policy.
3. Reads `CLAUDE.md` — Claude/Cline-specific addenda.
4. Reads `90-system/docs/OPERATING-MODEL.md` and `SECURITY.md` — operating and
   security models.
5. Retrieves task-relevant notes from Layer 1 folders (starting with
   `04 References` for most requests, or `00 Memory` for identity/values
   questions).

> **Cline does NOT use Claude Code's `pre_tool_use` hook.** That hook is
> Claude Code-specific and reads a JSON event schema that other agents don't
> understand. Do not register it with Cline (see `AGENTS.md`, Agent Tool Hygiene).

### Daily Commands

| Goal | Command |
|------|---------|
| Capture a note | `.\90-system\automation\scripts\second-self.ps1 capture --title "Idea"` |
| Journal | `.\90-system\automation\scripts\second-self.ps1 journal --body "Today I..."` |
| Search | `.\90-system\automation\scripts\second-self.ps1 search "topic"` |
| Recall (evidence-based) | `.\90-system\automation\scripts\second-self.ps1 recall "topic"` |
| List due items | `.\90-system\automation\scripts\second-self.ps1 due` |
| Run the local server | `.\90-system\automation\scripts\second-self.ps1 web` |
| Validate privacy | `.\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only` |
| Run tests | `python -m pytest` |

### Working with Skills

Browse `02-skills-projects/skills/` to discover reusable workflows. Each skill has
a `SKILL.md` with instructions. Relevant skills include:

- **`echo`** — Fragment-based personal recall (treats half-remembered facts as
  retrieval cues and runs `second-self-recall`).
- **`second-self-recall`** — Evidence-based recall with citations.
- **`second-self-capture`** — Import and organize new source material.
- **`second-self-commit`** — Safe commit workflow with privacy validation.
- **`second-self-wiki`** — Process Raw sources into the LLM Wiki.

### Sub-Agent Delegation (Project ECHO)

When a task is large enough to warrant delegation, ECHO routes work to one of the
sub-agents under `90-system/.echo/subagents/`:

| Agent | Purpose |
|-------|---------|
| **Charlie** | Development and coding tasks |
| **Sherlock** | Investigation and analysis |
| **Walter** | Deep research with multi-source synthesis |

To delegate: simply say *"ECHO, delegate [task] to [agent]"* or use a preset:
`quick-build`, `full-build`, `deep-dive`, or `research`.

---

## 7. Building AI-Assisted Products

Second Self provides the **context layer** — who you are, what you value, what
you've learned. Cline provides the **execution layer** — it reads that context
and writes code, documents, tests, and project plans.

### Project Layout

```
second-self/
├─ 02-skills-projects/
│  ├─ skills/              ← reusable workflows (public, tracked)
│  └─ projects/             ← your local projects (private, git-ignored)
│     └─ my-project/
│        ├─ .git/           ← own independent Git repo
│        └─ ...project files
```

### Workflow

1. **Create a project folder** under `02-skills-projects/projects/`:
   ```powershell
   mkdir "02-skills-projects/projects/my-ai-app"
   cd "02-skills-projects/projects/my-ai-app"
   git init
   git remote add origin https://github.com/<you>/my-ai-app.git
   ```

2. **Give Cline context.** Before starting, tell Cline to read relevant Layer 1
   notes. For example:
   ```
   Cline, before we start building, please recall any notes I have on
   "AI product strategy" or "minimum viable AI agent design."
   ```

3. **Build iteratively.** Cline will:
   - Read `AGENTS.md` for operating rules.
   - Use skills as needed (capture, commit, wiki, etc.).
   - Write code, tests, and documentation.
   - Ask you to review and approve before committing.

4. **Commit safely.** Use the `second-self-commit` skill or:
   ```powershell
   .\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only
   python -m pytest
   git add -A
   git commit -m "Add feature X"
   git push
   ```

5. **Return lessons to Second Self.** After the project is done, use the
   `second-self-project-writeback` skill to save reusable lessons back to
   `01-capture`, `04-references`, or `05-reviews`.

### Key Rules for Cline

| Rule | Why |
|------|-----|
| **Never commit private data.** | `.second-self.local.json`, Layer 1 contents, and project files are git-ignored. |
| **Run validation before every commit.** | `.\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only` |
| **Use the protected `main` workflow.** | Commit on `main`, let the post-commit hook create a PR to `automation/main`, merge with **Create a merge commit** — never rebase or squash. |
| **Don't use `Sync Changes`** on the Second Self repo. | Use it only on independent project repos. |
| **Cite evidence, never invent.** | Cite internal files and dates for decisions and recalled facts. |

---

## 8. Best Practices

### Start Cline in the Right Folder

Always open the **Second Self repository root** in VS Code. Never open a
subfolder as a separate workspace — Cline needs the root-level `AGENTS.md` to
load the correct rules.

### Keep Privacy Validation in Mind

Run privacy validation regularly:
```powershell
.\90-system\automation\scripts\second-self.ps1 validate --privacy
```
This checks that no private paths or personal content leaked into tracked files.

### Reduce Cline Tool-Call Failures

From `AGENTS.md` — Agent Tool Hygiene:

- **Split large writes** into smaller `write_to_file` or `replace_in_file` calls.
  A single mega-write is the most likely to be truncated in transit.
- **Retry "missing required parameter" errors** — this is usually an adapter-side
  truncation, not a Second Self defect.
- **Read large files selectively** — use line ranges, tail, or grep instead of
  loading everything.

### Use Cline's Memory Features

Enable `cline.enableCheckpoints` in VS Code settings to save and resume
conversation state. This is especially useful for long-running project work.

### Sync with the Local Server

The local dashboard (`http://127.0.0.1:8765`) provides a web interface for
recalling notes, capturing thoughts, and managing the LLM Wiki. You can use it
side-by-side with Cline in VS Code.

---

## 9. Troubleshooting

### "I see 'missing required parameter' errors in Cline"

This is an adapter-side truncation issue, **not** a Second Self defect. Cline does
not register any hooks or MCP servers with Second Self. Simply retry the same
tool call. See `AGENTS.md` → Agent Tool Hygiene for prevention tips.

### "Cline doesn't see my private notes"

Check `.second-self.local.json`:
```json
{
  "schema_version": 1,
  "data_root": "C:\\Users\\<you>\\SecondSelfData"
}
```
If `data_root` is incorrect, re-run the bootstrap script.

### "The workspace shows empty folders"

The private junctions may not have been created. Re-run bootstrap:
```powershell
.\90-system\automation\scripts\bootstrap.ps1
```

### "Cline is slow or runs out of context"

- Reduce the number of files Cline reads in one turn.
- Use `second-self-recall` for targeted searches rather than opening entire folders.
- Enable Cline's context-compression features in settings.

### "I want to use Cline with a different model"

Go to VS Code Settings → Cline → Model, and select your preferred provider and
model. If using BYOK, ensure your API key is configured under
**Cline: Manage Account** → **Add Provider**.

---

## Next Steps

- [Quick Start](../Quick%20Start.md) — general Second Self setup and everyday commands
- [AGENTS.md](../AGENTS.md) — canonical agent policy (read this as Cline on first launch)
- [CLAUDE.md](../CLAUDE.md) — Claude/Cline-specific addenda
- [Operating Model](90-system/docs/OPERATING-MODEL.md) — recall, review, and decision-making
- [Security Model](90-system/docs/SECURITY.md) — boundary, prohibited content, and protected operations
- [FAQ](../FAQ.md) — privacy, platform support, and Cline-specific notes

---

*This guide is part of the Second Self system documentation. For questions or
corrections, file a GitHub issue or discuss with Chad.*
