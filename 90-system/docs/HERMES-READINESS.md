# Hermes Readiness

Second Self is Hermes-first: the repository owns ECHO's canonical identity,
skills, memory boundaries, and delegation contracts. Hermes is the runtime that
loads those contracts and keeps ECHO as the primary agent.

## Repository-side check

Run from the repository root:

```powershell
python 90-system/.echo/runtime/certify_hermes.py --json
```

This verifies the canonical files, generated Hermes bundle mirrors, ECHO
context assembly, delegation boundaries, and Walter/Sherlock/Charlie role
contracts. It reads architecture and public contract files only; it does not
load private Second Self content or claim that Hermes itself ran. The generated
`hermes-ready/` directory is ignored by Git; when it is absent, the checker
defers bundle-mirror checks and tells the operator to regenerate it before the
runtime smoke test.

## Runtime certification smoke test

The static check must pass before using a Hermes session. In Hermes, perform
one disposable end-to-end test:

1. Start ECHO from the repository's `90-system/.echo/hermes-ready/` bundle.
2. Ask ECHO to retrieve one known synthetic or explicitly approved Second Self
   fact and require an evidence label plus source citation.
3. Ask ECHO to delegate a synthetic research task to Walter, Sherlock, or
   Charlie.
4. Confirm the specialist receives only the scoped task context, reads its
   role contract, and returns confidence plus limitations.
5. Confirm ECHO synthesizes the result and does not apply a protected write.
6. Confirm a proposed memory or project change remains pending until Chad
   explicitly approves it.

Hermes is runtime-certified only when all six checks pass and the evidence is
recorded outside private content. The repository-side checker intentionally
reports `runtime_certified: false` until that live proof exists.

## Boundaries

- Second Self remains the brain, evidence store, and memory system.
- ECHO remains the coordinator and user-facing agent.
- Walter researches, Sherlock investigates, and Charlie builds.
- Specialists run as separate sessions with scoped context by default.
- Protected writes remain approval-gated.
- Missing Hermes, Ollama, scheduler state, or external connectors does not
  change the core readiness result; those are separate capability checks.
