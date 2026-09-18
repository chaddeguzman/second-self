#!/usr/bin/env python3
"""Check Hermes-facing ECHO contracts without loading private Second Self data.

This is the repository-side half of Hermes certification.  It verifies that
the canonical ECHO sources, generated Hermes bundle, and specialist contracts
are present and consistent.  A live Hermes session is still required before
the result can be called runtime-certified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from prompt import EchoContextError, render_context


REPORT_VERSION = "hermes-readiness/v1"
ROLES = {
    "walter": ("research", "sources"),
    "sherlock": ("investigation", "evidence"),
    "charlie": ("development", "testing"),
}


@dataclass(frozen=True)
class Check:
    check_id: str
    passed: bool
    detail: str


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_file(root: Path, relative: str, check_id: str) -> Check:
    path = root / relative
    try:
        value = path.read_bytes()
    except (OSError, UnicodeError):
        return Check(check_id, False, "required file unavailable")
    return Check(check_id, bool(value.strip()), "present and non-empty")


def _check_mirror(root: Path, source: str, generated: str, check_id: str) -> Check:
    source_path = root / source
    generated_path = root / generated
    try:
        matches = _digest(source_path) == _digest(generated_path)
    except OSError:
        matches = False
    return Check(
        check_id,
        matches,
        "canonical and Hermes bundle match" if matches else "canonical and Hermes bundle differ",
    )


def run_checks(root: Path) -> tuple[Check, ...]:
    checks: list[Check] = []
    checks.extend(
        (
            _check_file(root, "90-system/.echo/IDENTITY.md", "canonical.identity"),
            _check_file(root, "02-skills-projects/skills/echo/SKILL.md", "canonical.skill"),
            _check_file(root, "90-system/.echo/runtime/prompt.py", "canonical.runtime"),
            _check_file(root, "90-system/.echo/hermes-ready/HERMES-SETUP.md", "bundle.setup"),
            _check_file(root, "90-system/.echo/hermes-ready/STABLE_BLOCK.md", "bundle.stable_block"),
            _check_file(root, "90-system/.echo/subagents/README.md", "delegation.protocol"),
        )
    )
    checks.extend(
        (
            _check_mirror(
                root,
                "90-system/.echo/IDENTITY.md",
                "90-system/.echo/hermes-ready/IDENTITY.md",
                "bundle.identity_matches",
            ),
            _check_mirror(
                root,
                "02-skills-projects/skills/echo/SKILL.md",
                "90-system/.echo/hermes-ready/SKILL.md",
                "bundle.skill_matches",
            ),
        )
    )
    try:
        render_context(repo_root=root, reason="hermes-certification")
        checks.append(Check("context.assembly", True, "canonical ECHO context assembles"))
    except EchoContextError as exc:
        checks.append(Check("context.assembly", False, f"assembly failed: {exc.code}"))

    delegation = root / "02-skills-projects/skills/echo/references/delegation.md"
    try:
        delegation_text = delegation.read_text(encoding="utf-8").lower()
    except (OSError, UnicodeError):
        delegation_text = ""
    checks.append(
        Check(
            "delegation.boundaries",
            all(term in delegation_text for term in ("walter", "sherlock", "charlie", "scope")),
            "role routing and scoped delegation are documented",
        )
    )

    for role, markers in ROLES.items():
        skill = root / "90-system/.echo/subagents" / role / "SKILL.md"
        log = root / "90-system/.echo/subagents" / role / "log.md"
        try:
            text = skill.read_text(encoding="utf-8").lower()
            valid = log.is_file() and all(marker in text for marker in markers)
        except (OSError, UnicodeError):
            valid = False
        checks.append(
            Check(
                f"agent.{role}",
                valid,
                "skill and task log present with role markers" if valid else "role contract incomplete",
            )
        )
    return tuple(checks)


def build_report(root: Path) -> dict[str, object]:
    checks = run_checks(root.resolve())
    static_ready = all(check.passed for check in checks)
    return {
        "version": REPORT_VERSION,
        "static_ready": static_ready,
        "runtime_certified": False,
        "runtime_smoke": "required",
        "checks": [asdict(check) for check in checks],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="certify-hermes")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = build_report(args.repo)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("Hermes static readiness: " + ("PASS" if report["static_ready"] else "FAIL"))
        print("Hermes runtime certification: NOT RUN")
        for check in report["checks"]:
            status = "PASS" if check["passed"] else "FAIL"
            print(f"[{status}] {check['check_id']}: {check['detail']}")
    return 0 if report["static_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
