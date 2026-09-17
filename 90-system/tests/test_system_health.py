"""Hermetic tests for Second Self-only readiness checks."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from second_self.health import FAIL, OK, WARN
from second_self.health.system import (
    SystemHealthContext,
    build_system_health_registry,
    check_active_second_self_vault,
    check_evaluation_state,
    check_git_main_alignment,
    check_ollama_readiness,
    check_privacy_validator,
    check_private_path_resolution,
    check_scheduler_state,
    check_semantic_readiness,
)
from second_self.providers import ProviderHealth, ProviderHealthStatus


def completed(stdout: str = "", returncode: int = 0):
    return subprocess.CompletedProcess([], returncode, stdout, "")


def make_context(tmp_path: Path, **overrides) -> SystemHealthContext:
    values = {
        "repo_root": tmp_path,
        "config_path": tmp_path / ".second-self.local.json",
        "git_runner": lambda args, _cwd: completed(
            "main\n" if args[0] == "symbolic-ref" else "0\t0\n"
        ),
        "ollama_health": lambda _config: ProviderHealth(
            ProviderHealthStatus.READY, "Ollama provider ready"
        ),
    }
    values.update(overrides)
    return SystemHealthContext(**values)


def write_valid_config(context: SystemHealthContext) -> None:
    private = context.repo_root / "private"
    private.mkdir()
    context.config_path.write_text(
        json.dumps({"schema_version": 1, "data_root": str(private)}),
        encoding="utf-8",
    )


@pytest.mark.parametrize("content", [None, "not json", "{}", '{"data_root": 3}'])
def test_private_path_missing_or_invalid_is_fail(tmp_path, content):
    context = make_context(tmp_path)
    if content is not None:
        context.config_path.write_text(content, encoding="utf-8")

    result = check_private_path_resolution(context)

    assert result.status == FAIL
    assert str(tmp_path) not in result.detail


def test_private_path_valid_is_ok(tmp_path):
    context = make_context(tmp_path)
    write_valid_config(context)

    assert check_private_path_resolution(context).status == OK


def test_active_vault_requires_only_second_self_markers(tmp_path):
    context = make_context(tmp_path)
    assert check_active_second_self_vault(context).status == FAIL

    (tmp_path / ".obsidian").mkdir()
    (tmp_path / "AGENTS.md").write_text("rules", encoding="utf-8")
    (tmp_path / "Start-Second-Self.cmd").write_text("start", encoding="utf-8")

    assert check_active_second_self_vault(context).status == OK


@pytest.mark.parametrize(
    ("branch", "alignment", "expected"),
    [
        (completed("main\n"), completed("0\t0\n"), OK),
        (completed("feature\n"), completed("0\t0\n"), FAIL),
        (completed("", 1), completed("0\t0\n"), FAIL),
        (completed("main\n"), completed("1\t0\n"), FAIL),
        (completed("main\n"), completed("", 1), FAIL),
    ],
)
def test_git_branch_and_alignment(tmp_path, branch, alignment, expected):
    def git_runner(args, _cwd):
        return branch if args[0] == "symbolic-ref" else alignment

    result = check_git_main_alignment(make_context(tmp_path, git_runner=git_runner))

    assert result.status == expected


def test_git_exception_is_redacted_fail(tmp_path):
    def broken_git(_args, _cwd):
        raise OSError(f"failed in {tmp_path}")

    result = check_git_main_alignment(make_context(tmp_path, git_runner=broken_git))

    assert result.status == FAIL
    assert str(tmp_path) not in result.detail


def test_privacy_validator_is_required(tmp_path):
    context = make_context(tmp_path)
    assert check_privacy_validator(context).status == FAIL

    validator = tmp_path / "90-system" / "automation" / "scripts" / "second-self.ps1"
    validator.parent.mkdir(parents=True)
    validator.write_text("# validator", encoding="utf-8")

    assert check_privacy_validator(context).status == OK


def test_ollama_ready_and_offline_are_bounded(tmp_path):
    ready = make_context(tmp_path)
    assert check_ollama_readiness(ready).status == OK

    def offline(_config):
        raise OSError(f"offline at {tmp_path}")

    result = check_ollama_readiness(make_context(tmp_path, ollama_health=offline))
    assert result.status == WARN
    assert str(tmp_path) not in result.detail


def test_semantic_readiness_reports_optional_index_without_loading_model(tmp_path):
    context = make_context(tmp_path)
    write_valid_config(context)
    result = check_semantic_readiness(context)
    assert result.status == WARN
    assert "keyword fallback" in result.detail
    assert str(tmp_path) not in result.detail


@pytest.mark.parametrize(
    ("checker", "relative"),
    [
        (check_scheduler_state, Path("scheduler/jobs.json")),
    ],
)
def test_optional_state_absent_invalid_and_valid(tmp_path, checker, relative):
    context = make_context(tmp_path)
    state = context.cache_root / relative
    assert checker(context).status == WARN

    state.parent.mkdir(parents=True)
    state.write_text("invalid", encoding="utf-8")
    invalid = checker(context)
    assert invalid.status == WARN
    assert str(tmp_path) not in invalid.detail

    state.write_text('{"schema_version": 1}', encoding="utf-8")
    assert checker(context).status == OK


def test_evaluation_state_requires_a_compatible_tracked_baseline(tmp_path):
    context = make_context(tmp_path)
    baseline = tmp_path / "90-system" / "evaluation-baseline.json"
    assert check_evaluation_state(context).status == WARN

    baseline.parent.mkdir(parents=True)
    baseline.write_text("invalid private path details", encoding="utf-8")
    invalid = check_evaluation_state(context)
    assert invalid.status == WARN
    assert str(tmp_path) not in invalid.detail

    source = Path("90-system/evaluation-baseline.json")
    baseline.write_bytes(source.read_bytes())
    valid = check_evaluation_state(context)
    assert valid.status == OK
    assert valid.detail == "evaluation baseline is compatible"


def test_system_registry_has_exact_order_and_read_only_fix_behavior(tmp_path):
    context = make_context(tmp_path)
    registry = build_system_health_registry(context)

    assert [check.name for check in registry] == [
        "private-path-resolution",
        "active-second-self-vault",
        "git-main-alignment",
        "privacy-validator",
        "ollama-readiness",
        "semantic-readiness",
        "evaluation-state",
        "scheduler-state",
    ]
    assert all(not check.supports_fix for check in registry)
