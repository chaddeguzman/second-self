---
name: second-self-recall
description: Retrieve personal facts, preferences, decisions, commitments, lessons, or history from Second Self. Use when an answer should rely on stored personal context or when the user asks what was previously recorded.
---
# Second Self Recall

Version: `1.0.0`

1. Read compact current-view indexes first.
2. Search titles, metadata, and content for the specific topic.
3. Treat every matching source as evidence; do not discard conflicts.
4. Cite paths and dates for consequential claims.
5. If evidence is missing or contradictory, state what was searched and ask.
6. Do not load unrelated journals or history.

## Ranked Recall Command

Use the `recall` CLI subcommand for ranked results across Layer 1:

```sh
python -m second_self recall "<topic>" [--max-results N] [--min-score N]
```

Results are scored by folder priority (00 Memory highest), recency, tag
strength (frontmatter tags and body `#tag` mentions), and title match. Higher
scores rank first. Use `--min-score` to filter weak matches and `--max-results`
to cap the result count.

