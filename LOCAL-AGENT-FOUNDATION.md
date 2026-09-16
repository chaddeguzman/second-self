# Local-Agent Foundation

The local-agent foundation is the shared, privacy-aware runtime beneath ECHO and
Second Self. It consists of four public command families:

```powershell
python -m second_self doctor --json
python -m second_self route --operation NAME --sensitivity LEVEL --dry-run --json
python -m second_self eval --json
python -m second_self schedule status --json
```

`doctor` is the authoritative live readiness check. The local dashboard shows a
bounded summary for health, routing policy, evaluation baseline, scheduler state,
and Calendar command availability. Neither surface renders prompts, credentials,
private absolute paths, evaluation fixtures, or scheduler parameters.

## Recovery

- Ollama unavailable: routing fails closed; restore the configured local service
  and rerun `doctor`.
- Evaluation baseline missing or incompatible: run the synthetic suites, review
  the result, and use the explicit baseline refresh only when intentionally
  accepting a reviewed baseline change.
- Scheduler state missing: `schedule list` remains an empty read-only view. A
  corrupt state file is preserved for diagnosis and is never overwritten.
- Launcher mismatch or removal: inspect with `schedule status --launcher --json`.
  Installation and removal require explicit `--confirm`; manual `run-due` remains
  available.
- Calendar unavailable: use `echo-calendar.py doctor-check`; other health and
  briefing sections continue to work.

## Safety boundaries

Tracked tests use synthetic data. Cloud routing requires trusted sanitization or
approval bound to the exact payload. Scheduled jobs cannot approve protected
writes, send messages, or install an OS task implicitly. Live Ollama and Windows
Task Scheduler verification are optional and require direct user intent.
