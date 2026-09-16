"""Payload-free integration summary for the local-agent foundation."""

from __future__ import annotations

from pathlib import Path

from .core.paths import SecondSelfPaths
from .health.system import (
    SystemHealthContext,
    check_evaluation_state,
    check_privacy_validator,
    check_scheduler_state,
)
from .routing import DataOrigin, DataOriginKind, diagnose_policy


SUMMARY_VERSION = "local-agent-foundation/v1"


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
            "scheduler": check_scheduler_state(context).status.lower(),
            "calendar": "command-available" if calendar_script.is_file() else "unavailable",
        },
    }
