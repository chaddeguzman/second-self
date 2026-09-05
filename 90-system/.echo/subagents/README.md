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
- [ ] Project documents current (builds above the size gate): PRD.md,
      ARCHITECTURE.md, regenerated ARCHITECTURE-ESSENTIALS.md, thin
      per-project AGENTS.md

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

## Project document convention

Build tasks above the size gate produce four documents inside the
project folder, created from the templates in
`subagents/shared/templates/` **before** any feature code:

| Document | Source of truth for |
|----------|---------------------|
| `PRD.md` | WHAT and WHY — problem, users, requirements, "done" |
| `ARCHITECTURE.md` | HOW — complete design, data models, tech stack |
| `ARCHITECTURE-ESSENTIALS.md` | Derived outline of Architecture — critical decisions only |
| `AGENTS.md` | Thin per-project agent rules — a pointer, never a fork |

**Size gate:** quick fixes and one-off scripts (under ~30 minutes, no
data model, no stack choice) skip the documents. Everything else gets
them, scaffold-first: folders, data models, and stub files exist before
individual features are built, so the project has a clear scope and
Chad can redirect cheaply.

**Reading rule:** agents load `ARCHITECTURE-ESSENTIALS.md` at boot —
not the full Architecture — to keep context lean. Full `ARCHITECTURE.md`
is pulled for deep work or design changes. `PRD.md` governs scope: no
feature gets added that isn't in it (or added to it first).

**Drift guard:** `ARCHITECTURE-ESSENTIALS.md` is regenerated whenever
`ARCHITECTURE.md` changes — derived files are regenerated, never
hand-edited, the same rule that keeps CAPABILITIES.md honest.

These documents live in the project folder (under
`02-skills-projects/projects/`, git-ignored by default), not in `.echo`
— they belong to the project, not to ECHO.

## Shared context file

ECHO writes relevant vault notes to `subagents/shared/context.md` before
delegating. All agents can read it for background beyond the raw task.

```text
subagents/shared/context.md   ← ECHO writes, all agents read
```

- ECHO updates it when a task needs vault context (relevant notes, prior
  findings, constraints)
- Agents read it at task start; it supplements — never replaces — the task
  description
- ECHO refreshes it per task; stale context is replaced, not accumulated

## Subtask breakdown

For complex tasks, agents create `subtasks.md` in their folder — a
checklist of steps they'll complete:

```markdown
# Task: Build SAP workflow tracker

- [ ] Research SAP workflow API
- [ ] Design data model
- [ ] Implement core module
- [ ] Implement approval flow
- [ ] Write tests
- [ ] Write setup docs
```

- Chad can see the plan and redirect mid-task if needed
- Agents check items off as they go
- The file is deleted when the task completes

## Task dependencies

When an agent's task depends on another task finishing first:

1. Agent updates log status to `Waiting: [what it's waiting for]`
2. ECHO tracks the dependency chain
3. When the blocking task completes, ECHO notifies the waiting agent

**Example:** Charlie is `Waiting: Walter's API research` — ECHO tells
Charlie when Walter's research is Done.

## Stuck protocol

If an agent has attempted a task 3 times without progress:

1. Agent updates log status to `Stuck: [what was tried]`
2. Agent writes what they tried and why it failed
3. ECHO escalates to Chad: "Sherlock is stuck after 3 attempts: [details]"
4. Chad decides: provide guidance, reassign, or cancel

**Stuck ≠ Blocked:** Blocked means missing info or access. Stuck means
the agent tried multiple approaches and none worked.

## Daily digest

On request ("daily digest," "what did the agents do today?"), ECHO compiles:

```markdown
## Agent Digest — 2026-08-31

**Walter:** Completed "Research SAP workflows" (92% confidence)
**Sherlock:** Investigating "why builds stall" — 50% checkpoint reached
**Charlie:** Completed bugfix #2, started new build
```

One compact summary covering all agents' activity for the day.

## Cross-task memory

Before starting a new task, agents scan their own log.md for related past
tasks. If a related task exists:

1. Agent notes it: "Building on my earlier research from 2026-08-30"
2. Agent skips redundant work and extends the previous findings
3. Output references the prior work

This prevents redoing the same work and lets each agent's knowledge compound
over time. The log is not just a record — it's a working memory.

## "Ask Chad" flag

When an agent makes a judgment call that Chad might want to override, they
add a non-blocking flag in their output:

```markdown
**Needs Chad's decision:**
- [item] — [what I chose and why, what the alternative was]
```

**Ask Chad ≠ questions.md:** questions.md blocks work until answered.
The "Ask Chad" flag doesn't block — the agent delivers their best work
with the decision flagged for review.

ECHO surfaces these prominently when reporting results to Chad.

## Graceful degradation

When full completion isn't possible, agents deliver partial results:

1. Agent updates log status to `Partial: [XX%] — [what's missing and why]`
2. Output includes what was delivered AND what couldn't be
3. Chad decides: accept, request more, or cancel

**Partial ≠ Done:** Partial means genuinely useful work was delivered,
but gaps remain. Chad sees the confidence score and decides.

**Example:** Walter can't access a paywalled source — delivers findings
from 4 of 5 sources at 85% confidence, notes the gap.

## Recurring tasks

Standing tasks that repeat on a schedule. Each agent maintains a
`recurring.md` in their folder:

```markdown
| Task | Schedule | Last run | Status | Notes |
|------|----------|----------|--------|-------|
| Weekly AI news digest | Every Monday | 2026-08-31 | active | Focus on agent frameworks |
```

- **Status column** — `active` or `paused`. "Pause the weekly digest"
  sets `paused`; paused tasks are skipped by the due-check but never
  deleted. "Resume" sets `active` and recomputes next due from now.
- ECHO checks recurring.md at session start or on request
  ("run recurring tasks")
- When a task is due, ECHO delegates it like any other task
- Agent updates "Last run" after completing
- Chad adds/removes recurring tasks by telling ECHO
- **Next-due surfacing** — the morning briefing and "run recurring
  tasks" report upcoming due dates ("weekly digest due tomorrow"),
  computed from Schedule + Last run.
- **Run history** — each agent maintains `recurring-history.md`:
  append-only table (Date / Task / Outcome / Notes), last ~20 runs kept.
  "Has the digest been running?" is answered from this file, not memory.

## Lessons learned

After each task, agents note one lesson — what worked, what to do
differently next time:

```markdown
**Lesson learned:** [one sentence]
```

Lessons compound with cross-task memory: agents scan past lessons
alongside past tasks when starting new work. Over time, each agent
gets better at their specialty.

## WIP snapshot (session recovery)

Long tasks can outlast a session. While working, agents maintain a
`wip.md` in their folder:

```markdown
# WIP: Build SAP workflow tracker
**Done:** Data model, core module
**In progress:** Approval flow — half implemented
**Next:** Finish approval flow, then tests
**Where I left off:** [specific file/state details]
```

- On session start, agent checks for wip.md FIRST — resume before
  accepting new work
- Updated at each checkpoint (25/50/75%)
- Deleted at the moment the task is marked Done — not later. Order
  matters: outcome captured in log.md and reusable insights moved to
  patterns.md FIRST, then the file is deleted in the same step
- Self-healing: if an agent finds a wip.md whose log.md shows the task
  already Done, the wip.md is stale — delete it immediately on boot
  before accepting new work

## Task archive

When log.md exceeds ~20 completed rows, agents move older Done/Cancelled
rows to `log-archive.md`.

- Active log keeps only recent + in-progress work — stays scannable
- Cross-task memory scans both files (past tasks and lessons live in both)
- Archive is append-only; never deleted

## Vault write-back

Agent findings can be captured into Second Self's vault — but agents never
write to the vault directly. ECHO brokers it:

1. Agent identifies a finding worth keeping (research, investigation result,
   reusable lesson)
2. Agent appends a proposal to `subagents/shared/vault-proposals.md`:

```markdown
## Proposal — 2026-09-01 (Walter)
**Type:** research finding
**Title:** SAP workflow patterns comparison
**Content:** [the finding, formatted for the vault]
**Why keep it:** [one line]
```

3. ECHO reviews proposals on status checks; presents them to Chad
4. On Chad's approval, ECHO routes the proposal through the existing
   capture/intake flow (never direct writes)
5. Approved proposals are removed from the file; rejected ones are marked
   and kept for reference

**Agents propose. ECHO brokers. Chad approves.** Same staging-gate pattern
as ECHO's own memory.

## Collaboration requests

When an agent needs a small assist from another agent — without giving up
the task (that's a handoff):

1. Agent writes `collab-request.md` in the target agent's folder:

```markdown
# Collaboration request from Walter
**What I need:** Verify the API rate limits I found are current
**Why:** My research conclusion depends on it
**Scope:** Small assist — check one source, not a full investigation
**My task:** [what Walter is working on]
```

2. ECHO detects the request, creates a mini-task for the target agent
3. Target agent completes the assist, writes results back
4. ECHO routes the result to the requesting agent
5. The requesting agent stays primary owner of the original task

**Collab ≠ Handoff:** Handoff transfers the whole task. Collab is a
scoped assist — the requester keeps ownership.

## Runtime contract

Each agent may maintain a `RUNTIME.md` in its folder — a contract declaring
what the runtime must provide for the agent to function:

- **Required capabilities** — file read/write, shell execution, git access
- **Required context files** — which files the agent reads at boot
- **Boot prompt (dynamic)** — generated by ECHO at delegation time, points
  the agent at their log where the task already waits
- **Built-in verification** — the boot sequence's step 0 capability self-check
  replaces the operator checklist; if tools are missing, the agent reports
  `Blocked: missing tool X`
- **Runtime mapping** — how to spawn the agent per runtime (Hermes, Claude, Codex)

The flow: ECHO writes the task to the agent's log first → spawns a session
with a dynamically-generated boot prompt that points at the log → agent runs
the boot sequence (including capability self-check) → if wired correctly,
reports status and starts work; if not, reports `Blocked` and ECHO escalates.

The dependency moves from invisible assumption to declared contract with
self-verifying boot.

## Boot sequence

Every agent runs a deterministic startup ritual at session start — same
order every time, no drift:

0. Verify tool access (per RUNTIME.md) — if missing, report `Blocked: missing tool X`
1. Read own SKILL.md (who I am, how I work)
2. Check wip.md — resume if present
3. Read own log.md status line — what state am I in?
4. Scan log.md + log-archive.md — what do I already know?
5. Check recurring.md — anything due takes priority
6. Read shared/context.md — current mission context from ECHO
7. Read patterns.md (if maintained) — accumulated patterns and anti-patterns
8. Only then: accept work

ECHO knows agents orient via boot sequence before accepting work — a
`Pending` task isn't started until the agent has oriented.

## Patterns library

Agents that benefit from accumulated experience maintain a `patterns.md`
in their folder:

- **Patterns that worked** — added after each successful task
- **Anti-patterns to avoid** — added after each failure or lesson

The library starts empty and grows via the lessons-learned loop. It gives
cross-task memory something structured to accumulate into — agents don't
just remember *what* they did, they remember *how* to do it better.

## Adding a new sub-agent

1. Create the next numbered folder: `subagents/NN/`
2. Write `SKILL.md` — define the specialty, boundaries, process, output format
3. Write `log.md` — start with the table header, no rows
4. Optionally add `patterns.md` — empty patterns/anti-patterns scaffold
5. ECHO can now delegate to it

## Completion standard

A task is **done** when it reaches 90-100% completion. Perfection is not
required — "without fail" means delivered to a usable standard.