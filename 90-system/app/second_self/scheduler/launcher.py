"""Least-privilege Windows Task Scheduler launcher boundary."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


TASK_NAME = "Second Self - Run Due"


@dataclass(frozen=True)
class TaskSpec:
    name: str = TASK_NAME
    cadence: str = "ONLOGON"
    command: str = "second-self schedule run-due"
    run_level: str = "LIMITED"
    instance_policy: str = "IGNORE_NEW"

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "cadence": self.cadence, "command": self.command,
                "run_level": self.run_level, "instance_policy": self.instance_policy}


class TaskSchedulerBackend(Protocol):
    def query(self, name: str) -> bool: ...
    def create(self, spec: TaskSpec) -> bool: ...
    def remove(self, name: str) -> bool: ...


class WindowsTaskScheduler:
    """Small subprocess adapter; tests inject a fake instead."""

    def _run(self, args: list[str]) -> bool:
        try:
            return subprocess.run(args, capture_output=True, text=True, check=False).returncode == 0
        except OSError:
            return False

    def query(self, name: str) -> bool:
        return self._run(["schtasks.exe", "/Query", "/TN", name])

    def create(self, spec: TaskSpec) -> bool:
        if os.name != "nt":
            return False
        executable = Path(sys.executable).resolve()
        return self._run([
            "schtasks.exe", "/Create", "/TN", spec.name, "/SC", spec.cadence,
            "/TR", f'"{executable}" -m second_self schedule run-due', "/RL", spec.run_level, "/F",
        ])

    def remove(self, name: str) -> bool:
        return self._run(["schtasks.exe", "/Delete", "/TN", name, "/F"])


def task_preview() -> TaskSpec:
    return TaskSpec()


def launcher_status(backend: TaskSchedulerBackend) -> dict[str, object]:
    if os.name != "nt":
        return {"version": "launcher-status/v1", "supported": False, "installed": False, "reason": "unsupported_platform"}
    return {"version": "launcher-status/v1", "supported": True, "installed": backend.query(TASK_NAME), "task": task_preview().as_dict()}


def install_launcher(backend: TaskSchedulerBackend, *, confirmed: bool) -> dict[str, object]:
    preview = task_preview().as_dict()
    if not confirmed:
        return {"version": "launcher-action/v1", "action": "install", "changed": False, "reason": "confirmation_required", "task": preview}
    if os.name != "nt":
        return {"version": "launcher-action/v1", "action": "install", "changed": False, "reason": "unsupported_platform", "task": preview}
    changed = backend.create(task_preview())
    return {"version": "launcher-action/v1", "action": "install", "changed": changed, "verified": changed and backend.query(TASK_NAME), "task": preview}


def remove_launcher(backend: TaskSchedulerBackend, *, confirmed: bool) -> dict[str, object]:
    if not confirmed:
        return {"version": "launcher-action/v1", "action": "remove", "changed": False, "reason": "confirmation_required"}
    if os.name != "nt":
        return {"version": "launcher-action/v1", "action": "remove", "changed": False, "reason": "unsupported_platform"}
    existed = backend.query(TASK_NAME)
    changed = backend.remove(TASK_NAME) if existed else False
    return {"version": "launcher-action/v1", "action": "remove", "changed": changed, "verified": not backend.query(TASK_NAME)}
