# ECHO Local-Agent Foundation Capabilities

This is the verified Phase 17 runtime reference. It does not replace ECHO's
identity, skill, evidence, broker, or approval rules.

| Surface | Command | Verified behavior |
|---|---|---|
| Unified health | `python -m second_self doctor [--strict] [--json]` | Reports ECHO, Calendar, routing/Ollama readiness, evaluation state, scheduler state, privacy, vault, and Git checks with redacted details. |
| Routing diagnostic | `python -m second_self route --operation NAME --sensitivity LEVEL --dry-run [--json]` | Validates trusted metadata and fails closed without accepting a prompt or invoking a provider. |
| Synthetic evaluations | `python -m second_self eval [suite] [--json]` | Runs deterministic recall/safety gates against the reviewed baseline without private fixtures or model judging. |
| Scheduler | `python -m second_self schedule list\|status\|run-due\|install\|remove [--json]` | Uses versioned local state, bounded locking/retries, disabled-by-default jobs, and explicit launcher confirmation. |
| Dashboard summary | Local dashboard home | Shows payload-free health, routing, evaluation, scheduler, and Calendar availability states. |

Conditional operation rules:

- Use `doctor` for live readiness. Dashboard cards are concise summaries.
- Missing Ollama denies local drafting safely; it never triggers cloud fallback.
- Calendar failure degrades only Calendar output.
- Corrupt scheduler state is preserved and reported; manual `run-due` remains
  the launcher recovery path.
- No scheduled job may approve a protected write or send an external message.
