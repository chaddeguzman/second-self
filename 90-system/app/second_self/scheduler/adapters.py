"""Disabled-by-default, non-mutating Phase 16 adapter definitions."""

from __future__ import annotations

from .models import JobDefinition, RetryPolicy, Schedule, ScheduleKind

ADAPTERS = (
    "calendar-snapshot",
    "time-capsule-reminder",
    "review-reminder",
    "backup-due-reminder",
    "memory-health-check",
)


def initial_job_definitions() -> tuple[JobDefinition, ...]:
    common = {"enabled": False, "time_zone": "Asia/Shanghai", "timeout_seconds": 60,
              "retry_policy": RetryPolicy(2, 30)}
    return (
        JobDefinition("calendar-snapshot", ADAPTERS[0], schedule=Schedule(ScheduleKind.DAILY, time="07:00"), parameters=(("period", "today"),), **common),
        JobDefinition("time-capsule-reminder", ADAPTERS[1], schedule=Schedule(ScheduleKind.DAILY, time="09:00"), parameters=(("mode", "notify"),), **common),
        JobDefinition("review-reminder", ADAPTERS[2], schedule=Schedule(ScheduleKind.WEEKLY, time="09:00", weekday=0), parameters=(("cadence", "weekly"),), **common),
        JobDefinition("backup-due-reminder", ADAPTERS[3], schedule=Schedule(ScheduleKind.WEEKLY, time="09:30", weekday=4), parameters=(("mode", "notify"),), **common),
        JobDefinition("memory-health-check", ADAPTERS[4], schedule=Schedule(ScheduleKind.WEEKLY, time="10:00", weekday=6), parameters=(("mode", "read-only"),), **common),
    )
