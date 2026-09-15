#!/usr/bin/env python3
"""Live Tier 1-2 certification against authenticated Codex CLI.

The disposable repository and JSONL streams exist only for the duration of
this process. Canonical identity content is never copied into it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parents[3]


def _write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="")


def _seed(repo: Path, marker: str) -> None:
    (repo / ".codex").mkdir(parents=True)
    (repo / "90-system" / ".echo" / "runtime").mkdir(parents=True)
    (repo / "02-skills-projects" / "skills" / "echo").mkdir(parents=True)
    (repo / ".agents" / "skills" / "echo").mkdir(parents=True)
    shutil.copy2(ROOT / ".codex" / "echo_prompt_hook.py", repo / ".codex" / "echo_prompt_hook.py")
    shutil.copy2(
        ROOT / "90-system" / ".echo" / "runtime" / "prompt.py",
        repo / "90-system" / ".echo" / "runtime" / "prompt.py",
    )
    shutil.copy2(
        ROOT / "90-system" / ".echo" / "runtime" / "__init__.py",
        repo / "90-system" / ".echo" / "runtime" / "__init__.py",
    )
    shutil.copy2(
        ROOT / "02-skills-projects" / "skills" / "echo" / "SKILL.md",
        repo / "02-skills-projects" / "skills" / "echo" / "SKILL.md",
    )
    shutil.copy2(ROOT / ".agents" / "skills" / "echo" / "SKILL.md", repo / ".agents" / "skills" / "echo" / "SKILL.md")
    _write(repo / "90-system" / ".echo" / "IDENTITY.md", f"# ECHO — Identity\nidentity_marker: {marker}\n")
    _write(
        repo / ".codex" / "hooks.json",
        json.dumps(
            {
                "hooks": {
                    "UserPromptSubmit": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": 'python "$(git rev-parse --show-toplevel)/.codex/echo_prompt_hook.py"',
                                    "commandWindows": (
                                        "$root = git rev-parse --show-toplevel; "
                                        "python (Join-Path $root '.codex/echo_prompt_hook.py')"
                                    ),
                                    "timeout": 10,
                                }
                            ]
                        }
                    ]
                }
            },
            indent=2,
        )
        + "\n",
    )


def _events(command: list[str], *, cwd: Path, timeout: int = 240) -> list[dict[str, object]]:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    events: list[dict[str, object]] = []
    for line in result.stdout.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
    if result.returncode != 0:
        tail = result.stderr.strip().splitlines()[-1:] or ["no diagnostic"]
        raise RuntimeError(f"Codex exited {result.returncode}: {tail[0]}")
    return events


def _thread_id(events: list[dict[str, object]]) -> str:
    for event in events:
        if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
            return str(event["thread_id"])
    raise RuntimeError("Codex JSONL did not contain a thread id")


def _message(events: list[dict[str, object]]) -> str:
    messages: list[str] = []
    for event in events:
        if event.get("type") != "item.completed":
            continue
        item = event.get("item")
        if isinstance(item, dict) and item.get("type") == "agent_message" and isinstance(item.get("text"), str):
            messages.append(str(item["text"]))
    if not messages:
        raise RuntimeError("Codex JSONL did not contain an agent message")
    return messages[-1].strip()


def _usage(events: list[dict[str, object]]) -> dict[str, object]:
    for event in reversed(events):
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            return dict(event["usage"])
    return {}


def _item_types(events: list[dict[str, object]]) -> list[str]:
    values: list[str] = []
    for event in events:
        item = event.get("item")
        if isinstance(item, dict) and isinstance(item.get("type"), str):
            values.append(str(item["type"]))
    return values


def _errors(events: list[dict[str, object]]) -> list[dict[str, object]]:
    values: list[dict[str, object]] = []
    for event in events:
        item = event.get("item")
        if isinstance(item, dict) and item.get("type") == "error":
            values.append(item)
    return values


@contextmanager
def _trusted_profile(repo: Path) -> Iterator[str]:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    name = f"echo-cert-{uuid.uuid4().hex}"
    profile = codex_home / f"{name}.config.toml"
    _write(
        profile,
        f"[projects.'{repo}']\ntrust_level = \"trusted\"\n",
    )
    try:
        yield name
    finally:
        profile.unlink(missing_ok=True)


def _initial(repo: Path, profile: str, prompt: str) -> list[dict[str, object]]:
    return _events(
        [
            "codex",
            "exec",
            "-C",
            str(repo),
            "--sandbox",
            "read-only",
            "--json",
            "--color",
            "never",
            "--profile",
            profile,
            "--dangerously-bypass-hook-trust",
            prompt,
        ],
        cwd=repo,
    )


def _resume(repo: Path, profile: str, thread_id: str, prompt: str) -> list[dict[str, object]]:
    return _events(
        [
            "codex",
            "--profile",
            profile,
            "exec",
            "resume",
            "--json",
            "--dangerously-bypass-hook-trust",
            thread_id,
            prompt,
        ],
        cwd=repo,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="echo-codex-cert-") as directory:
        repo = Path(directory).resolve()
        _seed(repo, "ALPHA")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=ECHO Certification",
                "-c",
                "user.email=echo-certification@invalid.local",
                "commit",
                "-qm",
                "Seed disposable certification repository",
            ],
            cwd=repo,
            check=True,
        )

        with _trusted_profile(repo) as profile:
            marker_prompt = (
                "$echo Do not use tools or read files. Reply with exactly the identity_marker "
                "value from the developer-provided ECHO_CONTEXT_V1 for this turn."
            )
            alpha_events = _initial(repo, profile, marker_prompt)
            thread_id = _thread_id(alpha_events)
            alpha = _message(alpha_events)
            if alpha != "ALPHA":
                raise RuntimeError(
                    f"Expected ALPHA, received {alpha!r}; item types: {_item_types(alpha_events)!r}; "
                    f"errors: {_errors(alpha_events)!r}"
                )

            _write(repo / "90-system" / ".echo" / "IDENTITY.md", "# ECHO — Identity\nidentity_marker: BETA\n")
            beta_events = _resume(
                repo,
                profile,
                thread_id,
                "$echo Do not use tools or read files. Use only the newest developer-provided "
                "ECHO_CONTEXT_V1 for this turn and reply with exactly its identity_marker value.",
            )
            beta = _message(beta_events)
            if beta != "BETA" or "ALPHA" in beta:
                raise RuntimeError(
                    f"Expected only BETA after live identity edit, received {beta!r}; "
                    f"item types: {_item_types(beta_events)!r}"
                )

            ordinary_events = _initial(repo, profile, "Reply with exactly ORDINARY.")
            ordinary = _message(ordinary_events)
            if ordinary != "ORDINARY":
                raise RuntimeError(f"Ordinary prompt was affected: {ordinary!r}")

            recall_events = _initial(
                repo,
                profile,
                "I remember something. Reply with exactly the identity_marker value from ECHO_CONTEXT_V1.",
            )
            recall = _message(recall_events)
            if recall != "BETA":
                raise RuntimeError(f"Implicit recall cue did not load BETA: {recall!r}")

        summary = {
            "certified": True,
            "identity_first": alpha,
            "identity_after_edit_same_session": beta,
            "ordinary_prompt": ordinary,
            "implicit_recall": recall,
            "usage": {
                "alpha": _usage(alpha_events),
                "beta": _usage(beta_events),
                "ordinary": _usage(ordinary_events),
                "implicit": _usage(recall_events),
            },
            "temporary_repository_removed_on_exit": True,
        }
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
