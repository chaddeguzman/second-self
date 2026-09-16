"""End-to-end synthetic checks for the Phase 17 integration surface."""

from __future__ import annotations

import json
from pathlib import Path

from second_self.core.paths import SecondSelfPaths
from second_self.foundation import SUMMARY_VERSION, foundation_summary
from second_self.health.system import SystemHealthContext, check_scheduler_state
from second_self.reads.dashboard import scan_dashboard
from second_self.scheduler import JobStore, SchedulerState


def _paths(tmp_path: Path) -> SecondSelfPaths:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    (data / "01-strategy-storage/01 Capture/00 Raw").mkdir(parents=True)
    (data / "02-skills-projects/projects").mkdir(parents=True)
    (data / "03-wiki").mkdir(parents=True)
    return SecondSelfPaths(repo, data)


def _config(paths: SecondSelfPaths) -> Path:
    config = paths.repo_root / ".second-self.local.json"
    config.write_text(
        json.dumps({"schema_version": 1, "data_root": str(paths.data_root)}),
        encoding="utf-8",
    )
    return config


def test_doctor_scheduler_uses_configured_operational_cache(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    config = _config(paths)
    store = JobStore(paths.cache / "scheduler" / "jobs.json")
    store.write(SchedulerState())

    result = check_scheduler_state(SystemHealthContext(paths.repo_root, config))

    assert result.status == "OK"
    assert str(paths.data_root) not in result.detail


def test_foundation_summary_is_bounded_and_payload_free(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    _config(paths)
    (paths.repo_root / "90-system/evaluation-baseline.json").parent.mkdir(parents=True)
    summary = foundation_summary(paths)

    assert summary["version"] == SUMMARY_VERSION
    assert set(summary["areas"]) == {"health", "routing", "evaluation", "scheduler", "calendar"}
    serialized = json.dumps(summary)
    assert str(paths.data_root) not in serialized
    assert summary["areas"]["routing"] == "policy-ready"


def test_dashboard_exposes_same_payload_free_summary(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    _config(paths)

    snapshot = scan_dashboard(paths)

    assert snapshot.foundation["version"] == SUMMARY_VERSION
    assert "routing" in snapshot.foundation["areas"]


def test_one_corrupt_subsystem_does_not_hide_other_areas(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    _config(paths)
    scheduler = paths.cache / "scheduler" / "jobs.json"
    scheduler.parent.mkdir(parents=True)
    scheduler.write_text('{"private":"never render",', encoding="utf-8")

    summary = foundation_summary(paths)

    assert summary["areas"]["scheduler"] == "warn"
    assert summary["areas"]["routing"] == "policy-ready"
    assert "never render" not in json.dumps(summary)


def test_corrupt_config_fails_closed_without_path_output(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    config = paths.repo_root / ".second-self.local.json"
    config.write_text('{"data_root":"C:/private",', encoding="utf-8")

    summary = foundation_summary(paths, config_path=config)

    serialized = json.dumps(summary)
    assert "C:/private" not in serialized
    assert summary["areas"]["routing"] == "policy-ready"
