# ECHO Sub-Agent System

> This folder contains ECHO's sub-agents — specialized, single-purpose
> agents that handle big, hard, time-consuming tasks so ECHO stays free
> for Chad.

## What is a sub-agent?

A sub-agent is a focused specialist. It does **one thing very well and
nothing else**. Each sub-agent runs as a separate LLM session (another
Hermes/Claude window) that reads its own folder, works asynchronously,
and writes results back.

## Golden rule

**ECHO stays free.** Small tasks → ECHO handles directly. Big/hard tasks →
ECHO delegates to a sub-agent and immediately returns to Chad. The
sub-agent works in parallel while ECHO handles other requests.

## Folder structure

```
subagents/
├── README.md          ← this file
├── 01/                ← placeholder (research)
│   ├── SKILL.md       ← specialist operating rules
│   └── log.md         ← compounding task log
├── 02/                ← placeholder (investigation)
│   ├── SKILL.md
│   └── log.md
├── 03/                ← placeholder (development/coding)
│   ├── SKILL.md
│   └── log.md
└── NN/                ← future sub-agents follow same pattern
    ├── SKILL.md
    └── log.md
```

## Sub-agent convention

Each sub-agent folder contains exactly two files:

### SKILL.md

The specialist's operating rules. Simpler than user-facing skills —
no YAML front matter needed. Contains:

- **What I do** — the single specialty
- **What I don't do** — explicit boundaries
- **How I work** — step-by-step process
- **Output format** — how results are reported

### log.md

A compounding, tabular task log. Every task the sub-agent receives
gets a new row. The log grows over time — never deleted.

Format:

```markdown
| Date | Time | Request | Status | Output/Summary |
|------|------|---------|--------|----------------|
| 2026-08-30 | 09:15 | Build SAP workflow tracker | Done | 3 modules delivered. See output/ |
| 2026-08-29 | 14:00 | Research topic X | Done | Summary of findings. |
```

- **Date/Time** — when the task was received
- **Request** — Chad's original request (or ECHO's translation)
- **Status** → `Pending` → `In Progress` → `Done` (or `Cancelled`)
- **Output/Summary** — results, or pointer to an `output/` subfolder

## Delegation flow

1. Chad gives ECHO a task
2. ECHO assesses: small → do it himself. Big → delegate.
3. ECHO writes the task to the right sub-agent's log.md
4. ECHO tells Chad which agent is handling it
5. ECHO stays free for other requests
6. Sub-agent (separate LLM session) reads SKILL.md + log.md, works, updates log
7. Chad asks "is it done?" → ECHO reads the log, reports back

## Context model

Each sub-agent receives:
- Raw task description
- Chad's preferences (from CORE_KNOWLEDGE.md)
- Its own SKILL.md and log.md

Each sub-agent does NOT receive:
- ECHO's persona or identity
- Vault data (04 References, 00 Memory, etc.)
- Second Self curated tree
- ECHO's memory store
- Other sub-agents' data

## Edge cases

| Scenario | Behavior |
|----------|----------|
| ECHO delegates to wrong agent | Chad overrides: "Use Agent 2." ECHO reassigns. |
| Two sub-agents simultaneously | Supported — each has its own session and folder. |
| Sub-agent stuck below 90% | Status stays `In Progress`. ECHO reports partial progress. |
| Chad cancels a task | ECHO updates the log status to `Cancelled`. |

## Adding a new sub-agent

1. Create the next numbered folder: `subagents/NN/`
2. Write `SKILL.md` — define the specialty, boundaries, process, output format
3. Write `log.md` — start with the table header, no rows
4. ECHO can now delegate to it

## Completion standard

A task is **done** when it reaches 90-100% completion. Perfection is not
required — "without fail" means delivered to a usable standard.