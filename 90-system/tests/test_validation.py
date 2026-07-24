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
    reference_scaffolds = [
        repo / "01-strategy-storage" / "04 References" / name / ".gitkeep"
        for name in ("00 books", "01 quotes", "02 research", "03 guides", "04 docs")
    ]
    for scaffold in reference_scaffolds:
        scaffold.parent.mkdir(parents=True, exist_ok=True)
        scaffold.touch()
    personal_note = memory / "personal.md"
    personal_note.write_text("# Private\n", encoding="utf-8")

    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "add",
            "--",
            str(readme),
            str(personal_note),
            *(str(scaffold) for scaffold in reference_scaffolds),
        ],
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


def test_projects_placeholder_is_public_but_project_contents_are_rejected(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    project = repo / "02-skills-projects" / "projects" / "example"
    project.mkdir(parents=True)
    data.mkdir()

    placeholder = repo / "02-skills-projects" / "projects" / ".gitkeep"
    placeholder.touch()
    private_file = project / "private.md"
    private_file.write_text("# Private project\n", encoding="utf-8")

    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "add",
            "--",
            str(placeholder),
            str(private_file),
        ],
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
        "02-skills-projects/projects/example/private.md"
    ]


def test_wiki_placeholder_is_public_but_generated_pages_are_rejected(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    wiki = repo / "03-wiki"
    wiki.mkdir(parents=True)
    data.mkdir()
    placeholder = wiki / ".gitkeep"
    placeholder.touch()
    private_page = wiki / "topics" / "private.md"
    private_page.parent.mkdir()
    private_page.write_text("# Private synthesis\n", encoding="utf-8")
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "add", "--", str(placeholder), str(private_page)],
        check=True,
        capture_output=True,
    )

    errors = validate(
        SecondSelfPaths(repo_root=repo, data_root=data),
        privacy=True,
        check_private=False,
    )

    assert errors == ["private/runtime path is tracked: 03-wiki/topics/private.md"]


def test_private_schema_marker_is_rejected_if_tracked(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    data.mkdir()
    marker = repo / ".second-self-schema"
    marker.write_text("2\n", encoding="ascii")
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "add", "--", str(marker)],
        check=True,
        capture_output=True,
    )

    errors = validate(
        SecondSelfPaths(repo_root=repo, data_root=data),
        privacy=True,
        check_private=False,
    )

    assert errors == ["private/runtime path is tracked: .second-self-schema"]
