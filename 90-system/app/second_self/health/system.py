"""Read-only, redacted readiness checks for the Second Self CLI doctor."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .registry import FAIL, OK, WARN, HealthCheck, HealthRegistry, HealthResult


class HttpResponse(Protocol):
    """Minimum response surface required by the bounded Ollama probe."""

    status: int

    def read(self, amount: int = -1) -> bytes: ...

    def __enter__(self) -> HttpResponse: ...

    def __exit__(self, *args: object) -> None: ...


GitRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]
OllamaProbe = Callable[[str, float], HttpResponse]


def _run_git(arguments: Sequence[str], repo_root: Path) -> subprocess.CompletedProcess[str]:
    """Run one bounded, read-only Git query."""
    return subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def _probe_ollama(url: str, timeout: float) -> HttpResponse:
    """Open Ollama's model-list endpoint without sending inference content."""
    return urllib.request.urlopen(url, timeout=timeout)


@dataclass(frozen=True, slots=True)
class SystemHealthContext:
    """Resolved locations and injectable read-only system boundaries."""

    repo_root: Path
    config_path: Path
    git_runner: GitRunner = _run_git
    ollama_probe: OllamaProbe = _probe_ollama

    @property
    def cache_root(self) -> Path:
        return self.repo_root / ".second-self-cache"


def _read_private_root(context: SystemHealthContext) -> Path | None:
    """Return a valid configured data root, otherwise None without path output."""
    try:
        if context.config_path.stat().st_size > 1_048_576:
            return None
        payload = json.loads(context.config_path.read_text(encoding="utf-8"))
        configured = payload.get("data_root") if isinstance(payload, dict) else None
        if not isinstance(configured, str) or not configured.strip():
            return None
        root = Path(os.path.expandvars(configured)).expanduser().resolve()
        if not root.is_dir():
            return None
        return root
    except (OSError, ValueError, TypeError):
        return None


def check_private_path_resolution(context: SystemHealthContext) -> HealthResult:
    """Require a valid local configuration and existing private data root."""
    if not context.config_path.is_file():
        return HealthResult(
            "private-path-resolution", FAIL, "private path configuration is missing"
        )
    if _read_private_root(context) is None:
        return HealthResult(
            "private-path-resolution", FAIL, "private path configuration is invalid"
        )
    return HealthResult("private-path-resolution", OK, "private data root resolved")


def check_active_second_self_vault(context: SystemHealthContext) -> HealthResult:
    """Confirm this workspace is the sole approved Second Self Obsidian vault."""
    required = (
        context.repo_root / ".obsidian",
        context.repo_root / "AGENTS.md",
        context.repo_root / "Start-Second-Self.cmd",
    )
    if not all(path.exists() for path in required):
        return HealthResult(
            "active-second-self-vault", FAIL, "approved Second Self vault not confirmed"
        )
    return HealthResult(
        "active-second-self-vault", OK, "approved Second Self vault confirmed"
    )


def check_git_main_alignment(context: SystemHealthContext) -> HealthResult:
    """Verify main is checked out and aligned without mutating Git state."""
    try:
        branch = context.git_runner(
            ["symbolic-ref", "--quiet", "--short", "HEAD"], context.repo_root
        )
        if branch.returncode != 0 or branch.stdout.strip() != "main":
            return HealthResult(
                "git-main-alignment", FAIL, "repository is detached or not on main"
            )
        alignment = context.git_runner(
            ["rev-list", "--left-right", "--count", "main...origin/main"],
            context.repo_root,
        )
        if alignment.returncode != 0:
            return HealthResult(
                "git-main-alignment", FAIL, "main alignment could not be verified"
            )
        counts = alignment.stdout.strip().split()
        if counts != ["0", "0"]:
            return HealthResult(
                "git-main-alignment", FAIL, "main and origin/main are not aligned"
            )
    except (OSError, subprocess.SubprocessError):
        return HealthResult(
            "git-main-alignment", FAIL, "Git readiness could not be verified"
        )
    return HealthResult("git-main-alignment", OK, "main and origin/main aligned")


def check_privacy_validator(context: SystemHealthContext) -> HealthResult:
    """Require the tracked privacy-validation entry point."""
    validator = (
        context.repo_root
        / "90-system"
        / "automation"
        / "scripts"
        / "second-self.ps1"
    )
    if not validator.is_file():
        return HealthResult(
            "privacy-validator", FAIL, "privacy validator is unavailable"
        )
    return HealthResult("privacy-validator", OK, "privacy validator available")


def check_ollama_readiness(context: SystemHealthContext) -> HealthResult:
    """Probe only Ollama's loopback model-list endpoint with a short timeout."""
    try:
        with context.ollama_probe("http://127.0.0.1:11434/api/tags", 1.0) as response:
            payload = json.loads(response.read(1_048_576).decode("utf-8"))
            if response.status != 200 or not isinstance(payload.get("models"), list):
                raise ValueError("unexpected response")
    except Exception:
        return HealthResult(
            "ollama-readiness", WARN, "optional Ollama service is unavailable"
        )
    return HealthResult("ollama-readiness", OK, "Ollama service ready")


def _check_optional_json_state(
    path: Path, *, check: str, label: str
) -> HealthResult:
    """Report optional JSON state without emitting its path or content."""
    if not path.is_file():
        return HealthResult(check, WARN, f"optional {label} state is absent")
    try:
        if path.stat().st_size > 1_048_576:
            raise ValueError("state file is too large")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("state must be an object")
    except (OSError, ValueError, TypeError):
        return HealthResult(check, WARN, f"optional {label} state is invalid")
    return HealthResult(check, OK, f"{label} state available")


def check_evaluation_state(context: SystemHealthContext) -> HealthResult:
    """Inspect the planned evaluation baseline without running evaluations."""
    return _check_optional_json_state(
        context.cache_root / "evaluations" / "baseline.json",
        check="evaluation-state",
        label="evaluation",
    )


def check_scheduler_state(context: SystemHealthContext) -> HealthResult:
    """Inspect the planned scheduler store without executing jobs."""
    return _check_optional_json_state(
        context.cache_root / "scheduler" / "jobs.json",
        check="scheduler-state",
        label="scheduler",
    )


def build_system_health_registry(context: SystemHealthContext) -> HealthRegistry:
    """Build the seven Second Self-only readiness checks in stable order."""
    registry = HealthRegistry()
    checks = (
        ("private-path-resolution", check_private_path_resolution),
        ("active-second-self-vault", check_active_second_self_vault),
        ("git-main-alignment", check_git_main_alignment),
        ("privacy-validator", check_privacy_validator),
        ("ollama-readiness", check_ollama_readiness),
        ("evaluation-state", check_evaluation_state),
        ("scheduler-state", check_scheduler_state),
    )
    for name, check in checks:
        registry.register(
            HealthCheck(name, lambda _fix, check=check: check(context))
        )
    return registry
