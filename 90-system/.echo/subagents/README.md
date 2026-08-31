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
├── walter/            ← research specialist
│   ├── SKILL.md       ← specialist operating rules
│   └── log.md         ← compounding task log
├── sherlock/          ← investigation specialist
│   ├── SKILL.md
│   └── log.md
├── charlie/           ← development/coding specialist
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
| ECHO delegates to wrong agent | Chad overrides: "Use Charlie." ECHO reassigns. |
| Two sub-agents simultaneously | Supported — each has its own session and folder. |
| Sub-agent stuck below 90% | Status stays `In Progress`. ECHO reports partial progress. |
| Chad cancels a task | ECHO updates the log status to `Cancelled`. |

## Questions protocol

When a sub-agent needs more info than the task provides:

1. Agent writes `questions.md` in its folder with specific questions
2. Agent updates log status to `Needs Info`
3. ECHO detects `questions.md`, asks Chad the questions
4. ECHO writes answers to `answers.md` in the agent's folder
5. Agent reads answers, continues work

**Questions must be specific and actionable:**
- ❌ "Tell me more about the project"
- ✅ "What SAP module should the workflow tracker cover — MM, SD, or PP?"

## Agent handoff protocol

When one agent's work should continue with another:

1. Agent writes `handoff.md` in the target agent's folder
2. Contains: what to do, why, relevant findings, context
3. ECHO detects handoff, creates a new task for the target agent
4. ECHO includes the handoff context in the new task entry

**Example:** Walter finds a feature that needs building → writes
`subagents/charlie/handoff.md` → ECHO creates a Charlie task with context.

## Progress checkpoint convention

For tasks estimated at 30+ minutes, agents update their log at checkpoints:

| Checkpoint | What to update |
|------------|----------------|
| 25% | What's done so far, what's next |
| 50% | Progress summary, any blockers |
| 75% | Nearly done, final steps remaining |

Each checkpoint is a brief log entry — 1-2 lines. ECHO reads these when
Chad asks "how's it going?"

## Confidence scoring

Every output includes a numeric confidence percentage:

| Score | Label | Meaning |
|-------|-------|---------|
| 90-100% | High | Multiple sources agree, evidence is solid, reproducible |
| 80-89% | Medium | Some uncertainty, limited sources, or minor conflicts |
| 79% and below | Low | Significant gaps, single source, or high speculation |

Agents calculate confidence by starting at 100% and deducting for each
limitation (missing source -10%, conflicting evidence -15%, unverified -20%).

ECHO flags low-confidence findings (below 80%) when reporting to Chad.

## Pre-completion checklist

Before marking a task Done, agents self-review their work:

**Walter (Research):**
- [ ] Multiple independent sources consulted
- [ ] Confidence levels tagged on findings
- [ ] Source conflicts noted
- [ ] Gaps in evidence identified

**Sherlock (Investigation):**
- [ ] Chain of reasoning documented
- [ ] Evidence cited for each finding
- [ ] Inconsistencies flagged
- [ ] "Still open" items noted

**Charlie (Development):**
- [ ] Code tested and working
- [ ] Known limitations documented
- [ ] Technical debt flagged
- [ ] Setup/run instructions included

## Early blocker alerts

When a sub-agent hits a blocker they can't resolve:

1. Agent updates log status to `Blocked: [reason]`
2. ECHO detects blocked status on next check
3. ECHO immediately tells Chad: "Walter is blocked: [reason]"
4. Chad can provide guidance, reassign, or cancel the task

**Blocker examples:**
- "Blocked: can't access the API documentation"
- "Blocked: conflicting requirements, need Chad to decide"

## Task acceptance

When a sub-agent receives a new task:

1. Agent reads the task in log.md (status: `Pending`)
2. Agent updates status to `In Progress` to acknowledge
3. ECHO knows the agent has accepted and is working

This prevents tasks from sitting unnoticed in the queue.

## Agent status line

Each agent maintains a one-line status at the top of their log.md:

```markdown
# [Agent Name] — Status: [status]

| Date | Time | Request | Status | Output/Summary |
```

**Status values:**
| Status | Meaning |
|--------|---------|
| `Idle` | No active task, available for new work |
| `Working: [brief description]` | Actively working on a task |
| `Blocked: [reason]` | Stuck, needs Chad's help |
| `Done` | Most recent task completed |

ECHO reads these status lines for quick "what are your agents doing?" reports.

## Known limitations

Every output includes a dedicated section for what the agent couldn't do:

```markdown
**Known limitations:**
- [what wasn't verified or tested]
- [what was out of scope]
- [what needs follow-up]
```

This ensures no output looks more complete than it actually is.

## Task templates

Common task types get pre-defined structures. ECHO includes a template
reference when delegating:

| Template | When to use | Structure |
|----------|-------------|-----------|
| `research` | Walter — new topic | Question → Sources → Findings → Confidence → Gaps |
| `investigation` | Sherlock — deep dive | Scope → Evidence → Reasoning → Conclusion → Open items |
| `build` | Charlie — new feature | What → How to run → Tests → Limitations → Debt |
| `bugfix` | Charlie — fix issue | Root cause → Fix → Tests → Regression check |

Agents follow the template that matches their task type for consistent,
predictable output.

## Adding a new sub-agent

1. Create the next numbered folder: `subagents/NN/`
2. Write `SKILL.md` — define the specialty, boundaries, process, output format
3. Write `log.md` — start with the table header, no rows
4. ECHO can now delegate to it

## Completion standard

A task is **done** when it reaches 90-100% completion. Perfection is not
required — "without fail" means delivered to a usable standard.
