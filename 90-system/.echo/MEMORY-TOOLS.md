# ECHO — Memory Tools (Tier 7: Save, Recall, Forget)

> ECHO can write memories — but only through the **staging gate**. Nothing
> lands in durable memory un-reviewed. The gate and the "never secrets" rule
> are boundaries, not suggestions: in the file-convention phase they are
> enforced by this spec being part of the loaded operating rules; the Phase 3
> standalone runtime enforces them in the write-permission layer itself.

## The tools

### save — write a new memory to staging

```text
save(type, hook, body) -> staging file
```

- Writes `memory/staging/YYYY-MM-DD-<slug>.md` in the exact Tier 5 entry
  format (front-matter `type` / `source` / `created` / `updated`; H1 hook;
  body with fact + why + how to apply).
- `source` is `echo-inferred` when ECHO proposes it, `chad-authored` when
  Chad states it directly.
- Staging is **direct-write, reversible, inbox-style** — ECHO may write here
  freely; it is ECHO's own sandbox, never Layer 1 content.
- **Dedupe on the way in:** before saving, run recall (Tier 6) against the
  durable store; if an existing memory already covers it, update that
  proposal or skip — never store a near-duplicate.

### recall — query durable memory

Per `90-system/.echo/RECALL.md` (Tier 6). Recall reads the durable store;
staged (un-promoted) memories are not recalled as fact — they may be
surfaced as pending proposals, labeled as such.

### forget — delete a memory, confirmation required

```text
forget(memory file) -> deleted   (only after Chad explicitly confirms)
```

- Never delete on inference or implication. Chad says which memory goes;
  ECHO confirms the exact file before deleting.
- Forgetting removes the durable file and updates the index. Staging files
  are simply discarded on request — no ceremony.

## Save discipline

**ECHO saves:**
- things Chad teaches it,
- corrections Chad makes (a live correction wins and gets captured),
- decisions on projects,
- time capsules (notes to future Chad with a review_date),
- quick captures (fast, general-purpose notes with zero ceremony).

**ECHO does not save:**
- transient task state,
- the current conversation (that's working memory, Tier 4 — it ages out),
- anything already derivable from code or config,
- **never secrets or private data** — passwords, API keys, recovery codes,
  private keys, credentials of any kind. If a request to save one slips
  through, the save refuses and says why.

## The staging gate

```text
memory/staging/          ← ECHO writes here (inbox-style, reversible)
        │  promotion = review-shaped batch approval (e.g. weekly review)
        ▼
memory/                  ← durable store (Tier 5) — only via promotion
```

- New memories land in `memory/staging/` and are **promoted** to durable
  memory through a review-shaped step — a batch approval during the weekly
  review, not the full broker Y/N ceremony. This mirrors how Capture →
  Memory already works in Second Self.
- Promotion updates the durable index; discarding deletes the staging file.
- Staging content is pending, not fact: it is never cited as confirmed.

## The extractor (manual trigger for now)

On demand ("extract" or "/wrap"), ECHO reads the session transcript and:
1. proposes durable memories worth keeping,
2. checks each against the durable store to avoid duplicates,
3. skips sessions that look like testing or idle chatter,
4. writes proposals to staging — never directly to durable memory.

The automatic session-end trigger is deferred to the Phase 3 standalone
runtime (needs a real lifecycle hook); manual extraction is the portable
core.

## Privacy

Staging and durable memory both live under the git-ignored `memory/` folder
— nothing personal is ever committed. And per the rule above: secrets never
land in memory at all, staged or otherwise.