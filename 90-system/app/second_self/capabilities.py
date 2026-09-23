"""Stable, payload-free ECHO capability status registry."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Capability:
    name: str
    state: str
    summary: str
    reason_code: str
    writes_external: bool = False
    boundary: str = "local_only"
    prerequisites: tuple[str, ...] = ()
    approval: str = "none"
    fallback: str = "none"
    examples: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def build_registry() -> tuple[Capability, ...]:
    return (
        Capability(
            "echo",
            "available",
            "Core ECHO coordination",
            "core",
            examples=("ask ECHO what it can do",),
        ),
        Capability(
            "second-self-recall",
            "available",
            "Local evidence-aware recall",
            "core",
            prerequisites=("curated local sources",),
            fallback="reports not found when local evidence is missing",
            examples=("recall what I wrote about a topic",),
        ),
        Capability(
            "semantic-memory",
            "available",
            "Semantic recall with keyword fallback",
            "local_fallback",
            prerequisites=("local semantic index",),
            fallback="keyword recall remains available when semantic search is unavailable",
            examples=("recall related ideas",),
        ),
        Capability(
            "calendar",
            "degraded",
            "Read-only Calendar when configured",
            "optional_connector",
            boundary="external_provider_read_only",
            prerequisites=("configured Calendar connector",),
            fallback="reports unavailable or stale snapshot status without blocking local features",
            examples=("show today's calendar",),
        ),
        Capability(
            "gmail",
            "disabled",
            "Future read-only, on-demand Gmail search",
            "future_connector",
            boundary="external_provider_when_enabled",
            prerequisites=(
                "DOC-002 contract",
                "explicit enablement",
                "read-only OAuth consent",
            ),
            approval="explicit_request",
            fallback="remains disabled; local recall is unaffected",
            examples=(
                "python -m second_self gmail auth --client-config <local-file>",
                "python -m second_self gmail search \"from:team\"",
            ),
        ),
        Capability(
            "drive",
            "disabled",
            "Future read-only, on-demand Drive search",
            "future_connector",
            boundary="external_provider_when_enabled",
            prerequisites=("DOC-002 contract", "explicit enablement"),
            approval="explicit_request",
            fallback="remains disabled; local recall is unaffected",
            examples=("search Drive metadata",),
        ),
        Capability(
            "external-actions",
            "planned",
            "Future approval-gated external actions; contract only",
            "future_scope",
            boundary="external_provider_when_enabled",
            prerequisites=("ACT-001 action contract", "scoped permission"),
            approval="explicit_confirmation",
            fallback="does not create, send, upload, or change anything",
            examples=("draft an email for review",),
        ),
    )


def build_report() -> dict[str, Any]:
    return {
        "version": "capabilities/v1",
        "capabilities": [item.as_dict() for item in build_registry()],
    }


_STATE_LEGEND = {
    "available": {
        "meaning": "ready to use within its documented boundary",
        "next_step": "ask ECHO to use this capability",
    },
    "degraded": {
        "meaning": "usable with a documented limitation or fallback",
        "next_step": "use the capability with its stated fallback",
    },
    "disabled": {
        "meaning": "known capability that is intentionally not active",
        "next_step": "wait for an approved adapter and explicit enablement",
    },
    "planned": {
        "meaning": "future scope that is not implemented or authorized",
        "next_step": "wait for a reviewed design and implementation",
    },
}


def build_guide_report() -> dict[str, Any]:
    capabilities: list[dict[str, Any]] = []
    for item in build_registry():
        payload = item.as_dict()
        payload["next_step"] = _STATE_LEGEND[item.state]["next_step"]
        capabilities.append(payload)
    return {
        "version": "capability-help/v1",
        "state_legend": _STATE_LEGEND,
        "capabilities": capabilities,
    }


def render_guide(report: dict[str, Any]) -> str:
    lines = ["ECHO capability guide", "", "State meanings"]
    for state, details in report["state_legend"].items():
        lines.append(f"- {state}: {details['meaning']}")
    lines.extend(["", "Capabilities"])
    for item in report["capabilities"]:
        lines.extend(
            [
                f"- {item['name']}: {item['state']} — {item['summary']}",
                f"  Boundary: {item['boundary']}",
                f"  Prerequisites: {', '.join(item['prerequisites']) or 'none'}",
                f"  Approval: {item['approval']}",
                f"  Fallback: {item['fallback']}",
                f"  Example: {item['examples'][0] if item['examples'] else 'none'}",
                f"  Next: {item['next_step']}",
            ]
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="echo-capabilities")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--guide", action="store_true")
    args = parser.parse_args(argv)
    report = build_guide_report() if args.guide else build_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.guide:
        print(render_guide(report))
    else:
        for item in build_report()["capabilities"]:
            print(f"{item['name']}: {item['state']} — {item['summary']}")
    return 0
