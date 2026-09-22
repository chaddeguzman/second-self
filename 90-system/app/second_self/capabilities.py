"""Stable, payload-free ECHO capability status registry."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class Capability:
    name: str
    state: str
    summary: str
    reason_code: str
    writes_external: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def build_registry() -> tuple[Capability, ...]:
    return (
        Capability("echo", "available", "Core ECHO coordination", "core"),
        Capability("second-self-recall", "available", "Local evidence-aware recall", "core"),
        Capability(
            "semantic-memory",
            "available",
            "Semantic recall with keyword fallback",
            "local_fallback",
        ),
        Capability(
            "calendar", "degraded", "Read-only Calendar when configured", "optional_connector"
        ),
        Capability(
            "gmail", "disabled", "Future read-only, on-demand Gmail search", "future_connector"
        ),
        Capability(
            "drive", "disabled", "Future read-only, on-demand Drive search", "future_connector"
        ),
        Capability(
            "external-actions", "planned", "Future approval-gated external actions", "future_scope"
        ),
    )


def build_report() -> dict[str, object]:
    return {
        "version": "capabilities/v1",
        "capabilities": [item.as_dict() for item in build_registry()],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="echo-capabilities")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for item in report["capabilities"]:
            print(f"{item['name']}: {item['state']} — {item['summary']}")
    return 0
