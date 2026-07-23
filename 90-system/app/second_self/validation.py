from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .frontmatter import read_note, validate_metadata
from .paths import SecondSelfPaths
from .scaffold import DIRECTORIES


SECRET_PATTERNS = {
    "OpenAI key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[opsu]_[A-Za-z0-9]{30,}\b"),
}
ABSOLUTE_USER_PATH = re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\")
IGNORED_TRACKED_PREFIXES = (
    "01-strategy-storage/",
    "02-skills-projects/projects/",
    ".second-self.local.json",
    ".second-self-cache/",
)
ALLOWED_PRIVATE_SCAFFOLD_FILES = {
    "01-strategy-storage/README.md",
    "01-strategy-storage/00 Memory/.gitkeep",
    "01-strategy-storage/01 Notes/.gitkeep",
    "01-strategy-storage/02 Journal/.gitkeep",
    "01-strategy-storage/03 Strategy/.gitkeep",
    "01-strategy-storage/04 References/.gitkeep",
    "01-strategy-storage/04 References/00 books/.gitkeep",
    "01-strategy-storage/04 References/01 quotes/.gitkeep",
    "01-strategy-storage/04 References/02 research/.gitkeep",
    "01-strategy-storage/04 References/03 guides/.gitkeep",
    "01-strategy-storage/04 References/04 docs/.gitkeep",
    "01-strategy-storage/05 Reviews/.gitkeep",
}


def _tracked_files(repo: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z"],
        check=False,
        capture_output=True,
    )
    if result.returncode:
        return []
    return [repo / value.decode("utf-8") for value in result.stdout.split(b"\0") if value]


def validate(
    paths: SecondSelfPaths, privacy: bool = False, check_private: bool = True
) -> list[str]:
    errors: list[str] = []
    if check_private:
        for relative in DIRECTORIES:
            if not (paths.data_root / relative).exists():
                errors.append(f"missing private directory: {relative}")

    private_notes = (
        paths.data_root.rglob("*.md")
        if check_private and paths.data_root.exists()
        else []
    )
    for note in private_notes:
        try:
            metadata, _ = read_note(note)
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{note}: unreadable metadata: {exc}")
            continue
        for error in validate_metadata(metadata):
            errors.append(f"{note.relative_to(paths.data_root)}: {error}")

    if privacy:
        for tracked in _tracked_files(paths.repo_root):
            relative = tracked.relative_to(paths.repo_root).as_posix()
            if (
                relative.startswith(IGNORED_TRACKED_PREFIXES)
                and relative not in ALLOWED_PRIVATE_SCAFFOLD_FILES
            ):
                errors.append(f"private/runtime path is tracked: {relative}")
                continue
            if not tracked.is_file() or tracked.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif"}:
                continue
            try:
                text = tracked.read_text(encoding="utf-8")
            except UnicodeError:
                continue
            for label, pattern in SECRET_PATTERNS.items():
                if pattern.search(text):
                    errors.append(f"{relative}: possible {label}")
            if ABSOLUTE_USER_PATH.search(text):
                errors.append(f"{relative}: contains an absolute user path")
    return errors
