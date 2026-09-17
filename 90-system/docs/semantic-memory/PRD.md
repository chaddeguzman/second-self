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

## Done

All four implementation phases pass focused tests, privacy validation, the
full pytest suite, and the semantic evaluation suite. Normal recall remains
available when the optional model or index is unavailable.
