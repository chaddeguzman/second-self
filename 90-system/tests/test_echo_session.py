"""Tests for the echo-session CLI (ECHO Session Manager)."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path("90-system/.echo/scripts/echo-session.py")


def run_cli(*args: str, base_dir: Path | None = None) -> tuple[int, str, str]:
    """Run the echo-session CLI and return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, str(SCRIPT)]
    if base_dir:
        cmd += ["--base-dir", str(base_dir)]
    cmd += list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
    return result.returncode, result.stdout, result.stderr


@pytest.fixture
def temp_base(tmp_path: Path) -> Path:
    """Create a temp directory mimicking the ECHO memory layout."""
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    (sessions / "2026-08-29T1600.md").write_text(
        "# Session 2026-08-29T1600\n\n"
        "## Session state\n\n"
        "turn_count: 10\n"
        "mode: text\n"
        "Initial session for testing\n"
    )
    (sessions / "2026-08-30T0900.md").write_text(
        "# Session 2026-08-30T0900\n\n"
        "## Session state\n\n"
        "turn_count: 3\n"
        "mode: voice\n"
        "Voice test session\n"
    )
    return tmp_path


# --- create ---

def test_create(temp_base: Path):
    code, out, err = run_cli("create", "--summary", "Test session", base_dir=temp_base)
    assert code == 0
    assert "Created session:" in out
    files = list((temp_base / "sessions").glob("*.md"))
    assert any(f.name for f in files)
    pointer = (temp_base / "current-session.md").read_text()
    assert "Active session:" in pointer


def test_create_no_summary_prompts(tmp_path: Path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--base-dir", str(tmp_path), "create"],
        input="My summary\n",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Created session:" in result.stdout


# --- list ---

def test_list(temp_base: Path):
    code, out, err = run_cli("list", base_dir=temp_base)
    assert code == 0
    assert "2026-08-29T1600" in out
    assert "2026-08-30T0900" in out
    assert "Total:" in out


def test_list_empty(tmp_path: Path):
    (tmp_path / "sessions").mkdir()
    code, out, err = run_cli("list", base_dir=tmp_path)
    assert code == 0
    assert "No sessions found." in out


def test_list_no_sessions_dir(tmp_path: Path):
    code, out, err = run_cli("list", base_dir=tmp_path)
    assert code == 0
    assert "No sessions directory found." in out


# --- resume ---

def test_resume(temp_base: Path):
    code, out, err = run_cli("resume", "2026-08-29T1600.md", base_dir=temp_base)
    assert code == 0
    assert "Resumed: 2026-08-29T1600.md" in out
    pointer = (temp_base / "current-session.md").read_text()
    assert "2026-08-29T1600.md" in pointer


def test_resume_missing(temp_base: Path):
    code, out, err = run_cli("resume", "nonexistent.md", base_dir=temp_base)
    assert code == 2
    assert "error" in err.lower()


# --- archive ---

def test_archive(temp_base: Path):
    code, out, err = run_cli("archive", "2026-08-29T1600.md", base_dir=temp_base)
    assert code == 0
    assert "Archived" in out
    assert (temp_base / "sessions" / "2026-08-29T1600.md.archived").exists()
    assert not (temp_base / "sessions" / "2026-08-29T1600.md").exists()


def test_archive_clears_pointer(temp_base: Path):
    run_cli("resume", "2026-08-29T1600.md", base_dir=temp_base)
    code, out, err = run_cli("archive", "2026-08-29T1600.md", base_dir=temp_base)
    assert code == 0
    assert "pointer cleared" in out.lower()


# --- summary ---

def test_summary_explicit(temp_base: Path):
    code, out, err = run_cli("summary", "2026-08-29T1600.md", base_dir=temp_base)
    assert code == 0
    assert "turn_count: 10" in out
    assert "mode: text" in out
    assert "Initial session for testing" in out


def test_summary_current(temp_base: Path):
    run_cli("resume", "2026-08-29T1600.md", base_dir=temp_base)
    code, out, err = run_cli("summary", base_dir=temp_base)
    assert code == 0
    assert "turn_count: 10" in out


def test_summary_no_current(tmp_path: Path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    (sessions / "2026-08-29T1600.md").write_text(
        "# Session 2026-08-29T1600\n\n## Session state\n\nturn_count: 5\nmode: text\nTest\n"
    )
    code, out, err = run_cli("summary", base_dir=tmp_path)
    assert code == 0
    assert "No current session" in out


# --- help subcommand ---

def test_help_subcommand():
    code, out, err = run_cli("help")
    assert code == 0
    assert "how to use it" in out
    assert "Worked examples:" in out
    assert "create --summary" in out
    assert "echo-session list" in out
    assert "echo-session resume" in out
    assert "echo-session archive" in out
    assert "echo-session summary" in out
    assert "SESSION-CONVENTION.md" in out
    assert "CAPABILITY-LIST.md" in out


# --- --help ---

def test_help():
    code, out, err = run_cli("--help")
    assert code == 0
    assert "echo-session" in out
    assert "create" in out
    assert "list" in out
    assert "resume" in out
    assert "archive" in out
    assert "summary" in out


def test_create_help():
    code, out, err = run_cli("create", "--help")
    assert code == 0
    assert "summary" in out
