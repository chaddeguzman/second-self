from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    """Walk up from a module file until the repository root marker is found.

    The package previously lived at ``second_self/paths.py``; it now lives at
    ``second_self/core/paths.py``. A fixed ``parents`` offset is brittle, so
    locate the root via a stable marker file instead.
    """
    for parent in (start.resolve() if start.is_absolute() else start.resolve()).parents:
        if (parent / "Start-Second-Self.cmd").is_file():
            return parent
    raise FileNotFoundError(
        "Could not locate Second Self repository root "
        "(expected a Start-Second-Self.cmd marker)."
    )


REPO_ROOT = _find_repo_root(Path(__file__))
CONFIG_PATH = REPO_ROOT / ".second-self.local.json"


@dataclass(frozen=True)
class SecondSelfPaths:
    repo_root: Path
    data_root: Path

    @property
    def layer1(self) -> Path:
        return self.data_root / "01-strategy-storage"

    @property
    def projects(self) -> Path:
        return self.data_root / "02-skills-projects" / "projects"

    @property
    def raw(self) -> Path:
        return self.layer1 / "01 Notes" / "00 Raw"

    @property
    def wiki(self) -> Path:
        return self.data_root / "03-wiki"

    @property
    def cache(self) -> Path:
        return self.data_root / ".second-self-cache"

    @property
    def wiki_transactions(self) -> Path:
        return self.cache / "wiki-transactions"

    @property
    def audit(self) -> Path:
        return self.layer1 / "99-audit"

    @property
    def trash(self) -> Path:
        return self.layer1 / "98-trash"


def default_data_root() -> Path:
    return Path(os.environ.get("SECOND_SELF_DATA", Path.home() / "SecondSelfData"))


def load_paths(require_config: bool = False) -> SecondSelfPaths:
    data_root = default_data_root()
    if CONFIG_PATH.exists():
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        configured = raw.get("data_root")
        if configured:
            data_root = Path(os.path.expandvars(configured)).expanduser()
    elif require_config:
        raise FileNotFoundError(
            f"Missing {CONFIG_PATH.name}; run "
            "90-system/automation/scripts/bootstrap.ps1 first."
        )
    return SecondSelfPaths(REPO_ROOT, data_root.resolve())


def write_config(data_root: Path) -> Path:
    payload = {
        "schema_version": 1,
        "data_root": str(data_root.resolve()),
    }
    CONFIG_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return CONFIG_PATH


def resolve_private_path(paths: SecondSelfPaths, value: str | Path) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = paths.data_root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(paths.data_root.resolve())
    except ValueError as exc:
        raise ValueError(f"Path escapes private data root: {value}") from exc
    return resolved
