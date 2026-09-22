# ECHO Commands

> A human-friendly guide to asking ECHO to use Second Self.

ECHO is the conversational front door. Ask for the outcome in plain language;
ECHO chooses the appropriate workflow and can run the underlying command when
the current client has local workspace access.

This file is the user-facing command index. Technical setup details belong in
the setup guides. Add new user-facing requests here when a new command or
workflow becomes available.

## How to ask ECHO

Use this pattern:

```text
ECHO, <what I want> [<scope or time range>].
```

Examples:

```text
ECHO, recall what I have written about avoiding important work.
ECHO, check whether semantic memory is ready.
ECHO, rebuild the semantic index if it is stale.
ECHO, save this as an idea: <idea>.
```

If ECHO cannot execute a command in the current client, ECHO should provide
the exact direct command instead of pretending it ran.

## Recall and memory

| What I want | Ask ECHO | Underlying command |
|---|---|---|
| Find an exact word or phrase | “ECHO, search for `identity`.” | `.\90-system\automation\scripts\second-self.ps1 search "identity"` |
| Recall related ideas | “ECHO, recall what I have written about avoiding important work.” | `.\90-system\automation\scripts\second-self.ps1 recall "avoiding important work"` |
| Explain a recall result | “ECHO, explain how you found that.” | `python -m second_self recall "<query>" --explain` |
| Check the semantic index | “ECHO, check semantic memory status.” | `.\90-system\automation\scripts\second-self.ps1 recall-index status` |
| Rebuild semantic memory | “ECHO, rebuild the semantic index.” | `.\90-system\automation\scripts\second-self.ps1 recall-index rebuild` |
| Rebuild only if needed | “ECHO, check the index and rebuild it if stale.” | status, then rebuild only when required |
| Explain conflicting memories | “ECHO, review the conflicting claims about mornings and nights.” | `.\90-system\automation\scripts\second-self.ps1 recall ...` plus conflict review |

Semantic rebuilding is explicit. It may load or download the local embedding
model and change derived cache state. It never changes the authoritative
Markdown memories. If semantic memory is unavailable, keyword recall remains
available.

## Capture and journaling

| What I want | Ask ECHO | Underlying command |
|---|---|---|
| Capture an idea | “ECHO, save this as an idea: `<text>`.” | `.\90-system\automation\scripts\second-self.ps1 capture --title "Idea" --body "<text>"` |
| Record a journal entry | “ECHO, add this to today’s journal: `<text>`.” | `.\90-system\automation\scripts\second-self.ps1 journal --body "<text>"` |
| Capture a titled note | “ECHO, capture `<title>` with this content: `<text>`.” | `.\90-system\automation\scripts\second-self.ps1 capture --title "<title>" --body "<text>"` |
| Import a source document | “ECHO, ingest this document: `<path>`.” | `.\90-system\automation\scripts\second-self.ps1 ingest "<path>"` |

ECHO should preserve the difference between a temporary thought, a journal
entry, and a reviewed source. It should not silently promote a capture into
confirmed personal memory.

## Planning and review

| What I want | Ask ECHO | Underlying command or workflow |
|---|---|---|
| Show due items | “ECHO, what is due?” | `.\90-system\automation\scripts\second-self.ps1 due` |
| Show overdue items | “ECHO, show only overdue items.” | `.\90-system\automation\scripts\second-self.ps1 due --overdue-only` |
| Show recent activity | “ECHO, show what changed in the last 14 days.” | `.\90-system\automation\scripts\second-self.ps1 recent --days 14` |
| Run a weekly review | “ECHO, start my weekly review.” | `second-self-weekly-review` workflow |
| Review conflicting claims | “ECHO, prepare a decision about these conflicting notes.” | `second-self-conflict-review` workflow |
| Delegate a large build | “ECHO, delegate this build to Charlie.” | Charlie delegation workflow |
| Check delegated-agent progress | “ECHO, what are your agents doing?” | `python -m second_self agents status` |

## Wiki and source maintenance

| What I want | Ask ECHO | Underlying command |
|---|---|---|
| Check the wiki | “ECHO, show wiki status.” | `.\90-system\automation\scripts\second-self.ps1 wiki status` |
| Check wiki structure | “ECHO, lint the wiki.” | `.\90-system\automation\scripts\second-self.ps1 wiki lint` |
| Process pending Raw files | “ECHO, process the new Raw files.” / “ECHO, check the Raw folder and process it.” / “ECHO, process-raw.” | `process-raw` → `second-self-wiki` workflow |
| Add a source for review | “ECHO, add this source to the wiki: `<path>`.” | `.\90-system\automation\scripts\second-self.ps1 wiki add "<path>"` |
| Initialize wiki support | “ECHO, initialize the wiki.” | `.\90-system\automation\scripts\second-self.ps1 wiki init` |
| Find legacy files | “ECHO, inspect unstructured files.” | `.\90-system\automation\scripts\second-self.ps1 legacy` |

Wiki processing and moves remain explicit. ECHO should ask for the required
review or approval instead of silently moving or rewriting private sources.

For Raw processing, the natural-language requests above should route to the
deterministic `process-raw` trigger. The workflow checks `01 Capture/00 Raw`,
creates linked wiki source and topic pages, recommends `04 References`
destinations, and waits for one `Yes` before applying the reviewed
`wiki_process` transaction. It processes at most ten Markdown or text files per
run.

## Health and safety

| What I want | Ask ECHO | Underlying command |
|---|---|---|
| Check overall readiness | “ECHO, run a health check.” | `.\90-system\automation\scripts\second-self.ps1 doctor --json` |
| Run a strict health check | “ECHO, tell me whether every health check is clean.” | `.\90-system\automation\scripts\second-self.ps1 doctor --strict --json` |
| Run privacy validation | “ECHO, validate repository privacy.” | `.\90-system\automation\scripts\second-self.ps1 validate --privacy --tracked-only` |
| Run tests | “ECHO, run the full test suite.” | `python -m pytest` |
| Check evaluation suites | “ECHO, run the semantic evaluation.” | `python -m second_self eval semantic --json` |
| View scheduler state | “ECHO, show scheduler status.” | `.\90-system\automation\scripts\second-self.ps1 schedule status --json` |
| Run due test-only jobs | “ECHO, run the due scheduled checks.” | `.\90-system\automation\scripts\second-self.ps1 schedule run-due --json` |

Health checks are read-only. A warning usually means an optional capability is
degraded; it does not automatically mean that ordinary keyword recall has
failed.

`python -m second_self capabilities --json` reports the redacted capability
registry. States are `available`, `degraded`, `disabled`, or `planned`.
Gmail and Drive are intentionally `disabled` placeholders until their
read-only, on-demand contracts are implemented and explicitly enabled.
DOC-002 now defines the future contract boundary, but does not enable either
connector: requests must be bounded and explicit, results are transient and
source-attributed, and any save must go through broker-reviewed Raw capture.

For an onboarding view with state meanings, data boundaries, prerequisites,
approval requirements, examples, fallbacks, and safe next steps, run:

```powershell
python -m second_self capabilities --guide
python -m second_self capabilities --guide --json
```

The guide is informational. It does not enable disabled capabilities or grant
external-action authority.

## Calendar

| What I want | Ask ECHO | Underlying command |
|---|---|---|
| Show today’s calendar | “ECHO, what is on my calendar today?” | `python 90-system/.echo/scripts/echo-calendar.py fetch --period today` |
| Show this week’s calendar | “ECHO, what is on my calendar this week?” | `python 90-system/.echo/scripts/echo-calendar.py fetch --period week` |
| Show this month’s calendar | “ECHO, what is on my calendar this month?” | `python 90-system/.echo/scripts/echo-calendar.py fetch --period month` |
| Diagnose calendar access | “ECHO, check calendar connectivity.” | `python 90-system/.echo/scripts/echo-calendar.py doctor-check` |
| Refresh calendar cache | “ECHO, refresh the calendar cache.” | `python 90-system/.echo/scripts/echo-calendar.py cache --refresh` |

Calendar retrieval is read-only. Cached results must be labeled when they are
stale.

## Backup and restore

| What I want | Ask ECHO | Underlying command or workflow |
|---|---|---|
| Create a backup | “ECHO, create a Second Self backup.” | `.\90-system\automation\scripts\backup.ps1 -Destination "<path>"` |
| Restore a backup | “ECHO, help me restore this backup.” | `.\90-system\automation\scripts\restore.ps1 -Archive "<archive>" -Destination "<path>"` |
| Verify a backup plan | “ECHO, check my backup setup.” | backup skill and diagnostics |

Backup and restore operations require careful path and approval handling. ECHO
should show the intended source and destination before a consequential change.

## Git and delivery

| What I want | Ask ECHO | Underlying workflow |
|---|---|---|
| Review current changes | “ECHO, review the repository changes.” | Git status and complete diff review |
| Validate before delivery | “ECHO, run the required delivery checks.” | privacy validation, tests, and relevant lint |
| Commit and merge completed work | “ECHO, finalize and merge this completed Second Self change.” | `second-self-commit` workflow |

**Golden rule — propose, then confirm.** Whenever ECHO finishes work that
changed tracked files, ECHO proactively proposes the `second-self-commit`
workflow (what changed, the proposed commit subject, validation status) and
waits for Chad's explicit Yes before staging, committing, or merging. ECHO
never commits or merges silently; the workflow only runs when Chad confirms.

ECHO must never stage private Second Self content, bypass privacy validation,
push directly to protected `main`, or silently choose a merge strategy.

## Future commands

When a new Second Self capability is added, document it here using this shape:

| What I want | Ask ECHO | Underlying command or workflow | Notes |
|---|---|---|---|
| `<plain-language outcome>` | “ECHO, `<natural request>`.” | `<command or skill>` | `<approval, privacy, or fallback rule>` |

Keep this guide focused on outcomes Chad can ask for. Put implementation
details, flags, architecture, and installation instructions in the technical
documentation linked from `README.md`.
