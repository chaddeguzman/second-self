# ECHO Delegation and Subagents

Use this reference only when delegation, agent status, recurring work, handoffs, collaboration, or agent reviews are required.

## Delegation logic

When a task comes in, assess its size and complexity:

1. **Small task → handle it yourself.** Quick lookups, simple questions,
   short recalls — do it directly and respond.
2. **Big/hard task → delegate.** Building apps, creating systems, deep
   research, complex investigations — these go to a sub-agent.

To delegate:
1. Identify the right sub-agent under `90-system/.echo/subagents/`
   (walter = research, sherlock = investigation, charlie = development/coding)
2. Write the task to that sub-agent's `log.md` (date, time, request,
   status `Pending`)
3. Tell Chad which agent is handling it
4. Stay free for other requests

### Finalization rule for delegated builds

Phase checkpoints are review-only. Agents may run tests and report progress,
but must not commit or merge at a phase boundary. When the complete task has
passed self-review and validation, the agent changes its log status to `Done`
before repository finalization. The final status update and all task changes
are staged together, producing one commit, one PR, and one merge for the
delegated task. A status-only closeout commit is not allowed. CI repairs update
the existing PR; they do not create a second PR.

For build tasks, reference the project document convention in
`90-system/.echo/subagents/README.md` in the task entry: builds above
the size gate get `PRD.md`, `ARCHITECTURE.md`,
`ARCHITECTURE-ESSENTIALS.md`, and a thin per-project `AGENTS.md`,
scaffolded before any feature code (templates live in
`90-system/.echo/subagents/shared/templates/`).

When a sub-agent reports `Done` on work that changed tracked files, propose
the `second-self-commit` workflow to Chad — what changed, the proposed
commit subject, validation status — and run it only after an explicit Yes
(see the Delivery rule in `90-system/.echo/IDENTITY.md`).

When Chad asks "is it done?" or wants a status check:
1. Read the assigned sub-agent's log.md
2. Report the current status or results back to Chad
3. If confidence is below 80%, flag it: "Charlie finished at 75% confidence — worth double-checking X"

If Chad overrides your agent choice ("no, use Charlie"), reassign:
update both logs accordingly.

### Delegation presets
Named bundles in `90-system/.echo/subagents/shared/presets.md`:
- `quick-build` — Charlie, size-gate docs skipped, single milestone
- `full-build` — Charlie, PRD → Architecture → Essentials scaffold,
  incremental milestones, 25/50/75% checkpoints
- `deep-dive` — Sherlock, handoff notes attached, 75% checkpoints,
  confidence ≥ 85% target
- `research` — Walter, multi-source, confidence tagged, gaps listed

Chad says the preset name → apply the bundle. Chad can override any part
("full-build but skip the PRD"). The preset is a starting bundle, not a
contract.

### Questions protocol
When a sub-agent needs more info:
1. Check for `questions.md` in each sub-agent's folder (status = `Needs Info`)
2. If found, ask Chad the specific questions
3. Write answers to `answers.md` in the agent's folder
4. Agent reads answers and continues

### Handoff detection
When one agent's work should continue with another:
1. Check for `handoff.md` in each sub-agent's folder
2. If found, read the handoff: what to do, why, context
3. Create a new task for the target agent with the handoff context
4. Delete the `handoff.md` after processing

### Progress checkpoints
For long tasks, read the sub-agent's log for 25/50/75% checkpoint entries.
When Chad asks "how's it going?" report the latest checkpoint.

### Blocker detection
On every status check, look for `Blocked:` in the sub-agent's log status.
If found, immediately tell Chad: "[Agent] is blocked: [reason]" and suggest
options (provide guidance, reassign, or cancel).

### Task acceptance tracking
When delegating, write the task with status `Pending`. When the agent updates
it to `In Progress`, you know they've accepted. If a task stays `Pending`
for too long, follow up or reassign. Agents run a boot sequence (orient via
SKILL.md, wip.md, logs, recurring, shared context, patterns) before accepting
work — a Pending task isn't started until the agent has oriented.

### Agent status lines
Each agent maintains a one-line status at the top of their log.md. Read these
for quick "what are your agents doing?" reports without scanning full logs.

### Task templates
When delegating, include a template reference based on task type:
- Research → `research` template (Question → Sources → Findings → Confidence → Gaps)
- Investigation → `investigation` template (Scope → Evidence → Reasoning → Conclusion → Open items)
- Development → `build` template (What → How to run → Tests → Limitations → Debt)
- Bug fix → `bugfix` template (Root cause → Fix → Tests → Regression check)

Document templates for build tasks (`PRD.template.md`,
`ARCHITECTURE.template.md`, `ARCHITECTURE-ESSENTIALS.template.md`,
`project-AGENTS.template.md`) live in
`90-system/.echo/subagents/shared/templates/` — point Charlie at them
when delegating anything above the size gate.

### Shared context
Before delegating a task that needs vault context, write relevant notes to
`subagents/shared/context.md`. Agents read it at task start. Refresh it per
task — stale context is replaced, not accumulated.

### Stuck escalation
On every status check, look for `Stuck:` in the sub-agent's log status.
If found, escalate to Chad: "[Agent] is stuck after 3 attempts: [details]".
Stuck ≠ Blocked — stuck means multiple approaches failed; blocked means
missing info or access.

### Dependency tracking
Watch for `Waiting:` statuses in agent logs. When the blocking task
completes, notify the waiting agent so work resumes.

### Daily digest
When Chad asks "daily digest" or "what did the agents do today?":
1. Read all `subagents/*/log.md` for today's activity
2. Compile a compact summary: completed tasks (with confidence), in-progress
   work with checkpoints, blocked/stuck items
3. Deliver as a one-glance report

### "Ask Chad" surfacing
When reporting agent results, look for `**Needs Chad's decision:**` sections.
Surface these prominently — before or right after the main result — so Chad
sees the judgment calls agents made and can override them if needed.

### Partial delivery reporting
On every status check, look for `Partial:` statuses. Report to Chad:
"[Agent] delivered partial results at [XX%] — [what's missing]". Chad
decides: accept, request more, or cancel.

### Recurring task check
At session start or when Chad asks "run recurring tasks":
1. Read each agent's `recurring.md`
2. For tasks due (schedule elapsed since Last run), delegate as normal
3. Report what was re-delegated
4. **Pause/resume** — "pause the weekly digest" sets that row's Status to
   `paused` (skipped by the due-check, never deleted); "resume" sets it
   back to `active` and recomputes next due from now
5. **Next-due surfacing** — report upcoming due dates in the morning
   briefing and on "run recurring tasks" ("weekly digest due tomorrow"),
   computed from Schedule + Last run
6. **Run history** — each agent appends to `recurring-history.md`
   (Date / Task / Outcome / Notes, last ~20 runs). "Has the digest been
   running?" is answered from this file, not memory

### Archive awareness
When reading agent logs for history or cross-task context, also check
`log-archive.md` — older tasks and lessons live there once the active
log is archived.

### Vault write-back brokering
On status checks, look for proposals in `subagents/shared/vault-proposals.md`.
Present each to Chad: "[Agent] proposes capturing [title] to the vault —
approve?" On approval, route through the existing capture/intake flow
(never direct vault writes). Remove approved proposals; mark rejected ones.

### Collaboration request routing
On status checks, look for `collab-request.md` in each agent's folder.
If found, create a mini-task for the target agent with the request's scope.
When the assist completes, route the result back to the requesting agent.
The requester keeps ownership of their original task.
