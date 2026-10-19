"""Payload-free integration summary for the local-agent foundation."""

from __future__ import annotations

from pathlib import Path

from .core.paths import SecondSelfPaths
from .health.system import (
    SystemHealthContext,
    check_evaluation_state,
    check_privacy_validator,
)
from .routing import DataOrigin, DataOriginKind, diagnose_policy
from .scheduler import JobStore, SchedulerStateError

SUMMARY_VERSION = "local-agent-foundation/v1"


def _scheduler_status(context: SystemHealthContext) -> str:
    """Distinguish an unused optional scheduler from invalid operational state."""
    try:
        state = JobStore(context.cache_root / "scheduler" / "jobs.json").read()
    except (SchedulerStateError, OSError, TypeError):
        return "warn"
    return "ok" if state.jobs else "not-configured"


def _routing_status() -> str:
    decision = diagnose_policy(
        operation="foundation-status",
        sensitivity="prohibited",
        origins=(DataOrigin(DataOriginKind.EXTERNAL_UNTRUSTED, "dashboard"),),
    )
    return "policy-ready" if decision.outcome.value == "deny" else "attention"


def foundation_summary(
    paths: SecondSelfPaths, *, config_path: Path | None = None
) -> dict[str, object]:
    """Return bounded subsystem states without loading private payloads."""
    context = SystemHealthContext(
        repo_root=paths.repo_root,
        config_path=config_path or paths.repo_root / ".second-self.local.json",
    )
    calendar_script = (
        paths.repo_root / "90-system" / ".echo" / "scripts" / "echo-calendar.py"
    )
    return {
        "version": SUMMARY_VERSION,
        "areas": {
            "health": check_privacy_validator(context).status.lower(),
            "routing": _routing_status(),
            "evaluation": check_evaluation_state(context).status.lower(),
            "scheduler": _scheduler_status(context),
            "calendar": "command-available" if calendar_script.is_file() else "unavailable",
        },
    }
