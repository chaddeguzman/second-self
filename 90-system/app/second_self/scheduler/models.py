"""Validated, redacted scheduler data models.

These models describe jobs and history only. They deliberately contain no
execution hooks, prompt fields, or filesystem paths.
"""

from __future__ import annotations

import hashlib
import ntpath
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SCHEMA_VERSION = "scheduler-state/v1"
_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
ALLOWED_ADAPTERS = frozenset({"notification", "read-only", "test-noop"})
OUTCOMES = frozenset({"pending", "running", "succeeded", "failed", "skipped"})
_FORBIDDEN_PARAMETER_KEYS = frozenset({"args", "body", "command", "content", "path", "payload", "prompt", "text"})


def _text(value: Any, field: str, *, max_length: int = 128) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError(f"invalid {field}")
    if any(ord(char) < 32 for char in value):
        raise ValueError(f"invalid {field}")
    return value


def _id(value: Any, field: str) -> str:
    value = _text(value, field, max_length=64)
    if not _ID.fullmatch(value):
        raise ValueError(f"invalid {field}")
    return value


def _timezone(value: Any) -> str:
    value = _text(value, "time_zone", max_length=128)
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("invalid time_zone") from None
    return value


def _iso(value: Any, field: str, *, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    value = _text(value, field, max_length=64)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"invalid {field}") from None
    if parsed.tzinfo is None:
        raise ValueError(f"invalid {field}")
    return value


class ScheduleKind(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    INTERVAL = "interval"


@dataclass(frozen=True)
class Schedule:
    kind: ScheduleKind
    time: str | None = None
    weekday: int | None = None
    interval_minutes: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ScheduleKind):
            raise ValueError("invalid schedule kind")
        if self.kind in (ScheduleKind.DAILY, ScheduleKind.WEEKLY):
            if not isinstance(self.time, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", self.time):
                raise ValueError("invalid schedule time")
        else:
            if self.time is not None or self.weekday is not None:
                raise ValueError("interval schedule has unexpected fields")
        if self.kind is ScheduleKind.WEEKLY and (not isinstance(self.weekday, int) or not 0 <= self.weekday <= 6):
            raise ValueError("invalid schedule weekday")
        if self.kind is not ScheduleKind.WEEKLY and self.weekday is not None:
            raise ValueError("unexpected schedule weekday")
        if self.kind is ScheduleKind.INTERVAL and (not isinstance(self.interval_minutes, int) or not 1 <= self.interval_minutes <= 1_000_000):
            raise ValueError("invalid interval_minutes")
        if self.kind is not ScheduleKind.INTERVAL and self.interval_minutes is not None:
            raise ValueError("unexpected interval_minutes")

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"kind": self.kind.value}
        if self.time is not None:
            result["time"] = self.time
        if self.weekday is not None:
            result["weekday"] = self.weekday
        if self.interval_minutes is not None:
            result["interval_minutes"] = self.interval_minutes
        return result

    @classmethod
    def from_dict(cls, value: Any) -> "Schedule":
        if not isinstance(value, Mapping):
            raise ValueError("invalid schedule")
        try:
            kind = ScheduleKind(_text(value.get("kind"), "schedule.kind", max_length=16))
        except ValueError:
            raise ValueError("invalid schedule kind") from None
        allowed = {
            ScheduleKind.DAILY: {"kind", "time"},
            ScheduleKind.WEEKLY: {"kind", "time", "weekday"},
            ScheduleKind.INTERVAL: {"kind", "interval_minutes"},
        }[kind]
        if set(value) != allowed:
            raise ValueError("invalid schedule fields")
        return cls(kind, value.get("time"), value.get("weekday"), value.get("interval_minutes"))


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    backoff_seconds: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.max_attempts, int) or not 1 <= self.max_attempts <= 10:
            raise ValueError("invalid retry max_attempts")
        if not isinstance(self.backoff_seconds, int) or not 0 <= self.backoff_seconds <= 86_400:
            raise ValueError("invalid retry backoff_seconds")

    def as_dict(self) -> dict[str, int]:
        return {"max_attempts": self.max_attempts, "backoff_seconds": self.backoff_seconds}

    @classmethod
    def from_dict(cls, value: Any) -> "RetryPolicy":
        if not isinstance(value, Mapping) or set(value) != {"max_attempts", "backoff_seconds"}:
            raise ValueError("invalid retry_policy")
        return cls(value["max_attempts"], value["backoff_seconds"])


@dataclass(frozen=True)
class JobDefinition:
    job_id: str
    adapter: str
    enabled: bool
    time_zone: str
    schedule: Schedule
    timeout_seconds: int = 60
    retry_policy: RetryPolicy = RetryPolicy()
    parameters: tuple[tuple[str, str], ...] = ()
    version: str = SCHEMA_VERSION
    last_completed_occurrence: str | None = None

    def __post_init__(self) -> None:
        if self.version != SCHEMA_VERSION:
            raise ValueError("unsupported scheduler schema version")
        _id(self.job_id, "job_id")
        if self.adapter not in ALLOWED_ADAPTERS:
            raise ValueError("adapter is not allowed")
        if not isinstance(self.enabled, bool):
            raise ValueError("invalid enabled")
        _timezone(self.time_zone)
        if not isinstance(self.schedule, Schedule) or not isinstance(self.retry_policy, RetryPolicy):
            raise ValueError("invalid job model")
        if not isinstance(self.timeout_seconds, int) or not 1 <= self.timeout_seconds <= 86_400:
            raise ValueError("invalid timeout_seconds")
        if not isinstance(self.parameters, tuple) or any(
            not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", key)
            or key in _FORBIDDEN_PARAMETER_KEYS
            or not isinstance(value, str) or len(value) > 256 or any(ord(c) < 32 for c in value)
            or ntpath.isabs(value) or value.startswith("\\\\")
            for key, value in self.parameters
        ):
            raise ValueError("invalid parameters")
        if len({key for key, _ in self.parameters}) != len(self.parameters):
            raise ValueError("duplicate parameters")
        _iso(self.last_completed_occurrence, "last_completed_occurrence", required=False)

    def as_dict(self) -> dict[str, Any]:
        return {"version": self.version, "job_id": self.job_id, "adapter": self.adapter,
                "enabled": self.enabled, "time_zone": self.time_zone, "schedule": self.schedule.as_dict(),
                "timeout_seconds": self.timeout_seconds, "retry_policy": self.retry_policy.as_dict(),
                "parameters": dict(self.parameters), "last_completed_occurrence": self.last_completed_occurrence}

    @classmethod
    def from_dict(cls, value: Any) -> "JobDefinition":
        if not isinstance(value, Mapping) or set(value) != {"version", "job_id", "adapter", "enabled", "time_zone", "schedule", "timeout_seconds", "retry_policy", "parameters", "last_completed_occurrence"}:
            raise ValueError("invalid job definition")
        params = value["parameters"]
        if not isinstance(params, Mapping):
            raise ValueError("invalid parameters")
        return cls(value["job_id"], value["adapter"], value["enabled"], value["time_zone"], Schedule.from_dict(value["schedule"]), value["timeout_seconds"], RetryPolicy.from_dict(value["retry_policy"]), tuple(sorted(params.items())), value["version"], value["last_completed_occurrence"])


@dataclass(frozen=True)
class JobRun:
    run_id: str
    job_id: str
    scheduled_occurrence: str
    outcome: str
    attempt: int = 1
    started_at: str | None = None
    ended_at: str | None = None
    idempotency_key: str | None = None
    summary: str = ""
    version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.version != SCHEMA_VERSION:
            raise ValueError("unsupported scheduler schema version")
        _id(self.run_id, "run_id")
        _id(self.job_id, "job_id")
        _iso(self.scheduled_occurrence, "scheduled_occurrence")
        if self.outcome not in OUTCOMES or not isinstance(self.attempt, int) or not 1 <= self.attempt <= 10:
            raise ValueError("invalid run status")
        _iso(self.started_at, "started_at", required=False)
        _iso(self.ended_at, "ended_at", required=False)
        if self.idempotency_key is not None and not re.fullmatch(r"[a-f0-9]{64}", self.idempotency_key):
            raise ValueError("invalid idempotency_key")
        if len(self.summary) > 256 or any(ord(c) < 32 for c in self.summary):
            raise ValueError("invalid summary")

    @staticmethod
    def make_idempotency_key(job_id: str, occurrence: str) -> str:
        return hashlib.sha256(f"{job_id}\0{occurrence}".encode()).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {"version": self.version, "run_id": self.run_id, "job_id": self.job_id,
                "scheduled_occurrence": self.scheduled_occurrence, "outcome": self.outcome,
                "attempt": self.attempt, "started_at": self.started_at, "ended_at": self.ended_at,
                "idempotency_key": self.idempotency_key, "summary": self.summary}

    @classmethod
    def from_dict(cls, value: Any) -> "JobRun":
        if not isinstance(value, Mapping):
            raise ValueError("invalid job run")
        fields = {"version", "run_id", "job_id", "scheduled_occurrence", "outcome", "attempt", "started_at", "ended_at", "idempotency_key", "summary"}
        if set(value) != fields:
            raise ValueError("invalid job run")
        return cls(
            value["run_id"], value["job_id"], value["scheduled_occurrence"],
            value["outcome"], value["attempt"], value["started_at"],
            value["ended_at"], value["idempotency_key"], value["summary"],
            value["version"],
        )


@dataclass(frozen=True)
class SchedulerState:
    jobs: tuple[JobDefinition, ...] = ()
    runs: tuple[JobRun, ...] = ()
    version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.version != SCHEMA_VERSION or len({job.job_id for job in self.jobs}) != len(self.jobs):
            raise ValueError("invalid scheduler state")

    def as_dict(self) -> dict[str, Any]:
        return {"version": self.version, "jobs": [job.as_dict() for job in self.jobs], "runs": [run.as_dict() for run in self.runs]}

    @classmethod
    def from_dict(cls, value: Any) -> "SchedulerState":
        if not isinstance(value, Mapping) or set(value) != {"version", "jobs", "runs"}:
            raise ValueError("invalid scheduler state")
        if not isinstance(value["jobs"], list) or not isinstance(value["runs"], list):
            raise ValueError("invalid scheduler state")
        return cls(tuple(JobDefinition.from_dict(item) for item in value["jobs"]), tuple(JobRun.from_dict(item) for item in value["runs"]), value["version"])
