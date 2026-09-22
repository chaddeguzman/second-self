#!/usr/bin/env python3
"""Verify the checked-in dependency lock and its selected profile metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LOCK = ROOT / "requirements.lock"
CHECKSUM = ROOT / "requirements.lock.sha256"
PROFILES = ROOT / "requirements/profiles.json"


def package_names(lock: Path) -> set[str]:
    names: set[str] = set()
    for line in lock.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==[^\s]+", line)
        if not match:
            raise ValueError("lock entry is not an exact public distribution pin")
        names.add(match.group(1).lower().replace("_", "-"))
    return names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    args = parser.parse_args(argv)
    lock = args.lock.resolve()
    expected = CHECKSUM.read_text(encoding="ascii").strip().split()[0]
    actual = hashlib.sha256(lock.read_bytes()).hexdigest()
    if actual != expected:
        print("dependency lock digest mismatch", file=sys.stderr)
        return 1
    profiles = json.loads(PROFILES.read_text(encoding="utf-8"))
    locked = package_names(lock)
    missing = sorted({name for values in profiles.values() for name in values} - locked)
    if missing:
        print("dependency profile entries missing from lock", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
