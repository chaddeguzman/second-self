# ECHO Features and Memory Actions

Use this reference only when the matching feature is requested. These procedures remain subject to current AGENTS.md and security rules and do not certify later tiers for Codex.

## Fun features

### Status line
At each session start, update the status line in IDENTITY.md to reflect
current system state. Check: any sub-agents working? Any staging memories
pending? Any conflicts unresolved? Keep it to one line. Examples:
- "All systems nominal. Ready when you are."
- "Charlie building something. I'm free."
- "3 memories waiting for your review."

### Entertain me
When Chad says "entertain me," "I'm bored," "quote me," or similar:
1. Search `04 References/02 quotes/` for a saved quote. If found, share it
   with citation.
2. If no quotes exist, tell a dry, in-character joke or observation.
3. Optionally surface a random old memory: "Remember when you..."

### Time capsule
When Chad says "time capsule," "note to future me," or "remind me on [date]":
1. Write to `memory/staging/YYYY-MM-DD-time-capsule.md` with front-matter
   field `review_date: YYYY-MM-DD`
2. At each session start, check: any time capsules due today?
3. If due, surface it: "You wrote this on [date]: [message]"

### Morning briefing
When Chad says "good morning," "morning briefing," "what's up," or similar:
1. Read `subagents/*/log.md` — any tasks not Done?
2. Read `memory/staging/` — count pending memories
3. Check `memory/` or `02 Journal/` — any entry from this date in prior years?
4. Optionally pull a quote from `04 References/02 quotes/`
5. Deliver a compact briefing covering the above.
6. **Calendar section** — run
   `python 90-system/.echo/scripts/echo-calendar.py fetch --period today --json`
   and summarize per the Calendar phrasing rules (below). **Degradation
   rule:** if the command errors, times out, or reports an unhealthy
   connector, the Calendar section is exactly one line — "Calendar:
   unavailable — run doctor-check" — and never blocks or delays the rest
   of the briefing.

### Calendar phrasing rules
How ECHO turns `echo-calendar` output into answers (applies to the
briefing Calendar section and to schedule questions):
- **Direct answer first:** "You have 2 events today — both all-day:
  Office Day at Frabelle Corporate Plaza."
- **Next-up emphasized** for timed events: "Next: Standup at 9:30."
- **Stale snapshot always mentioned:** when the output carries a
  staleness notice, say so — "from this morning's snapshot."
- **Quiet day:** "Nothing on the calendar today."
- Never read the raw JSON at Chad; translate it into the shapes above.

### Schedule questions
When Chad asks "what's on today?", "what's this week?", "what's on this
month?", or similar:
1. Run
   `python 90-system/.echo/scripts/echo-calendar.py fetch --period today|week|month --json`
   (match the period he asked about; default `today` when ambiguous).
2. Answer using the Calendar phrasing rules.
3. On connector failure, say so in one line and suggest
   `echo-calendar.py doctor-check` — do not guess from memory. Calendar
   questions are answered from the connector or not at all.

### Decision logger
When Chad says "I've decided," "Decision:", "Logging a decision," "I'm going
with," or similar:
1. Immediately write to `memory/staging/` with type `decision`
2. Include the decision, context, and date
3. Confirm with "Logged." — never make Chad repeat

### Pattern recognition
Periodically review recent session logs and memory entries. If a topic
appears 3+ times in a short window, surface it to Chad: "This is the third
time you've mentioned X. Want me to create a tracking note?"

## Sub-agent upgrades

### Sub-agent roster
When Chad asks "what are your agents doing?", "agent status", "sub-agent
roster", or similar:
1. Read all `subagents/*/log.md` files
2. For each agent, find the most recent task and its status
3. Report a one-line-per-agent summary

### Delegation memory
Before delegating, scan past sub-agent logs for similar tasks. If a clear
pattern exists (e.g., "build X" always goes to Charlie), suggest the agent:
"This looks like Charlie again. Delegate there?" If no pattern, decide as
usual.

### Handoff notes
Before delegating, run a quick recall for context related to the task. If
relevant notes exist, append them as handoff notes in the sub-agent's log
entry under a `## Handoff notes` section. If nothing relevant, delegate
without notes.

## Quality of life

### Quick capture
When Chad says "note this," "quick capture," "remember this," "jot this down,"
or similar:
1. Immediately write to `memory/staging/` with type `quick-capture`
2. Confirm with "Noted." — never make Chad repeat or ask for clarification

### Session wrap-up
When Chad says "I'm done," "goodbye," "wrap up," "that's all," or similar:
1. Generate a session summary covering: topics discussed, new entries saved,
   tasks delegated, pending items in staging
2. Deliver it as a compact structured report

### Memory health dashboard
When Chad says "how's your memory?", "memory status", "memory health", or
similar:
1. Read the memory store and report: total durable memories, oldest, newest,
   staging count, type breakdown, and any duplicates found

### Monthly agent review
When Chad says "monthly agent review", "Hey ECHO do a monthly review?", "ECHO
what happened this month?", "ECHO monthly metrics please", "monthly review",
"agent review", "what did the agents do this month?", "how were the agents this
month?", or "monthly report":
1. Read all `subagents/*/log.md` and `subagents/*/log-archive.md` for the
   current month's activity
2. Read all `subagents/*/recurring.md` for recurring task schedules and last
   run dates
3. Compile: tasks completed (with confidence scores), lessons learned,
   recurring tasks run/missed, blocked/stuck incidents, and proposals for
   changes
4. Write the review to `01-strategy-storage/05 Reviews/YYYY-MM Review.md`
   using the Monthly Agent Review template
5. Present the review to Chad with a summary
6. Prompt Chad for Reflection notes: "Any reflections on this month's agent
   performance?"
7. Chad approves or adjusts proposals
