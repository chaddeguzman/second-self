from __future__ import annotations

from pathlib import Path

from second_self.core import paths


def test_repo_root_is_the_checked_out_repository_root() -> None:
    expected = Path(__file__).resolve().parents[2]  # 90-system/tests -> repo root
    assert paths.REPO_ROOT == expected
    assert (paths.REPO_ROOT / "Start-Second-Self.cmd").is_file()


def test_config_path_lives_at_the_repository_root() -> None:
    assert paths.CONFIG_PATH == paths.REPO_ROOT / ".second-self.local.json"
    assert paths.CONFIG_PATH.name == ".second-self.local.json"


def test_marker_sits_on_the_module_files_ancestor_chain() -> None:
    """The repo root must be reachable from paths.py, not a sibling level."""
    module_file = Path(paths.__file__).resolve()
    marked_ancestors = [
        parent for parent in module_file.parents if (parent / "Start-Second-Self.cmd").is_file()
    ]
    assert marked_ancestors
    assert marked_ancestors[0] == paths.REPO_ROOT