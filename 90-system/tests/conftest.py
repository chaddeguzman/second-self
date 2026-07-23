from pathlib import Path

import pytest

from second_self.paths import SecondSelfPaths
from second_self.scaffold import scaffold


@pytest.fixture
def second_self(tmp_path: Path) -> SecondSelfPaths:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    paths = SecondSelfPaths(repo, data)
    scaffold(paths)
    return paths

