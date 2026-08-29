# ECHO — Personality Checkpoint (Tier 9)

> The seatbelt you bolt on after the car is built. Over a long session —
> especially voice, where tone slips faster than it does on a page — ECHO's
> draft replies are checked against who it is before they're sent. The check
> is silent: Chad never sees "running drift check," he just never notices the
> voice flattening out.

## Thresholds (Chad, 2026-08-29)

| Mode | Turns before checkpoint fires |
| --- | --- |
| **Text** | 10 turns |
| **Voice** | 6 turns (drifts faster) |

These are the trigger points, not hard caps — the checkpoint fires *after*
the Nth turn and periodically thereafter, and resets when a new session
starts or a session is recovered.

## Tracking

The turn count is maintained in the working-memory session log
(`memory/sessions/*.md`, Tier 4) — each appended turn increments a counter
visible in the session-state header. The counter is runtime-owned state, not
durable; it does not get promoted to long-term memory. In the file-convention
layer the agent updates the counter as part of appending each turn; the
Phase 3 standalone runtime can track it natively.

## Injection into the dynamic block

When the counter reaches the threshold, the checkpoint is injected into the
dynamic block *before* the next response is generated — as a silent
instruction, not visible output. It tells ECHO to run the self-audit on its
draft before sending.

## The self-audit

Before sending, ECHO checks its draft against `IDENTITY.md` on exactly two
axes:

1. **Length** — is it still the right length for what was asked? (No
   padding a two-line finding into a five-paragraph report; no hedging
   filler.)
2. **Voice** — does it still sound like ECHO, not a generic hedging
   assistant? (Dry sarcasm aimed at plans, never at Chad; confirmed /
   inferred / missing stated plainly.)

If the draft passes both checks, it sends unchanged. If it fails either,
ECHO tightens it *before* answering — silently. It never sends a draft and
apologizes after.

## Reset

The counter resets to zero when:
- A new session starts (new session file created).
- A session is recovered from `current-session.md` (resume, not new).

## Why this is last

Small ≠ early. Tier 9 is small in *code* but late in *dependency*: it needs
Tier 2 (the dynamic block to inject into), Tier 4 (the session log to count
turns in), and the persona defined in Tier 1 (to check drafts against).
Building it earlier would mean rebuilding it once the real infrastructure
landed.