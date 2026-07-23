# Strategy Storage

`01-strategy-storage` is the private, personal layer of Second Self. It holds
the information used to understand who you are, recall what you have learned,
and keep actions aligned with your current direction.

The six folders below are the approved top-level structure. Their contents stay
local and are ignored by Git; only this guide and the empty folder scaffold are
committed.

## Folder Guide

### `00 Memory`

Stores durable personal context: identity, values, preferences, aspirations,
strengths, important experiences, and other information that helps Second Self
understand you consistently.

Use this folder for relatively stable context that should guide recall,
decisions, and agent behavior across many sessions. Update it deliberately when
your understanding of yourself changes.

### `01 Notes`

Stores general-purpose notes, ideas, observations, lessons, and working
knowledge that do not belong to a dated journal entry or a formal reference.

Use this folder to develop thoughts over time. Notes may later inform memory,
strategy, projects, or reviews, but they do not automatically become confirmed
personal context.

### `02 Journal`

Stores dated accounts of events, experiences, reflections, and personal
progress.

Use this folder for time-based records. Journal entries preserve historical
context and help reviews identify recurring patterns, changes, and lessons
without rewriting the past.

### `03 Strategy`

Stores purpose, principles, goals, priorities, commitments, plans, and other
documents that describe your current direction.

Use this folder to connect long-term intent with present choices. Strategy
documents should be reviewed when circumstances or priorities change rather
than treated as permanently fixed.

### `04 References`

Stores source material you may want to retrieve or cite, such as articles,
quotes, book notes, research, guides, and supporting documents.

Use this folder for information that primarily comes from external sources.
Keep enough source context to distinguish reference material from your own
confirmed beliefs, decisions, or memories.

Organize reference material into these subfolders:

- `00 books` — Book notes, summaries, excerpts, reading highlights, and related
  source information.
- `01 quotes` — Quotations with enough attribution and context to identify
  their original source.
- `02 research` — Research notes, studies, findings, evidence, and analytical
  source material.
- `03 guides` — Instructions, playbooks, tutorials, checklists, and other
  practical how-to material.
- `04 docs` — General supporting documents that do not fit one of the more
  specific reference categories.

### `05 Reviews`

Stores periodic review records, including weekly and quarterly reflections,
decisions, follow-ups, and approved updates produced by the review process.

Use this folder to assess captures, projects, priorities, conflicts, lessons,
and changes in direction. Reviews provide an audit trail of what was considered
and what was intentionally updated.

## How the Folders Work Together

A typical flow is:

1. Record raw thoughts and observations in notes or the journal.
2. Keep supporting external material in references.
3. Revisit this information during weekly or quarterly reviews.
4. Apply confirmed insights to memory or strategy when appropriate.
5. Preserve the review record so later sessions can understand why a change
   was made.

Markdown remains the source of truth. Second Self should retrieve only the
material relevant to the current task, preserve historical evidence, and
surface conflicts instead of silently choosing between contradictory records.

## Using Layer 1 as Context

`00 Memory` is the starting point for durable personal context, but it is not
the only context available to the user, Codex, Claude, or another trusted
agent. All six Layer 1 folders may contribute to recall and reasoning:

- `00 Memory` provides stable personal context and confirmed understanding.
- `01 Notes` contributes developed thoughts, observations, and working ideas.
- `02 Journal` contributes dated experiences, events, and reflections.
- `03 Strategy` contributes current direction, priorities, goals, and
  commitments.
- `04 References` contributes supporting sources, research, guides, and
  documents.
- `05 Reviews` contributes periodic assessments, decisions, follow-ups, and
  explanations for previous changes.

For a simple question, one relevant memory note may be enough. For deeper
recall, investigations, project work, or idea development, use a larger
task-relevant context set assembled from several folders. The goal is to use
the available context window well without loading unrelated private material
or the entire vault by default.

## Privacy and Structure

- Personal contents inside these folders must not be committed to Git.
- Do not place secrets, credentials, or private exports in tracked files.
- Do not add another top-level folder here without the protected approval
  workflow.
- Deletions should go through the recoverable private-trash process.
- Project execution details belong in the project layer, while reusable
  personal lessons may return here through review or writeback.
