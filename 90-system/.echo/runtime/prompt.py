#!/usr/bin/env python3
"""Assemble ECHO Tier 1-2 context without depending on an agent provider."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


CONTEXT_VERSION = "ECHO_CONTEXT_V1"
MAX_CONTEXT_BYTES = 8_000
TIMEZONE = ZoneInfo("Asia/Shanghai")

_EXPLICIT = re.compile(r"(?i)(?:\$echo\b|^\s*(?:hey\s+)?echo\s*[:,\u2014-])")
_ECHO_VERBS = re.compile(
    r"(?i)^\s*(?:hey\s+)?echo\s+(?:find|recall|remember|tell|what|where|when|"
    r"show|help|look|search|good\s+morning)\b"
)
_RECALL_CUES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("remember-fragment", re.compile(r"(?i)\bi remember(?:ed)?\b")),
    ("past-idea", re.compile(r"(?i)\bi (?:had|wrote|saved|noted) (?:an? )?(?:idea|note|thought)\b")),
    ("known-somewhere", re.compile(r"(?i)\bi know (?:i(?:'ve| have)|this is) .*\bsomewhere\b")),
    ("find-my-writing", re.compile(r"(?i)\bfind (?:what|something) i (?:wrote|saved|said|noted)\b")),
    ("past-decision", re.compile(r"(?i)\bwhat did i decide\b")),
    ("past-context", re.compile(r"(?i)\bwhat were we (?:doing|working on|discussing)\b")),
)


class EchoContextError(RuntimeError):
    """A privacy-safe ECHO assembly failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PromptBundle:
    text: str
    stable_fingerprint: str
    byte_count: int


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def activation_reason(prompt: str) -> str | None:
    """Return a conservative ECHO activation reason for a user prompt."""
    if not isinstance(prompt, str) or not prompt.strip():
        return None
    if _EXPLICIT.search(prompt) or _ECHO_VERBS.search(prompt):
        return "explicit-echo"
    for reason, pattern in _RECALL_CUES:
        if pattern.search(prompt):
            return reason
    return None


def _read_required(path: Path, label: str) -> str:
    try:
        raw = path.read_bytes()
        value = raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise EchoContextError("source-unavailable", f"{label} is unavailable") from exc
    if not value.strip():
        raise EchoContextError("source-empty", f"{label} is empty")
    return value


def _validate_identity(value: str) -> None:
    if not value.startswith("# ECHO \u2014 Identity"):
        raise EchoContextError("identity-invalid", "IDENTITY.md has an unexpected format")


def _validate_skill(value: str) -> None:
    if not value.startswith("---\n") or "\nname: echo\n" not in value[:500]:
        raise EchoContextError("skill-invalid", "ECHO SKILL.md has an unexpected format")


def _stable_payload(repo_root: Path) -> str:
    identity = _read_required(repo_root / "90-system" / ".echo" / "IDENTITY.md", "IDENTITY.md")
    skill = _read_required(
        repo_root / "02-skills-projects" / "skills" / "echo" / "SKILL.md",
        "ECHO SKILL.md",
    )
    _validate_identity(identity)
    _validate_skill(skill)
    identity_separator = "" if identity.endswith(("\n", "\r")) else "\n"
    skill_separator = "" if skill.endswith(("\n", "\r")) else "\n"
    return (
        "### Identity (Tier 1; complete source)\n"
        f"{identity}{identity_separator}\n"
        "### Operating rules (Tier 2; complete core)\n"
        f"{skill}{skill_separator}\n"
        "### Deferred stable slots\n"
        "- Tier 3 core knowledge: not loaded by this cycle.\n"
        "- Tier 8 generated capabilities: not loaded by this cycle.\n"
    )


def render_context(
    *,
    repo_root: Path | None = None,
    now: datetime | None = None,
    reason: str = "skill-fallback",
) -> PromptBundle:
    """Read canonical sources and assemble stable then dynamic ECHO context."""
    root = (repo_root or default_repo_root()).resolve()
    stable = _stable_payload(root)
    fingerprint = hashlib.sha256(stable.encode("utf-8")).hexdigest()
    instant = now or datetime.now(TIMEZONE)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=TIMEZONE)
    else:
        instant = instant.astimezone(TIMEZONE)
    text = (
        f"<{CONTEXT_VERSION}>\n"
        "## Stable block\n"
        f"stable_fingerprint: sha256:{fingerprint}\n"
        f"{stable}\n"
        "## Dynamic block\n"
        f"current_time: {instant.isoformat(timespec='seconds')}\n"
        f"activation_reason: {reason}\n"
        "recall_results: arrive as fresh tool output when retrieval is required\n"
        f"</{CONTEXT_VERSION}>\n"
    )
    byte_count = len(text.encode("utf-8"))
    if byte_count > MAX_CONTEXT_BYTES:
        raise EchoContextError(
            "context-too-large",
            f"ECHO context exceeds the {MAX_CONTEXT_BYTES}-byte safety budget",
        )
    return PromptBundle(text=text, stable_fingerprint=fingerprint, byte_count=byte_count)


def failure_context(error: EchoContextError) -> str:
    """Return a small model-visible failure that contains no filesystem paths."""
    return (
        f"<{CONTEXT_VERSION}_ERROR>\n"
        f"code: {error.code}\n"
        "ECHO was not loaded. Do not imitate or claim the ECHO persona. "
        "Tell Chad that the ECHO context needs repair.\n"
        f"</{CONTEXT_VERSION}_ERROR>\n"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="echo-prompt")
    sub = parser.add_subparsers(dest="command", required=True)
    render = sub.add_parser("render", help="Render current Tier 1-2 context")
    render.add_argument("--reason", default="skill-fallback")
    sub.add_parser("check", help="Validate sources and report safe metadata")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        bundle = render_context(reason=getattr(args, "reason", "diagnostic"))
    except EchoContextError as exc:
        print(json.dumps({"valid": False, "code": exc.code, "message": str(exc)}))
        return 2
    if args.command == "render":
        print(bundle.text, end="")
    else:
        print(
            json.dumps(
                {
                    "valid": True,
                    "version": CONTEXT_VERSION,
                    "stable_fingerprint": bundle.stable_fingerprint,
                    "byte_count": bundle.byte_count,
                    "max_bytes": MAX_CONTEXT_BYTES,
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
