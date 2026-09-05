"""Tests for the echo-doctor CLI (ECHO System Health Check)."""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("90-system/.echo/scripts/echo-doctor.py")


def run_cli(*args: str, base_dir: Path | None = None) -> tuple[int, str, str]:
    """Run the echo-doctor CLI and return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, str(SCRIPT)]
    if base_dir:
        cmd += ["--base-dir", str(base_dir)]
    cmd += list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
    return result.returncode, result.stdout, result.stderr


def make_base(tmp_path: Path) -> Path:
    """Create a temp .echo layout that passes all checks."""
    (tmp_path / "subagents").mkdir()
    (tmp_path / "memory" / "sessions").mkdir(parents=True)
    (tmp_path / "memory" / "staging").mkdir(parents=True)
    for f in [
        "IDENTITY.md",
        "STABLE_BLOCK.md",
        "RECALL.md",
        "MEMORY-TOOLS.md",
        "CAPABILITIES.md",
        "CAPABILITY-LIST.md",
    ]:
        (tmp_path / f).write_text("test\n", encoding="utf-8")
    (tmp_path / "subagents" / "README.md").write_text("test\n", encoding="utf-8")
    (tmp_path / "subagents" / "charlie").mkdir()
    (tmp_path / "subagents" / "charlie" / "log.md").write_text(
        "# Charlie \u2014 Status: Idle\n\n| Date |\n|------|\n",
        encoding="utf-8",
    )
    return tmp_path


# --- all-OK case ---

def test_all_ok(tmp_path: Path):
    base = make_base(tmp_path)
    code, out, err = run_cli(base_dir=base)
    assert code == 0
    assert "[FAIL]" not in out
    assert "[WARN]" not in out
    assert "Summary: 6 OK" in out


# --- check 1: stable-block files ---

def test_missing_stable_block_file_fails(tmp_path: Path):
    base = make_base(tmp_path)
    (base / "IDENTITY.md").unlink()
    code, out, err = run_cli(base_dir=base)
    assert code == 2
    assert "[FAIL]" in out
    assert "IDENTITY.md" in out


# --- check 2: session pointer ---

def test_pointer_at_none_is_ok(tmp_path: Path):
    base = make_base(tmp_path)
    pointer = base / "memory" / "current-session.md"
    pointer.write_text("# Current Session Pointer\n\nActive session: **(none)**\n", encoding="utf-8")
    code, out, err = run_cli(base_dir=base)
    assert code == 0
    assert "no active session" in out


def test_pointer_to_missing_session_fails(tmp_path: Path):
    base = make_base(tmp_path)
    pointer = base / "memory" / "current-session.md"
    pointer.write_text("Active session: `2026-01-01T0000.md`\n", encoding="utf-8")
    code, out, err = run_cli(base_dir=base)
    assert code == 2
    assert "missing session" in out


def test_pointer_to_existing_session_ok(tmp_path: Path):
    base = make_base(tmp_path)
    (base / "memory" / "sessions" / "2026-01-01T0000.md").write_text("x\n", encoding="utf-8")
    pointer = base / "memory" / "current-session.md"
    pointer.write_text("Active session: `2026-01-01T0000.md`\n", encoding="utf-8")
    code, out, err = run_cli(base_dir=base)
    assert code == 0
    assert "points at 2026-01-01T0000.md" in out


# --- check 3: staging queue ---

def test_staging_over_limit_warns(tmp_path: Path):
    base = make_base(tmp_path)
    staging = base / "memory" / "staging"
    for i in range(11):
        (staging / f"memory-{i}.md").write_text("x\n", encoding="utf-8")
    code, out, err = run_cli(base_dir=base)
    assert code == 0  # WARN without --strict
    assert "[WARN]" in out
    assert "11 files pending" in out


def test_staging_over_limit_strict_exits_1(tmp_path: Path):
    base = make_base(tmp_path)
    staging = base / "memory" / "staging"
    for i in range(11):
        (staging / f"memory-{i}.md").write_text("x\n", encoding="utf-8")
    code, out, err = run_cli("--strict", base_dir=base)
    assert code == 1


# --- check 4: log status lines ---

def test_malformed_status_line_warns(tmp_path: Path):
    base = make_base(tmp_path)
    log = base / "subagents" / "charlie" / "log.md"
    log.write_text("# Agent 01 — Task Log\n", encoding="utf-8")
    code, out, err = run_cli(base_dir=base)
    assert code == 0
    assert "malformed status line" in out
    assert "charlie" in out


# --- check 5: stale wip.md ---

def test_stale_wip_warns_and_fix_removes(tmp_path: Path):
    base = make_base(tmp_path)
    log = base / "subagents" / "charlie" / "log.md"
    log.write_text(
        "# Charlie \u2014 Status: Done\n\n| Date | Time | Request | Status |\n"
        "|------|------|---------|--------|\n"
        "| 2026-09-04 | 10:00 | Build thing | Done |\n",
        encoding="utf-8",
    )
    wip = base / "subagents" / "charlie" / "wip.md"
    wip.write_text("# WIP: Build thing\n", encoding="utf-8")

    # Without --fix: WARN
    code, out, err = run_cli(base_dir=base)
    assert code == 0
    assert "stale wip.md" in out
    assert wip.exists()

    # With --fix: removed
    code, out, err = run_cli("--fix", base_dir=base)
    assert code == 0
    assert "removed stale wip.md" in out
    assert not wip.exists()


def test_active_wip_not_flagged(tmp_path: Path):
    base = make_base(tmp_path)
    log = base / "subagents" / "charlie" / "log.md"
    log.write_text(
        "# Charlie \u2014 Status: Working\n\n| Date | Time | Request | Status |\n"
        "|------|------|---------|--------|\n"
        "| 2026-09-04 | 10:00 | Build thing | In Progress |\n",
        encoding="utf-8",
    )
    (base / "subagents" / "charlie" / "wip.md").write_text("# WIP: Build thing\n", encoding="utf-8")
    code, out, err = run_cli(base_dir=base)
    assert code == 0
    assert "no stale wip.md" in out


# --- check 6: session filenames ---

def test_convention_doc_not_flagged(tmp_path: Path):
    base = make_base(tmp_path)
    (base / "memory" / "sessions" / "SESSION-CONVENTION.md").write_text("doc\n", encoding="utf-8")
    code, out, err = run_cli(base_dir=base)
    assert code == 0
    assert "all conforming" in out


def test_archived_sessions_counted(tmp_path: Path):
    base = make_base(tmp_path)
    (base / "memory" / "sessions" / "2026-01-01T0000.md.archived").write_text("x\n", encoding="utf-8")
    code, out, err = run_cli(base_dir=base)
    assert code == 0
    assert "1 archived" in out


def test_bad_session_name_warns(tmp_path: Path):
    base = make_base(tmp_path)
    (base / "memory" / "sessions" / "not-a-session.txt").write_text("x\n", encoding="utf-8")
    code, out, err = run_cli(base_dir=base)
    assert code == 0
    assert "non-conforming" in out


# --- output modes ---

def test_json_output(tmp_path: Path):
    base = make_base(tmp_path)
    code, out, err = run_cli("--json", base_dir=base)
    assert code == 0
    data = json.loads(out)
    assert len(data["results"]) == 6
    assert all(r["status"] == "OK" for r in data["results"])


def test_strict_all_ok_exits_0(tmp_path: Path):
    base = make_base(tmp_path)
    code, out, err = run_cli("--strict", base_dir=base)
    assert code == 0