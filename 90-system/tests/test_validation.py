from __future__ import annotations

import subprocess
from pathlib import Path

from second_self.paths import SecondSelfPaths
from second_self.validation import validate


def test_layer1_readme_is_public_but_personal_notes_are_rejected(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    memory = repo / "01-strategy-storage" / "00 Memory"
    memory.mkdir(parents=True)
    data.mkdir()

    readme = repo / "01-strategy-storage" / "README.md"
    readme.write_text("# Strategy Storage\n", encoding="utf-8")
    personal_note = memory / "personal.md"
    personal_note.write_text("# Private\n", encoding="utf-8")

    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "add", "--", str(readme), str(personal_note)],
        check=True,
        capture_output=True,
    )

    errors = validate(
        SecondSelfPaths(repo_root=repo, data_root=data),
        privacy=True,
        check_private=False,
    )

    assert errors == [
        "private/runtime path is tracked: "
        "01-strategy-storage/00 Memory/personal.md"
    ]
