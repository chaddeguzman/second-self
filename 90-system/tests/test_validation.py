from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from second_self.core.paths import SecondSelfPaths
from second_self.core.scaffold import PUBLIC_SCAFFOLD_FILES
from second_self.maintenance.validation import validate


def _synthetic_openai_key() -> str:
    return "sk-" + "proj-" + "abcdefghijklmnopqrstuvwxyz"


def test_layer1_public_scaffold_is_allowed_but_personal_notes_are_rejected(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    memory = repo / "01-strategy-storage" / "00 Memory"
    memory.mkdir(parents=True)
    data.mkdir()

    public_scaffolds = [
        repo / "01-strategy-storage" / relative
        for relative in PUBLIC_SCAFFOLD_FILES["01-strategy-storage"]
    ]
    for scaffold in public_scaffolds:
        scaffold.parent.mkdir(parents=True, exist_ok=True)
        scaffold.write_text(
            "# Strategy Storage\n" if scaffold.name == "README.md" else "",
            encoding="utf-8",
        )
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
            str(personal_note),
            *(str(scaffold) for scaffold in public_scaffolds),
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


def test_privacy_validation_scans_staged_blob_instead_of_safe_worktree_copy(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    data.mkdir()
    tracked = repo / "config.txt"
    tracked.write_text(_synthetic_openai_key() + "\n", encoding="utf-8")
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "add", "--", str(tracked)],
        check=True,
        capture_output=True,
    )
    tracked.write_text("safe worktree content\n", encoding="utf-8")

    errors = validate(
        SecondSelfPaths(repo_root=repo, data_root=data),
        privacy=True,
        check_private=False,
    )

    assert errors == ["config.txt: possible OpenAI key"]


def test_privacy_validation_ignores_unstaged_secret_in_worktree(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    data.mkdir()
    tracked = repo / "config.txt"
    tracked.write_text("safe staged content\n", encoding="utf-8")
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "add", "--", str(tracked)],
        check=True,
        capture_output=True,
    )
    tracked.write_text(_synthetic_openai_key() + "\n", encoding="utf-8")

    errors = validate(
        SecondSelfPaths(repo_root=repo, data_root=data),
        privacy=True,
        check_private=False,
    )

    assert errors == []


def test_privacy_validation_fails_closed_when_git_index_cannot_be_enumerated(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "not-a-repository"
    data = tmp_path / "data"
    repo.mkdir()
    data.mkdir()

    errors = validate(
        SecondSelfPaths(repo_root=repo, data_root=data),
        privacy=True,
        check_private=False,
    )

    assert errors == ["privacy validation could not enumerate the Git index"]


def test_privacy_validation_fails_closed_when_staged_blob_cannot_be_read(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    data.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "update-index",
            "--add",
            "--info-only",
            "--cacheinfo",
            "100644,1111111111111111111111111111111111111111,missing.txt",
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
        "privacy validation could not read staged blob for missing.txt"
    ]


def test_privacy_validation_fails_closed_when_git_cannot_be_started(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    data.mkdir()

    def fail_to_start(*args, **kwargs):
        raise OSError("git unavailable")

    monkeypatch.setattr(
        "second_self.maintenance.validation.subprocess.run", fail_to_start
    )

    errors = validate(
        SecondSelfPaths(repo_root=repo, data_root=data),
        privacy=True,
        check_private=False,
    )

    assert errors == ["privacy validation could not enumerate the Git index"]


def test_privacy_validation_fails_closed_when_git_cannot_read_blob(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    data.mkdir()
    tracked = repo / "tracked.txt"
    tracked.write_text("staged content\n", encoding="utf-8")
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "add", "--", str(tracked)],
        check=True,
        capture_output=True,
    )
    real_run = subprocess.run

    def fail_blob_read(command, **kwargs):
        if "cat-file" in command:
            raise OSError("git blob read unavailable")
        return real_run(command, **kwargs)

    monkeypatch.setattr(
        "second_self.maintenance.validation.subprocess.run", fail_blob_read
    )

    errors = validate(
        SecondSelfPaths(repo_root=repo, data_root=data),
        privacy=True,
        check_private=False,
    )

    assert errors == [
        "privacy validation could not read staged blob for tracked.txt"
    ]


@pytest.mark.parametrize("mode", ["120000", "160000"])
def test_non_regular_index_entry_still_blocks_private_runtime_path(
    tmp_path: Path,
    mode: str,
) -> None:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    data.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    object_id = "2222222222222222222222222222222222222222"
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "update-index",
            "--add",
            "--info-only",
            "--cacheinfo",
            f"{mode},{object_id},.second-self.local.json",
        ],
        check=True,
        capture_output=True,
    )

    errors = validate(
        SecondSelfPaths(repo_root=repo, data_root=data),
        privacy=True,
        check_private=False,
    )

    assert errors == ["private/runtime path is tracked: .second-self.local.json"]


def test_privacy_validation_scans_staged_symlink_blob_content(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    data.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    object_id = subprocess.run(
        ["git", "-C", str(repo), "hash-object", "-w", "--stdin"],
        input=b"C:\\Users\\Alice\\private.txt",
        check=True,
        capture_output=True,
    ).stdout.decode("ascii").strip()
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "update-index",
            "--add",
            "--cacheinfo",
            f"120000,{object_id},shortcut",
        ],
        check=True,
        capture_output=True,
    )

    errors = validate(
        SecondSelfPaths(repo_root=repo, data_root=data),
        privacy=True,
        check_private=False,
    )

    assert errors == ["shortcut: contains an absolute user path"]
