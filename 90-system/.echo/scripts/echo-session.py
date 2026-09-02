#!/usr/bin/env python3
"""
echo-session — ECHO Session Manager CLI

A simple command-line tool for managing ECHO's session files.
Operates on memory/sessions/ and manages the current-session.md pointer.

Usage:
    echo-session create [--summary "text"]
    echo-session list
    echo-session resume <file>
    echo-session archive <file>
    echo-session summary [file]

All paths default to 90-system/.echo/memory/ but can be overridden with
--base-dir.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def _default_base_dir() -> Path:
    """Return the default ECHO memory directory."""
    # Resolve relative to this script's location so it works from any CWD
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent.parent / "memory"


def _sessions_dir(base_dir: Path) -> Path:
    return base_dir / "sessions"


def _pointer_file(base_dir: Path) -> Path:
    return base_dir / "current-session.md"


def _resolve_session_path(sessions_dir: Path, name: str) -> Path:
    """Resolve a session file name to a full path, validating it exists."""
    path = sessions_dir / name
    if not path.exists():
        raise FileNotFoundError(f"Session not found: {name}")
    return path


# ---------------------------------------------------------------------------
# Session file I/O
# ---------------------------------------------------------------------------

# Matches: YYYY-MM-DDTHHMM
SESSION_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{4}\.md$")


def _session_filename() -> str:
    """Generate a session filename using the current date/time."""
    now = datetime.now()
    return now.strftime("%Y-%m-%dT%H%M.md")


def _session_header(filename: str) -> str:
    """Extract the human-readable session name from a filename."""
    # 2026-08-29T1600.md -> 2026-08-29T1600
    return filename.rsplit(".", 1)[0]


def _write_session_file(path: Path, summary: str, turn_count: int = 0) -> None:
    """Write a new session file following the SESSION-CONVENTION.md format."""
    name = _session_header(path.name)
    content = (
        f"# Session {name}\n"
        f"\n"
        f"## Session state\n"
        f"\n"
        f"turn_count: {turn_count}\n"
        f"mode: text\n"
        f"{summary}\n"
    )
    path.write_text(content, encoding="utf-8")


def _update_pointer(pointer: Path, session_name: str) -> None:
    """Write the current-session.md pointer file."""
    content = f"# Current Session Pointer\n\nActive session: `{session_name}`\n"
    pointer.write_text(content, encoding="utf-8")


def _read_pointer(pointer: Path) -> str | None:
    """Read the pointer file and return the session name, or None."""
    if not pointer.exists():
        return None
    text = pointer.read_text(encoding="utf-8")
    # Active session: `2026-08-29T1600.md`
    match = re.search(r"`([^`]+)`", text)
    return match.group(1) if match else None


def _parse_session_state(path: Path) -> dict[str, str]:
    """Parse the '## Session state' block from a session file."""
    text = path.read_text(encoding="utf-8")
    # Find the session state section
    lines = text.splitlines()
    state: dict[str, str] = {}
    in_state = False
    summary_lines: list[str] = []

    for line in lines:
        if line.strip() == "## Session state":
            in_state = True
            continue
        if in_state:
            if line.startswith("## ") and "Session state" not in line:
                # End of session state section
                in_state = False
                break
            stripped = line.strip()
            if stripped.startswith("turn_count:"):
                state["turn_count"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("mode:"):
                state["mode"] = stripped.split(":", 1)[1].strip()
            elif stripped and not stripped.startswith("turn_count:") and not stripped.startswith("mode:"):
                summary_lines.append(stripped)

    state["summary"] = " ".join(summary_lines) if summary_lines else ""
    return state


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_create(args: argparse.Namespace) -> int:
    """Create a new session file and point the pointer at it."""
    base = Path(args.base_dir) if args.base_dir else _default_base_dir()
    sessions = _sessions_dir(base)
    sessions.mkdir(parents=True, exist_ok=True)

    summary = args.summary or input("Session summary: ").strip()
    if not summary:
        summary = "New session"

    filename = _session_filename()
    path = sessions / filename

    if path.exists():
        print(f"error: session file already exists: {filename}", file=sys.stderr)
        return 2

    _write_session_file(path, summary, turn_count=0)
    _update_pointer(_pointer_file(base), filename)

    print(f"Created session: {filename}")
    print(f"Summary: {summary}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List all sessions with their state headers."""
    base = Path(args.base_dir) if args.base_dir else _default_base_dir()
    sessions = _sessions_dir(base)

    if not sessions.exists():
        print("No sessions directory found.")
        return 0

    current = _read_pointer(_pointer_file(base))

    # Collect session files (exclude convention docs)
    files = sorted(
        f for f in sessions.iterdir()
        if f.is_file() and SESSION_FILENAME_RE.match(f.name)
    )

    if not files:
        print("No sessions found.")
        return 0

    print(f"{'NAME':<22} {'TURNS':>6}  {'MODE':<6} {'CURRENT':<8} SUMMARY")
    print("-" * 80)
    for f in files:
        state = _parse_session_state(f)
        is_current = "← current" if f.name == current else ""
        print(
            f"{f.stem:<22} {state.get('turn_count', '?'):>6}  "
            f"{state.get('mode', '?'):<6} {is_current:<8} {state.get('summary', '')[:30]}"
        )

    print(f"\nTotal: {len(files)} session(s)")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    """Point current-session.md at an existing session file."""
    base = Path(args.base_dir) if args.base_dir else _default_base_dir()
    sessions = _sessions_dir(base)

    path = _resolve_session_path(sessions, args.file)
    _update_pointer(_pointer_file(base), args.file)

    state = _parse_session_state(path)
    print(f"Resumed: {args.file}")
    print(f"  turns: {state.get('turn_count', '?')}")
    print(f"  mode:  {state.get('mode', '?')}")
    if state.get("summary"):
        print(f"  summary: {state['summary']}")
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    """Rename a session file with .archived suffix to preserve it."""
    base = Path(args.base_dir) if args.base_dir else _default_base_dir()
    sessions = _sessions_dir(base)

    path = _resolve_session_path(sessions, args.file)
    archived_name = args.file + ".archived"
    archived_path = sessions / archived_name

    if archived_path.exists():
        print(f"error: archive target already exists: {archived_name}", file=sys.stderr)
        return 2

    path.rename(archived_path)
    print(f"Archived: {args.file} -> {archived_name}")

    # If we archived the current session, clear the pointer
    current = _read_pointer(_pointer_file(base))
    if current == args.file:
        _update_pointer(_pointer_file(base), "(none)")
        print("  Note: current-session.md pointer cleared.")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """Print the session state header for a session (default: current)."""
    base = Path(args.base_dir) if args.base_dir else _default_base_dir()
    sessions = _sessions_dir(base)
    pointer = _pointer_file(base)

    if args.file:
        path = _resolve_session_path(sessions, args.file)
    else:
        current = _read_pointer(pointer)
        if not current:
            print("No current session. Specify one with: echo-session summary <file>")
            return 0
        path = _resolve_session_path(sessions, current)

    state = _parse_session_state(path)
    print(f"# Session {path.stem}")
    print(f"turn_count: {state.get('turn_count', '?')}")
    print(f"mode: {state.get('mode', '?')}")
    print(f"summary: {state.get('summary', '(none)')}")
    return 0


# ---------------------------------------------------------------------------
# CLI setup
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="echo-session",
        description="Manage ECHO session files.",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        help="Override the ECHO memory base directory (default: auto-detected)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create", help="Start a new session")
    p_create.add_argument("--summary", default="", help="One-line summary of the session")
    p_create.set_defaults(func=cmd_create)

    p_list = sub.add_parser("list", help="List all sessions")
    p_list.set_defaults(func=cmd_list)

    p_resume = sub.add_parser("resume", help="Resume an existing session")
    p_resume.add_argument("file", help="Session file name (e.g. 2026-08-29T1600.md)")
    p_resume.set_defaults(func=cmd_resume)

    p_archive = sub.add_parser("archive", help="Archive a session (rename to .archived)")
    p_archive.add_argument("file", help="Session file name to archive")
    p_archive.set_defaults(func=cmd_archive)

    p_summary = sub.add_parser("summary", help="Show session state header")
    p_summary.add_argument("file", nargs="?", default=None, help="Session file name (default: current)")
    p_summary.set_defaults(func=cmd_summary)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (FileNotFoundError, FileExistsError, PermissionError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
