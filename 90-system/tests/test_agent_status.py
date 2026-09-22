"""Tests for the redacted delegated-agent status view."""

import json

from second_self.agent_status import build_report, main


def _write_log(root, name: str, content: str) -> None:
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "log.md").write_text(content, encoding="utf-8")


def test_roster_reads_current_status_and_latest_assignment(tmp_path):
    _write_log(
        tmp_path,
        "charlie",
        """# Charlie — Assignment and Task Log

> Current status: In Progress: UX-004

| Date | Time | Request | Status | Output/Summary |
|------|------|---------|--------|----------------|
| 2026-09-20 | | OBS-001: old item | Done | complete |
| 2026-09-22 | | UX-004: add delegation status | In Progress | working |
""",
    )
    _write_log(
        tmp_path,
        "walter",
        """# Walter — Status: Idle

| Date | Time | Request | Status | Output/Summary |
|------|------|---------|--------|----------------|
| 2026-09-21 | | RESEARCH-001: old item | Done | complete |
""",
    )

    report = build_report(tmp_path)

    assert report["version"] == "agent-status/v1"
    assert report["agents"] == [
        {
            "name": "charlie",
            "current_status": "In Progress: UX-004",
            "latest_assignment": "UX-004",
            "latest_request": "UX-004: add delegation status",
            "latest_task_status": "In Progress",
        },
        {
            "name": "walter",
            "current_status": "Idle",
            "latest_assignment": "RESEARCH-001",
            "latest_request": "RESEARCH-001: old item",
            "latest_task_status": "Done",
        },
    ]


def test_roster_ignores_missing_or_malformed_logs(tmp_path):
    _write_log(tmp_path, "sherlock", "# Sherlock — Status: Blocked\nnot a table\n")
    (tmp_path / "walter").mkdir()

    report = build_report(tmp_path)

    assert report["agents"] == [
        {
            "name": "sherlock",
            "current_status": "Blocked",
            "latest_assignment": None,
            "latest_request": None,
            "latest_task_status": None,
        }
    ]


def test_agent_status_cli_supports_text_and_json(tmp_path, capsys):
    _write_log(tmp_path, "charlie", "# Charlie — Status: Done\n")

    assert main(["status", "--base-dir", str(tmp_path)]) == 0
    assert "Charlie: Done" in capsys.readouterr().out

    assert main(["status", "--base-dir", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["version"] == "agent-status/v1"
    assert payload["agents"][0]["name"] == "charlie"
