# ECHO — Recall (Tier 6, Keyword-First)

> Recall turns ECHO's stored memories back into answers. It must **degrade,
> never break**: if a smarter ranking method is unavailable, keyword matching
> still works. ECHO is never blinded just because a service hiccuped.

## The interface (stable — implementations change behind it)

```text
recall(query) -> [ranked memory files]
```

Given a query, return the memory files from `90-system/.echo/memory/`
(Tier 5 store) ranked most-relevant-first. Callers depend only on this
interface — the ranking implementation behind it can change without touching
anything else.

## Two recall paths — don't confuse them

1. **Vault recall** — `second-self-recall`: search across Second Self's
   curated tree (`04 References`, `00 Memory`, Journal, etc.). Governed by
   AGENTS.md and SKILL.md's interaction pattern.
2. **Memory-store recall** — *this file*: ranked retrieval over ECHO's own
   long-term memory entries in `90-system/.echo/memory/`. Used when the
   question is about what ECHO has been taught or has inferred, per the
   entry types (`fact-about-user`, `how-to-work`, `active-project`,
   `external-pointer`).

## Keyword ranking (active now)

Rank matching memories by, in order:

1. **Hook match** (highest weight) — the query's terms against the memory's
   H1 hook.
2. **Body match** — terms against the body text.
3. **Type match** — a query clearly about "how I work" boosts
   `how-to-work` entries; about a person or fact boosts `fact-about-user`;
   about current work boosts `active-project`.
4. **Recency** — among near-equal scores, newer `updated` dates rank first.

Return the top matches with their file paths so every answer can cite its
memory file. If nothing clears the bar, say so — `[not found]` with a
`Searched:` line, per SKILL.md. Never invent a memory that isn't there.

## Derived, rebuildable index

Any search index built for recall is **generated from the memory files** and
can be rebuilt from scratch at any time. The files are always the source of
truth; the index is never the only copy. If the index and the files
disagree, the files win — rebuild the index.

## Semantic path (optional, interface unchanged)

When the optional embedded model is installed, semantic recall embeds the
query and each Layer 1 or durable ECHO memory entry, ranks by normalized
cosine similarity, and merges with keyword scores. A paraphrased question
("something about why I stall on identity-tied tasks") can then find the right
memory even when it shares no keywords with the hook. The derived SQLite index
lives in the ignored private cache and is always rebuildable from the Markdown
sources. `recall-index status` reports aggregate freshness state using content
hashes and model version without exposing source text or private details.
Normal recall uses keyword fallback when the index is stale, missing, corrupt,
or the model is unavailable.
Until the model and index are ready — and automatically whenever the model is
missing or down — keyword ranking remains the path. Recall never fails because
semantic dependencies are unavailable.

## Provenance discipline

Ranked results carry their `source` (`echo-inferred` vs `chad-authored`).
When answering, ECHO labels findings accordingly — an `echo-inferred` memory
is a reasonable connection, not a confirmed fact. Conflicts between memories
go to Chad (`second-self-conflict-review`), never silently resolved. Retrieved
results from conflict sources carry a review flag; the ranking layer does not
choose a winner. Returned preference/action claims with opposing objects or
polarity are also conservatively flagged for review; this is not a general
natural-language reasoning system and uncertain claims remain unmerged.
