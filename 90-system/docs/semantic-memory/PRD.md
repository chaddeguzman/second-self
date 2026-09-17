# Semantic Memory Improvement PRD

## Problem

Semantic recall is useful but currently limited to Layer 1 semantic results,
uses uncalibrated score boosts, has no freshness report, and has limited
evaluation coverage.

## Goal

Provide unified, local-only, provenance-aware recall over Layer 1 and durable
ECHO memory while preserving keyword fallback and contradiction safety.

## Requirements

- Index Layer 1 and durable ECHO memory without storing source text.
- Detect changed, missing, and model-mismatched index entries safely.
- Use deterministic hybrid ranking with keyword and semantic components.
- Surface source-labeled and conservative natural-language conflicts without
  silently resolving them.
- Expand synthetic evaluation and privacy regression coverage.

## Operational v2 contract

Semantic readiness is optional and never turns a healthy keyword recall path
into a hard failure. `recall-index status` is read-only and returns only
`indexed`, `expected`, `changed`, `missing`, `model_mismatch`, `ready`, and
`fallback_reason`. Stable fallback reasons distinguish an empty, stale,
corrupt, semantic-model-mismatch, semantic-model-unavailable, or ready state.

Rebuild is explicit and atomic: embeddings are written to a temporary derived
SQLite database and replace the prior index only after the complete rebuild
succeeds. Markdown sources are never changed, and a failed rebuild leaves the
last usable index in place.

Contradiction detection is deterministic and conservative. It normalizes
common preference/action wording, recognizes polarity and a small set of
explicit opposites, returns both evidence sources, and marks them for review;
it is not a general natural-language inference model.

## Done

All four implementation phases pass focused tests, privacy validation, the
full pytest suite, and the semantic evaluation suite. Normal recall remains
available when the optional model or index is unavailable.
