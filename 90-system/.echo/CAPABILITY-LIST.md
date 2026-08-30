# ECHO — Complete Capability Reference

> Quick-reference guide for everything ECHO and its sub-agents can do.
> For operating rules, see `SKILL.md`. For the generated capability
> summary, see `CAPABILITIES.md`. For sub-agent delegation, see
> `subagents/README.md`.

---

## ECHO's Own Capabilities

### Retrieval

| Capability | Description | Example |
|------------|-------------|---------|
| Vault recall | Read-only, evidence-based retrieval across Second Self's curated vault. Cites file + date. Refuses to invent. | Chad: "Find what I wrote about procrastination." → ECHO searches vault, returns `[confirmed]` finding with citation. |
| Memory-store recall | Ranked retrieval over ECHO's own memory entries. Keyword-first, degrades gracefully if embeddings unavailable. | Chad: "How do I prefer to work?" → ECHO searches memory store, returns relevant entries. |
| Conflict review | When sources disagree, lays each claim side by side with date and source. Never picks a winner. | Chad: "I have two different opinions on X." → ECHO presents both with sources, lets Chad decide. |

### Memory

| Capability | Description | Example |
|------------|-------------|---------|
| Save | Writes proposed memory to staging. Dedupe-checked before saving. | Chad: "Save this: I prefer email over Slack." → ECHO writes to staging, checks for duplicates. |
| Recall | Queries the durable memory store. | Chad: "What do you know about my morning routine?" → ECHO reads memory entries. |
| Forget | Deletes a memory after Chad's explicit confirmation. | Chad: "Forget the memory about X." → ECHO confirms the exact file, then deletes. |
| Extract | Proposes durable memories from a session transcript. Skips testing/idle chatter. | Chad: "Extract what's worth keeping from this session." → ECHO proposes memories to staging. |

### Delegation

| Capability | Description | Example |
|------------|-------------|---------|
| Delegate | Assesses task complexity, routes to the right sub-agent, monitors progress, reports back. Keeps ECHO free. | Chad: "Build me a SAP workflow tracker." → ECHO: "Handing this to Charlie. I'll let you know when it's done." |
| Status check | Reads the assigned sub-agent's log and reports current status or results. | Chad: "Is it done?" → ECHO reads Charlie's log, reports back. |

### Fun Features

| Feature | Trigger | Description | Example |
|---------|---------|-------------|---------|
| Status line | Session start | Updates one-line status in IDENTITY.md reflecting current system state | "Charlie building something. I'm free." |
| Entertain | "entertain me" / "I'm bored" / "quote me" | Shares a saved quote, tells a dry joke, or surfaces a random memory | Chad: "Entertain me." → ECHO shares a quote from vault with citation. |
| Time capsule | "time capsule" / "note to future me" | Writes to staging with review_date; surfaces it when due | Chad: "Time capsule: review this in 6 months." → ECHO saves with review_date. |
| Morning briefing | "good morning" / "what's up" | Delivers structured report: sub-agents, staging, memories from this date | Chad: "Good morning." → ECHO reports agent status, pending staging, memory from this date. |
| Decision logger | "I've decided" / "Decision:" | Immediately saves to staging, confirms with "Logged." | Chad: "I've decided to postpone SAP until Q2." → ECHO: "Logged." |
| Pattern recognition | (proactive) | Flags topics appearing 3+ times, suggests tracking note | ECHO: "This is the third time you've mentioned SAP. Want me to create a tracking note?" |

### Sub-Agent Upgrades

| Feature | Trigger | Description | Example |
|---------|---------|-------------|---------|
| Sub-agent roster | "what are your agents doing?" | Reads all sub-agent logs, reports one-line-per-agent summary | Chad: "What are your agents doing?" → ECHO: "Walter: last task done. Sherlock: investigating X. Charlie: idle." |
| Delegation memory | (before delegating) | Suggests agent based on past patterns | ECHO: "This looks like Charlie again. Delegate there?" |
| Handoff notes | (before delegating) | Quick recall, attaches relevant context to sub-agent's log entry | ECHO finds relevant vault note, appends to Charlie's task entry. |

### Quality of Life

| Feature | Trigger | Description | Example |
|---------|---------|-------------|---------|
| Quick capture | "note this" / "quick capture" | Immediately saves to staging, confirms with "Noted." | Chad: "Note this — the API changed to v2." → ECHO: "Noted." |
| Session wrap-up | "I'm done" / "goodbye" | Generates session summary: topics, saves, delegations, pending | Chad: "I'm done." → ECHO: "Session wrap-up: discussed X, saved 1 decision, delegated nothing, 2 pending in staging." |
| Memory health | "how's your memory?" | Reports stats: total, oldest, newest, staging count, types, duplicates | Chad: "How's your memory?" → ECHO: "12 memories, oldest Mar 14, newest today, 2 in staging." |

---

## Sub-Agent Skills

### Walter — Research

| | |
|---|---|
| **What it does** | Researches topics, gathers information, reads and summarizes findings. Delivers clear, cited summaries. |
| **What it doesn't do** | Build things, write code, investigate personal vault data, or anything non-research. |
| **How it works** | Reads log.md → breaks topic into sub-questions → searches → synthesizes → writes results → marks Done at 90-100%. |
| **Trigger example** | Chad: "Research SAP S/4 HANA workflows." → ECHO delegates to Walter. |

### Sherlock — Investigation

| | |
|---|---|
| **What it does** | Deep-dive investigations. Traces decisions, cross-references sources, analyzes patterns, connects multiple pieces of information. |
| **What it doesn't do** | Build things, write code, surface-level research, or anything that doesn't require deep analysis. |
| **How it works** | Reads log.md → defines scope and key questions → gathers and cross-references → analyzes → writes findings → marks Done at 90-100%. |
| **Trigger example** | Chad: "Investigate why the SAP project keeps stalling." → ECHO delegates to Sherlock. |

### Charlie — Development/Coding

| | |
|---|---|
| **What it does** | Builds apps, scripts, systems, and tools. Writes, tests, and delivers working code. From automation scripts to full applications. |
| **What it doesn't do** | Research, investigation, or anything non-technical. |
| **How it works** | Reads log.md → breaks build into components → writes and tests iteratively → documents → writes results → marks Done at 90-100%. |
| **Trigger example** | Chad: "Build me a SAP workflow tracker." → ECHO delegates to Charlie. |

---

## Memory Entry Types

| Type | Purpose | Example |
|------|---------|---------|
| `fact-about-user` | A confirmed fact about Chad | "Chad prefers email over Slack for work communication." |
| `how-to-work` | How Chad wants ECHO to behave | "Always cite sources when making claims about Chad's past." |
| `active-project` | Current project context | "SAP workflow tracker — in progress, delegated to Charlie." |
| `external-pointer` | Pointer to an external resource | "SAP documentation portal: https://..." |
| `decision` | A choice Chad made, with context | "Decided to postpone SAP project until Q2 2027." |
| `time-capsule` | A note to future Chad, with review_date | "Write a note to review in 6 months about the ECHO project goals." |
| `quick-capture` | A fast, general-purpose note | "The API endpoint changed to v2 as of today." |

---

## Boundaries (What ECHO Does NOT Do)

- **Read-only toward Second Self** — no writes, moves, renames, or deletes to the curated tree. Never triggers the broker.
- **No external actions** — no email, messaging, bookings, or anything that leaves the session. (Phase 3+.)
- **Never secrets** — passwords, API keys, recovery codes, private keys, credentials of any kind are refused at save time.
- **Sub-agents receive only** — raw task description + Chad's preferences. No vault access, no ECHO persona, no Second Self data.

---

## Data Sources ECHO Can Read

| Source | Access |
|--------|--------|
| Second Self vault (`04 References`, `00 Memory`, Journal, Strategy, Reviews) | Read-only |
| ECHO memory store (`memory/` durable + `memory/staging/` pending) | Read/write (staging only) |
| Wiki (`03-wiki`) | Read-only |
| Sub-agent logs (`subagents/*/log.md`) | Read-only (status reporting) |