from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def _deny(reason: str) -> None:
    # Codex accepts this compatibility shape; Claude also understands it.
    print(json.dumps({"decision": "block", "reason": reason}))


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError):
        return
    text = json.dumps(event.get("tool_input", {}), ensure_ascii=False)
    lower = text.lower().replace("/", "\\")
    data_root = os.environ.get("SECOND_SELF_DATA", str(Path.home() / "SecondSelfData"))
    private_markers = [
        data_root.lower().replace("/", "\\"),
        "01-strategy-storage",
        "02-skills-projects\\projects",
    ]
    if not any(marker in lower for marker in private_markers):
        return

    protected_markers = [
        "\\10-current\\",
        "current identity.md",
        "current strategy.md",
    ]
    destructive = re.search(
        r"\b(remove-item|move-item|rename-item|rm|del|erase|mv|rmdir)\b", lower
    )
    patch_count = lower.count("*** update file:") + lower.count("*** delete file:")
    if any(marker in lower for marker in protected_markers):
        _deny("Protected identity/strategy changes must use the Second Self edit broker.")
    elif destructive:
        _deny("Private delete, move, or rename operations must use the Second Self edit broker.")
    elif patch_count >= 5:
        _deny("Bulk private edits affecting five or more files must use the Second Self edit broker.")


if __name__ == "__main__":
    main()
