#!/usr/bin/env python3
"""Thin Codex UserPromptSubmit adapter for the portable ECHO assembler."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "90-system" / ".echo" / "runtime"
sys.path.insert(0, str(RUNTIME))

from prompt import EchoContextError, activation_reason, failure_context, render_context  # noqa: E402


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        _emit({"continue": True, "systemMessage": "ECHO hook ignored malformed input."})
        return 0

    prompt = event.get("prompt") if isinstance(event, dict) else None
    reason = activation_reason(prompt) if isinstance(prompt, str) else None
    if reason is None:
        return 0

    try:
        context = render_context(repo_root=REPO_ROOT, reason=reason).text
        message = None
    except EchoContextError as exc:
        context = failure_context(exc)
        message = f"ECHO context unavailable ({exc.code})."

    payload: dict[str, object] = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }
    if message:
        payload["systemMessage"] = message
    _emit(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
