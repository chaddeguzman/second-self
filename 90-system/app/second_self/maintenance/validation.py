from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ..core.frontmatter import read_note, validate_metadata
from ..core.paths import SecondSelfPaths
from ..core.scaffold import DIRECTORIES, PUBLIC_SCAFFOLD_PATHS
from ..maintenance.link_check import as_error_strings, check_wikilinks


SECRET_PATTERNS = {
    "OpenAI key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[opsu]_[A-Za-z0-9]{30,}\b"),
}
ABSOLUTE_USER_PATH = re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\")
IGNORED_TRACKED_PREFIXES = (
    "01-strategy-storage/",
    "02-skills-projects/projects/",
    "03-wiki/",
    ".second-self.local.json",
    ".second-self-schema",
    ".second-self-cache/",
)
ALLOWED_PRIVATE_SCAFFOLD_FILES = set(PUBLIC_SCAFFOLD_PATHS)


def _tracked_files(repo: Path) -> list[tuple[str, str, str]]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "--stage", "-z"],
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise RuntimeError(
            "privacy validation could not enumerate the Git index"
        ) from exc
    if result.returncode:
        raise RuntimeError("privacy validation could not enumerate the Git index")
    entries: list[tuple[str, str, str]] = []
    try:
        for value in result.stdout.split(b"\0"):
            if not value:
                continue
            metadata, raw_path = value.split(b"\t", 1)
            mode, object_id, _stage = metadata.decode("ascii").split(" ")
            entries.append((raw_path.decode("utf-8"), object_id, mode))
    except (UnicodeError, ValueError) as exc:
        raise RuntimeError(
            "privacy validation could not enumerate the Git index"
        ) from exc
    return entries


def _staged_blob(repo: Path, relative: str, object_id: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "blob", object_id],
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise RuntimeError(
            f"privacy validation could not read staged blob for {relative}"
        ) from exc
    if result.returncode:
        raise RuntimeError(
            f"privacy validation could not read staged blob for {relative}"
        )
    return result.stdout


def validate(
    paths: SecondSelfPaths,
    privacy: bool = False,
    check_private: bool = True,
    link_check: bool = False,
) -> list[str]:
    errors: list[str] = []
    if check_private:
        for relative in DIRECTORIES:
            if not (paths.data_root / relative).exists():
                errors.append(f"missing private directory: {relative}")
    if link_check:
        errors.extend(as_error_strings(check_wikilinks(paths)))

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
        try:
            tracked_files = _tracked_files(paths.repo_root)
        except RuntimeError as exc:
            errors.append(str(exc))
            return errors
        for relative, object_id, mode in tracked_files:
            if (
                relative.startswith(IGNORED_TRACKED_PREFIXES)
                and relative not in ALLOWED_PRIVATE_SCAFFOLD_FILES
            ):
                errors.append(f"private/runtime path is tracked: {relative}")
                continue
            if mode == "160000":
                continue
            if Path(relative).suffix.lower() in {".png", ".jpg", ".jpeg", ".gif"}:
                continue
            try:
                blob = _staged_blob(paths.repo_root, relative, object_id)
                text = blob.decode("utf-8")
            except RuntimeError as exc:
                errors.append(str(exc))
                continue
            except UnicodeError:
                continue
            for label, pattern in SECRET_PATTERNS.items():
                if pattern.search(text):
                    errors.append(f"{relative}: possible {label}")
            if ABSOLUTE_USER_PATH.search(text):
                errors.append(f"{relative}: contains an absolute user path")
    return errors
