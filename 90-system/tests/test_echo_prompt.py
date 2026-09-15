"""Tier 1-2 tests for the portable ECHO prompt and Codex adapter."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "90-system" / ".echo" / "runtime" / "prompt.py"
HOOK = ROOT / ".codex" / "echo_prompt_hook.py"

SPEC = importlib.util.spec_from_file_location("echo_prompt_runtime", SCRIPT)
assert SPEC and SPEC.loader
prompt_runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = prompt_runtime
SPEC.loader.exec_module(prompt_runtime)


def _make_repo(tmp_path: Path, *, identity: bytes | None = None, skill: str | None = None) -> Path:
    identity_path = tmp_path / "90-system" / ".echo" / "IDENTITY.md"
    skill_path = tmp_path / "02-skills-projects" / "skills" / "echo" / "SKILL.md"
    identity_path.parent.mkdir(parents=True)
    skill_path.parent.mkdir(parents=True)
    identity_path.write_bytes(identity or b"# ECHO \xe2\x80\x94 Identity\r\nALPHA\r\n")
    skill_path.write_text(
        skill or "---\nname: echo\ndescription: test\n---\n\n# Rules\nKeep evidence honest.\n",
        encoding="utf-8",
        newline="",
    )
    return tmp_path


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("$echo find the note", "explicit-echo"),
        ("Echo: where is it?", "explicit-echo"),
        ("Echo, recall this", "explicit-echo"),
        ("Echo find my decision", "explicit-echo"),
        ("I remember a line about courage", "remember-fragment"),
        ("I had an idea about a study system", "past-idea"),
        ("find what I wrote about sleep", "find-my-writing"),
        ("what did I decide about the move?", "past-decision"),
    ],
)
def test_activation_matches_explicit_and_recall_cues(text: str, reason: str) -> None:
    assert prompt_runtime.activation_reason(text) == reason


@pytest.mark.parametrize(
    "text",
    [
        "echo hello",
        "Run `echo hello` in PowerShell",
        "Rename echo_server to audio_server",
        "Fix the EchoClient class",
        "Implement the parser",
        "",
    ],
)
def test_activation_avoids_false_positives(text: str) -> None:
    assert prompt_runtime.activation_reason(text) is None


def test_stable_order_and_identity_bytes_are_preserved(tmp_path: Path) -> None:
    identity = b"# ECHO \xe2\x80\x94 Identity\r\nALPHA\r\nsecond line"
    repo = _make_repo(tmp_path, identity=identity)
    bundle = prompt_runtime.render_context(repo_root=repo)
    decoded_identity = identity.decode("utf-8")

    assert decoded_identity in bundle.text
    assert bundle.text.index("### Identity") < bundle.text.index("### Operating rules")
    assert bundle.text.index("### Operating rules") < bundle.text.index("### Deferred stable slots")
    assert "Tier 3 core knowledge: not loaded" in bundle.text
    assert "Tier 8 generated capabilities: not loaded" in bundle.text


def test_stable_fingerprint_ignores_dynamic_timestamp(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    first = prompt_runtime.render_context(
        repo_root=repo, now=datetime.fromisoformat("2026-09-15T10:00:00+08:00")
    )
    second = prompt_runtime.render_context(
        repo_root=repo, now=datetime.fromisoformat("2026-09-15T10:01:00+08:00")
    )

    assert first.stable_fingerprint == second.stable_fingerprint
    assert first.text != second.text


def test_identity_change_is_seen_without_module_restart(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    first = prompt_runtime.render_context(repo_root=repo)
    identity_path = repo / "90-system" / ".echo" / "IDENTITY.md"
    identity_path.write_bytes(b"# ECHO \xe2\x80\x94 Identity\nBETA\n")
    second = prompt_runtime.render_context(repo_root=repo)

    assert "ALPHA" in first.text and "BETA" not in first.text
    assert "BETA" in second.text and "ALPHA" not in second.text
    assert first.stable_fingerprint != second.stable_fingerprint


@pytest.mark.parametrize(
    ("missing", "expected_code"),
    [("IDENTITY.md", "source-unavailable"), ("SKILL.md", "source-unavailable")],
)
def test_missing_sources_fail_safely(tmp_path: Path, missing: str, expected_code: str) -> None:
    repo = _make_repo(tmp_path)
    next(repo.rglob(missing)).unlink()
    with pytest.raises(prompt_runtime.EchoContextError) as error:
        prompt_runtime.render_context(repo_root=repo)
    assert error.value.code == expected_code


def test_unreadable_source_fails_safely(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _make_repo(tmp_path)
    original = Path.read_bytes

    def denied(path: Path) -> bytes:
        if path.name == "IDENTITY.md":
            raise PermissionError("private absolute detail")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", denied)
    with pytest.raises(prompt_runtime.EchoContextError) as error:
        prompt_runtime.render_context(repo_root=repo)
    assert error.value.code == "source-unavailable"
    safe = prompt_runtime.failure_context(error.value)
    assert str(repo) not in safe
    assert "private absolute detail" not in safe


@pytest.mark.parametrize(
    ("identity", "skill", "expected_code"),
    [
        (b"", None, "source-empty"),
        (b"wrong identity", None, "identity-invalid"),
        (None, "not yaml", "skill-invalid"),
    ],
)
def test_empty_or_malformed_sources_fail(
    tmp_path: Path, identity: bytes | None, skill: str | None, expected_code: str
) -> None:
    repo = _make_repo(tmp_path)
    if identity is not None:
        (repo / "90-system" / ".echo" / "IDENTITY.md").write_bytes(identity)
    if skill is not None:
        (repo / "02-skills-projects" / "skills" / "echo" / "SKILL.md").write_text(
            skill, encoding="utf-8"
        )
    with pytest.raises(prompt_runtime.EchoContextError) as error:
        prompt_runtime.render_context(repo_root=repo)
    assert error.value.code == expected_code


def test_oversized_source_is_rejected(tmp_path: Path) -> None:
    huge_skill = "---\nname: echo\ndescription: test\n---\n" + ("x" * 9_000)
    repo = _make_repo(tmp_path, skill=huge_skill)
    with pytest.raises(prompt_runtime.EchoContextError) as error:
        prompt_runtime.render_context(repo_root=repo)
    assert error.value.code == "context-too-large"


def test_unrelated_private_and_later_tier_files_are_never_read(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    forbidden = "FORBIDDEN_PRIVATE_MARKER"
    for relative in (
        "90-system/.echo/CORE_KNOWLEDGE.md",
        "90-system/.echo/CAPABILITIES.md",
        "90-system/.echo/memory/store.jsonl",
        "01-strategy-storage/00 Memory/private.md",
        ".env",
    ):
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(forbidden, encoding="utf-8")
    bundle = prompt_runtime.render_context(repo_root=repo)
    assert forbidden not in bundle.text


def test_real_context_is_within_budget_and_identity_is_complete() -> None:
    bundle = prompt_runtime.render_context(repo_root=ROOT)
    identity = (ROOT / "90-system" / ".echo" / "IDENTITY.md").read_bytes().decode("utf-8")
    assert identity in bundle.text
    assert bundle.byte_count == len(bundle.text.encode("utf-8"))
    assert bundle.byte_count <= 8_000


def _run_hook(prompt: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"prompt": prompt}),
        text=True,
        capture_output=True,
        cwd=ROOT,
        check=False,
    )


def test_hook_emits_nothing_for_unmatched_prompt() -> None:
    result = _run_hook("Please fix the parser")
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_hook_emits_codex_user_prompt_context() -> None:
    result = _run_hook("$echo find what I wrote")
    payload = json.loads(result.stdout)
    hook_output = payload["hookSpecificOutput"]
    assert result.returncode == 0
    assert hook_output["hookEventName"] == "UserPromptSubmit"
    assert "<ECHO_CONTEXT_V1>" in hook_output["additionalContext"]


def test_hooks_keep_protection_and_add_echo() -> None:
    config = json.loads((ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    assert "PreToolUse" in config["hooks"]
    assert "UserPromptSubmit" in config["hooks"]
    assert "pre_tool_use.py" in config["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert "echo_prompt_hook.py" in config["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
