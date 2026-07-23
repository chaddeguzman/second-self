from pathlib import Path

import pytest

from main_brain.paths import BrainPaths
from main_brain.scaffold import scaffold


@pytest.fixture
def brain(tmp_path: Path) -> BrainPaths:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    paths = BrainPaths(repo, data)
    scaffold(paths)
    return paths

