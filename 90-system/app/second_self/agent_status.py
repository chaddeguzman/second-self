"""Redacted status projections for tracked delegated-agent logs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_STATUS_RE = re.compile(r"(?:Current status:|Status:)\s*(.+)$", re.IGNORECASE)
_ASSIGNMENT_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d{3}\b")


def _current_status(text: str) -> str:
    for line in text.splitlines()[:8]:
        if line.startswith(">") or line.startswith("#"):
            match = _STATUS_RE.search(line)
            if match:
                return match.group(1).strip()
    return "Unknown"


def _latest_task(text: str, current_status: str) -> dict[str, str | None]:
    rows: list[dict[str, str | None]] = []
    for line in text.splitlines():
        if not line.startswith("|") or line.startswith("|-"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 5 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[0]):
            continue
        request = cells[2]
        assignment = _ASSIGNMENT_RE.search(request)
        rows.append(
            {
                "latest_assignment": assignment.group(0) if assignment else None,
                "latest_request": request or None,
                "latest_task_status": cells[3] or None,
            }
        )
    active_ids = _ASSIGNMENT_RE.findall(current_status)
    for active_id in active_ids:
        for row in rows:
            if row["latest_assignment"] == active_id:
                return row
    return rows[0] if rows else {
        "latest_assignment": None,
        "latest_request": None,
        "latest_task_status": None,
    }


def build_report(subagents_root: Path) -> dict[str, Any]:
    agents: list[dict[str, Any]] = []
    if subagents_root.is_dir():
        for log_path in sorted(subagents_root.glob("*/log.md")):
            text = log_path.read_text(encoding="utf-8")
            current_status = _current_status(text)
            task = _latest_task(text, current_status)
            agents.append(
                {
                    "name": log_path.parent.name,
                    "current_status": current_status,
                    **task,
                }
            )
    return {"version": "agent-status/v1", "agents": agents}


def render_report(report: dict[str, Any]) -> str:
    lines = ["ECHO delegated-agent status"]
    for agent in report["agents"]:
        assignment = agent["latest_assignment"] or "no assignment"
        task_status = agent["latest_task_status"] or "unknown"
        lines.append(
            f"- {agent['name'].title()}: {agent['current_status']} — "
            f"{assignment} ({task_status})"
        )
    if len(lines) == 1:
        lines.append("- No agent logs found.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="echo-agents")
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("--base-dir", type=Path, required=True)
    status.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.base_dir)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0
