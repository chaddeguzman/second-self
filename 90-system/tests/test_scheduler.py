"""Synthetic Phase 13 tests for scheduler models, store, and read-only CLI."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from second_self.cli import main
import second_self.cli as cli_module
from second_self.core.paths import SecondSelfPaths
from second_self.scheduler import (
    JobDefinition,
    JobRun,
    JobStore,
    RetryPolicy,
    Schedule,
    SchedulerState,
    SchedulerStateError,
)
from second_self.scheduler.due import due_jobs, run_due
from second_self.scheduler.lock import SchedulerLock
from second_self.scheduler.adapters import ADAPTERS, initial_job_definitions
from second_self.scheduler.launcher import (
    TASK_NAME, TaskSpec, install_launcher, launcher_status, remove_launcher,
)
from second_self.scheduler.models import ScheduleKind


OCCURRENCE = "2026-09-16T09:00:00+08:00"


def _job(job_id: str = "daily-health") -> JobDefinition:
    return JobDefinition(
        job_id, "test-noop", True, "Asia/Shanghai",
        Schedule(ScheduleKind.DAILY, time="09:00"),
        retry_policy=RetryPolicy(2, 30),
        parameters=(("report", "health"),),
    )


def _run(run_id: str = "run-1", occurrence: str = OCCURRENCE) -> JobRun:
    return JobRun(
        run_id, "daily-health", occurrence, "succeeded", started_at=occurrence,
        ended_at="2026-09-16T09:00:02+08:00",
        idempotency_key=JobRun.make_idempotency_key("daily-health", occurrence),
        summary="completed",
    )


@pytest.mark.parametrize(
    "schedule",
    [
        Schedule(ScheduleKind.DAILY, time="09:00"),
        Schedule(ScheduleKind.WEEKLY, time="09:00", weekday=2),
        Schedule(ScheduleKind.INTERVAL, interval_minutes=15),
    ],
)
def test_supported_schedules_round_trip(schedule: Schedule) -> None:
    assert Schedule.from_dict(schedule.as_dict()) == schedule


def test_models_reject_unsafe_or_invalid_values() -> None:
    with pytest.raises(ValueError, match="adapter"):
        JobDefinition("unsafe", "shell", True, "UTC", Schedule(ScheduleKind.DAILY, time="09:00"))
    with pytest.raises(ValueError, match="time_zone"):
        JobDefinition("bad-zone", "read-only", True, "Not/AZone", Schedule(ScheduleKind.DAILY, time="09:00"))
    with pytest.raises(ValueError, match="timeout"):
        JobDefinition("bad-timeout", "read-only", True, "UTC", Schedule(ScheduleKind.DAILY, time="09:00"), timeout_seconds=0)
    with pytest.raises(ValueError, match="schedule"):
        Schedule.from_dict({"kind": "daily", "time": "09:00", "prompt": "private prose"})
    with pytest.raises(ValueError, match="parameters"):
        JobDefinition(
            "raw-data", "read-only", True, "UTC",
            Schedule(ScheduleKind.DAILY, time="09:00"),
            parameters=(("prompt", "private prose"),),
        )
    with pytest.raises(ValueError, match="parameters"):
        JobDefinition(
            "raw-path", "read-only", True, "UTC",
            Schedule(ScheduleKind.DAILY, time="09:00"),
            parameters=(("report", "C:\\private\\note.md"),),
        )


def test_store_is_atomic_and_retains_bounded_history(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "scheduler" / "jobs.json", max_history=2)
    store.add_job(_job())
    store.record_run(_run("run-1", "2026-09-16T09:00:00+08:00"))
    store.record_run(_run("run-2", "2026-09-17T09:00:00+08:00"))
    state = store.record_run(_run("run-3", "2026-09-18T09:00:00+08:00"))
    assert [run.run_id for run in state.runs] == ["run-2", "run-3"]
    assert not list(store.path.parent.glob("*.tmp"))
    assert JobStore(store.path).read() == state


def test_duplicate_idempotency_does_not_append_history(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.json")
    store.add_job(_job())
    first = store.record_run(_run())
    second = store.record_run(_run("different-run-id"))
    assert second == first


def test_corrupt_state_is_preserved_and_redacted(tmp_path: Path) -> None:
    path = tmp_path / "jobs.json"
    path.write_text('{"private_path":"C:/secret","jobs":', encoding="utf-8")
    with pytest.raises(SchedulerStateError, match="invalid"):
        JobStore(path).read()
    assert path.read_text(encoding="utf-8").startswith('{"private_path"')


def test_empty_schedule_cli_is_stable_and_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # A synthetic operational root keeps CI independent of private config.
    monkeypatch.setattr(
        cli_module, "load_paths", lambda require_config=False: SecondSelfPaths(tmp_path, tmp_path / "data")
    )
    assert main(["schedule", "list", "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {"version": "schedule-list/v1", "jobs": []}


def test_due_runner_runs_once_and_records_completion(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.json")
    store.add_job(_job())
    now = datetime(2026, 9, 16, 10, tzinfo=timezone.utc)
    assert len(due_jobs(store.read(), now)) == 1
    first = run_due(store, SchedulerLock(tmp_path / "run.lock", owner="test"), now=now)
    second = run_due(store, SchedulerLock(tmp_path / "run.lock", owner="test"), now=now)
    assert first.as_dict()["outcome"] == "success"
    assert second.as_dict()["outcome"] == "no-work"
    assert store.read().runs[0].summary == "test_noop"


def test_due_runner_isolates_unavailable_adapter(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.json")
    store.add_job(JobDefinition("unsupported", "notification", True, "UTC", Schedule(ScheduleKind.DAILY, time="09:00")))
    result = run_due(
        store, SchedulerLock(tmp_path / "run.lock", owner="test"),
        now=datetime(2026, 9, 16, 10, tzinfo=timezone.utc),
    )
    assert result.outcome == "partial-failure"
    assert store.read().runs[0].summary == "adapter_not_available"


def test_lock_contention_and_stale_recovery(tmp_path: Path) -> None:
    path = tmp_path / "run.lock"
    first = SchedulerLock(path, owner="first")
    second = SchedulerLock(path, owner="second")
    assert first.acquire(now=100)
    assert second.acquire(now=101) is False
    first.release()
    path.write_text('{"owner":"old","acquired_at":100}', encoding="utf-8")
    assert second.acquire(now=100 + 15 * 60 + 1)
    second.release()


def test_phase_16_has_five_disabled_safe_adapters() -> None:
    jobs = initial_job_definitions()
    assert len(ADAPTERS) == 5
    assert {job.adapter for job in jobs} == set(ADAPTERS)
    assert all(not job.enabled for job in jobs)
    assert all(job.adapter in {"calendar-snapshot", "time-capsule-reminder", "review-reminder", "backup-due-reminder", "memory-health-check"} for job in jobs)


class FakeTaskBackend:
    def __init__(self) -> None:
        self.installed = False

    def query(self, _name: str) -> bool:
        return self.installed

    def create(self, spec: TaskSpec) -> bool:
        assert spec.name == TASK_NAME
        self.installed = True
        return True

    def remove(self, _name: str) -> bool:
        self.installed = False
        return True


def test_launcher_requires_confirmation_and_verifies_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = FakeTaskBackend()
    monkeypatch.setattr("second_self.scheduler.launcher.os.name", "nt")
    preview = install_launcher(backend, confirmed=False)
    assert preview["reason"] == "confirmation_required"
    assert not backend.installed
    installed = install_launcher(backend, confirmed=True)
    assert installed["verified"] is True
    assert launcher_status(backend)["installed"] is True
    removed = remove_launcher(backend, confirmed=True)
    assert removed["verified"] is True
