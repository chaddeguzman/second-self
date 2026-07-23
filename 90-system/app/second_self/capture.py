from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .frontmatter import read_note, validate_metadata
from .paths import SecondSelfPaths


MAX_TITLE_LENGTH = 120
MAX_BODY_LENGTH = 100 * 1024


@dataclass(frozen=True)
class CapturedNote:
    path: Path
    title: str
    created_at: datetime


def _safe_filename(value: str) -> str:
    cleaned = "".join(
        character if character not in '<>:"/\\|?*' and ord(character) >= 32 else "-"
        for character in value
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned[:80] or "Capture"


def _validate(title: str, body: str, require_body: bool) -> tuple[str, str]:
    title = title.strip()
    if not title:
        raise ValueError("Title is required.")
    if "\n" in title or "\r" in title:
        raise ValueError("Title must be a single line.")
    if len(title) > MAX_TITLE_LENGTH:
        raise ValueError(f"Title must be {MAX_TITLE_LENGTH} characters or fewer.")
    if require_body and not body.strip():
        raise ValueError("Body is required.")
    if len(body.encode("utf-8")) > MAX_BODY_LENGTH:
        raise ValueError(f"Body must be {MAX_BODY_LENGTH // 1024} KiB or smaller.")
    return title, body


def capture_note(
    paths: SecondSelfPaths,
    title: str,
    body: str = "",
    *,
    source: str = "cli",
    require_body: bool = False,
    now: datetime | None = None,
) -> CapturedNote:
    title, body = _validate(title, body, require_body)
    created_at = (now or datetime.now().astimezone()).replace(microsecond=0)
    inbox = paths.layer1 / "00-inbox"
    inbox.mkdir(parents=True, exist_ok=True)

    content = (
        "---\n"
        "type: capture\n"
        f"created: {created_at.date().isoformat()}\n"
        f"captured_at: {json.dumps(created_at.isoformat())}\n"
        "status: inbox\n"
        f"source: {json.dumps(source)}\n"
        "tags: []\n"
        "projects: []\n"
        "related: []\n"
        "---\n\n"
        f"# {title}\n\n"
        f"{body}"
    )
    if not content.endswith("\n"):
        content += "\n"

    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=".capture-",
            suffix=".tmp",
            dir=inbox,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())

        stem = f"{created_at:%Y-%m-%d %H%M%S} - {_safe_filename(title)}"
        final: Path | None = None
        for _ in range(20):
            candidate = inbox / f"{stem} - {secrets.token_hex(4)}.md"
            try:
                os.link(temporary, candidate)
            except FileExistsError:
                continue
            final = candidate
            break
        if final is None:
            raise RuntimeError("Could not allocate a unique capture filename.")

        temporary.unlink()
        temporary = None
        try:
            if final.read_text(encoding="utf-8") != content:
                raise RuntimeError("Capture verification failed.")
            metadata, _ = read_note(final)
            errors = validate_metadata(metadata)
            if errors:
                raise RuntimeError("Capture metadata verification failed.")
        except Exception:
            final.unlink(missing_ok=True)
            raise
        return CapturedNote(final, title, created_at)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
