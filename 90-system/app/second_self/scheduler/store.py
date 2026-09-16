"""Atomic local scheduler state storage with bounded history."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .models import JobDefinition, JobRun, SchedulerState


class SchedulerStateError(ValueError):
    """Safe public error for missing or corrupt operational scheduler state."""


class JobStore:
    def __init__(self, path: Path, *, max_history: int = 100) -> None:
        if not isinstance(max_history, int) or not 0 <= max_history <= 10_000:
            raise ValueError("invalid max_history")
        self.path = path
        self.max_history = max_history

    def read(self) -> SchedulerState:
        if not self.path.exists():
            return SchedulerState()
        try:
            if self.path.stat().st_size > 5 * 1024 * 1024:
                raise ValueError
            return SchedulerState.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, json.JSONDecodeError):
            raise SchedulerStateError("scheduler state is missing or invalid") from None

    def write(self, state: SchedulerState) -> None:
        if not isinstance(state, SchedulerState):
            raise ValueError("invalid scheduler state")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(state.as_dict(), stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except OSError:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise SchedulerStateError("scheduler state could not be written") from None

    def add_job(self, job: JobDefinition) -> SchedulerState:
        state = self.read()
        if any(existing.job_id == job.job_id for existing in state.jobs):
            raise SchedulerStateError("job already exists")
        updated = SchedulerState(tuple(sorted((*state.jobs, job), key=lambda item: item.job_id)), state.runs)
        self.write(updated)
        return updated

    def record_run(self, run: JobRun) -> SchedulerState:
        state = self.read()
        if run.idempotency_key and any(existing.idempotency_key == run.idempotency_key for existing in state.runs):
            return state
        runs = (*state.runs, run)
        updated = SchedulerState(state.jobs, tuple(runs[-self.max_history:] if self.max_history else ()))
        self.write(updated)
        return updated
