"""Due occurrence calculation and isolated test-only job execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from time import monotonic
from uuid import uuid4
from zoneinfo import ZoneInfo

from .lock import SchedulerLock, SchedulerLockError
from .models import JobDefinition, JobRun, ScheduleKind, SchedulerState
from .store import JobStore, SchedulerStateError


@dataclass(frozen=True)
class DueResult:
    outcome: str
    considered: int
    succeeded: int
    failed: int
    skipped: int
    reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "version": "schedule-run/v1", "outcome": self.outcome,
            "considered": self.considered, "succeeded": self.succeeded,
            "failed": self.failed, "skipped": self.skipped,
        }
        if self.reason:
            result["reason"] = self.reason
        return result


def _occurrence(job: JobDefinition, now: datetime) -> datetime | None:
    local_now = now.astimezone(ZoneInfo(job.time_zone))
    schedule = job.schedule
    if schedule.kind is ScheduleKind.INTERVAL:
        interval = schedule.interval_minutes * 60
        epoch_seconds = int(local_now.timestamp())
        return datetime.fromtimestamp(epoch_seconds - epoch_seconds % interval, ZoneInfo(job.time_zone))
    hour, minute = (int(part) for part in schedule.time.split(":"))
    candidate = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if schedule.kind is ScheduleKind.WEEKLY:
        candidate -= timedelta(days=(local_now.weekday() - schedule.weekday) % 7)
    if candidate > local_now:
        return None
    return candidate


def due_jobs(state: SchedulerState, now: datetime) -> tuple[tuple[JobDefinition, datetime], ...]:
    due: list[tuple[JobDefinition, datetime]] = []
    for job in state.jobs:
        if not job.enabled:
            continue
        occurrence = _occurrence(job, now)
        if occurrence is None:
            continue
        if job.last_completed_occurrence:
            completed = datetime.fromisoformat(job.last_completed_occurrence.replace("Z", "+00:00"))
            if occurrence <= completed.astimezone(occurrence.tzinfo):
                continue
        due.append((job, occurrence))
    return tuple(due)


def _complete(state: SchedulerState, job_id: str, occurrence: str) -> SchedulerState:
    jobs = tuple(
        job if job.job_id != job_id else JobDefinition(
            job.job_id, job.adapter, job.enabled, job.time_zone, job.schedule,
            job.timeout_seconds, job.retry_policy, job.parameters, job.version, occurrence,
        )
        for job in state.jobs
    )
    return SchedulerState(jobs, state.runs, state.version)


def run_due(store: JobStore, lock: SchedulerLock, *, now: datetime) -> DueResult:
    try:
        state = store.read()
    except SchedulerStateError:
        return DueResult("state-failure", 0, 0, 0, 0, "scheduler_state_unavailable")
    try:
        if not lock.acquire():
            return DueResult("lock-contention", 0, 0, 0, 0, "scheduler_lock_busy")
    except SchedulerLockError:
        return DueResult("state-failure", 0, 0, 0, 0, "scheduler_lock_unavailable")
    try:
        due = due_jobs(state, now)
        if not due:
            return DueResult("no-work", 0, 0, 0, 0)
        succeeded = failed = skipped = 0
        for job, occurrence in due:
            occurrence_text = occurrence.isoformat()
            key = JobRun.make_idempotency_key(job.job_id, occurrence_text)
            existing = next((run for run in state.runs if run.idempotency_key == key), None)
            if existing and existing.outcome == "succeeded":
                skipped += 1
                continue
            if job.adapter != "test-noop":
                outcome, summary = "failed", "adapter_not_available"
            else:
                # The no-op adapter is intentionally bounded and cannot receive
                # a command, prompt, module path, or private payload.
                started = monotonic()
                outcome, summary = "succeeded", "test_noop"
                if monotonic() - started > job.timeout_seconds:
                    outcome, summary = "failed", "timeout"
            attempts = 1
            while outcome == "failed" and attempts < job.retry_policy.max_attempts:
                attempts += 1
                if job.adapter == "test-noop":
                    outcome, summary = "succeeded", "test_noop"
            run = JobRun(
                f"run-{uuid4().hex[:16]}", job.job_id, occurrence_text, outcome,
                attempt=attempts, idempotency_key=key, summary=summary,
            )
            state = SchedulerState(state.jobs, (*state.runs, run))
            if outcome == "succeeded":
                state = _complete(state, job.job_id, occurrence_text)
                succeeded += 1
            else:
                failed += 1
            state = SchedulerState(state.jobs, tuple(state.runs[-store.max_history:] if store.max_history else ()))
            try:
                store.write(state)
            except SchedulerStateError:
                return DueResult("state-failure", len(due), succeeded, failed, skipped, "history_write_failed")
        return DueResult("partial-failure" if failed else "success", len(due), succeeded, failed, skipped)
    finally:
        try:
            lock.release()
        except SchedulerLockError:
            pass
