from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .frontmatter import read_note, validate_metadata
from .paths import SecondSelfPaths


MAX_TITLE_LENGTH = 120
MAX_BODY_LENGTH = 100 * 1024


@dataclass(frozen=True)
class JournalEntry:
    path: Path
    entry_date: date
    appended: bool


def _validate(body: str, title: str) -> tuple[str, str]:
    body = body.strip()
    if not body:
        raise ValueError("Body is required.")
    if len(body.encode("utf-8")) > MAX_BODY_LENGTH:
        raise ValueError(f"Body must be {MAX_BODY_LENGTH // 1024} KiB or smaller.")
    title = title.strip()
    if title:
        if "\n" in title or "\r" in title:
            raise ValueError("Title must be a single line.")
        if len(title) > MAX_TITLE_LENGTH:
            raise ValueError(f"Title must be {MAX_TITLE_LENGTH} characters or fewer.")
    return body, title


def _template(entry_date: date) -> str:
    return (
        "---\n"
        "type: journal\n"
        f"created: {entry_date.isoformat()}\n"
        "status: active\n"
        "tags: []\n"
        "projects: []\n"
        "related: []\n"
        "---\n\n"
        f"# {entry_date.isoformat()}\n\n"
        "## Notes\n\n"
        "## Decisions\n\n"
        "## Lessons\n"
    )


def _append_under_notes(text: str, body: str, title: str) -> str:
    """Append body (optionally under a ### title heading) under the ## Notes section."""
    if not text.endswith("\n"):
        text += "\n"
    heading = f"### {title}\n\n" if title else ""
    block = f"{heading}{body}\n"
    lines = text.splitlines(keepends=True)
    notes_index: int | None = None
    next_heading: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "## Notes":
            notes_index = index
        elif notes_index is not None and stripped.startswith("## "):
            next_heading = index
            break
    if notes_index is None:
        if not text.endswith("\n"):
            text += "\n"
        return text + "\n## Notes\n\n" + block
    if next_heading is None:
        return text + block
    insert_at = next_heading
    while insert_at > notes_index + 1 and not lines[insert_at - 1].strip():
        insert_at -= 1
    return "".join(lines[:insert_at]) + block + "".join(lines[insert_at:])


def journal_entry(
    paths: SecondSelfPaths,
    body: str,
    *,
    title: str = "",
    now: datetime | None = None,
) -> JournalEntry:
    body, title = _validate(body, title)
    created_at = (now or datetime.now().astimezone()).replace(microsecond=0)
    entry_date = created_at.date()
    journal_dir = paths.layer1 / "02 Journal"
    journal_dir.mkdir(parents=True, exist_ok=True)
    target = journal_dir / f"{entry_date.isoformat()} - Journal.md"

    if target.exists():
        existing = target.read_text(encoding="utf-8")
        content = _append_under_notes(existing, body, title)
        appended = True
    else:
        content = _template(entry_date)
        content = _append_under_notes(content, body, title)
        appended = False
    if not content.endswith("\n"):
        content += "\n"

    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=".journal-",
            suffix=".tmp",
            dir=journal_dir,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temporary, target)
        temporary = None
        try:
            if target.read_text(encoding="utf-8") != content:
                raise RuntimeError("Journal verification failed.")
            metadata, _ = read_note(target)
            errors = validate_metadata(metadata)
            if errors:
                raise RuntimeError("Journal metadata verification failed.")
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return JournalEntry(target, entry_date, appended)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()