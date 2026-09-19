from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from second_self.broker import broker
from second_self.core import scaffold as scaffold_module
from second_self.maintenance import validation


REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_SCAFFOLD_HELPER = (
    REPO_ROOT / "90-system" / "automation" / "scripts" / "public-scaffold.ps1"
)
EXPECTED_PUBLIC_SCAFFOLD_FILES = {
    "01-strategy-storage": (
        "README.md",
        "00 Memory/.gitkeep",
        "02 Journal/.gitkeep",
        "03 Strategy/.gitkeep",
        "04 References/.gitkeep",
        "05 Reviews/.gitkeep",
    ),
    "02-skills-projects/projects": (".gitkeep",),
    "03-wiki": (
        ".gitkeep",
        "README.md",
        "analyses/.gitkeep",
        "entities/.gitkeep",
        "sources/.gitkeep",
        "topics/.gitkeep",
    ),
}
EXPECTED_PUBLIC_SCAFFOLD_PATHS = tuple(
    f"{root}/{relative}"
    for root, files in EXPECTED_PUBLIC_SCAFFOLD_FILES.items()
    for relative in files
)


def _production_manifest() -> dict[str, tuple[str, ...]]:
    manifest = getattr(scaffold_module, "PUBLIC_SCAFFOLD_FILES", None)
    assert manifest is not None, "canonical public scaffold manifest is missing"
    return manifest


def _write_manifest(repo: Path) -> None:
    path = repo / "90-system/app/second_self/public_scaffold.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema": "second-self-public-scaffold",
                "version": 1,
                "roots": [
                    {"path": root, "files": list(files)}
                    for root, files in EXPECTED_PUBLIC_SCAFFOLD_FILES.items()
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_public_scaffold(repo: Path) -> None:
    for root, files in EXPECTED_PUBLIC_SCAFFOLD_FILES.items():
        for relative in files:
            path = repo / root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            content = f"public scaffold: {root}/{relative}\n" if path.name == "README.md" else ""
            path.write_text(content, encoding="utf-8")


def _run_scaffold_helper(repo: Path, data: Path) -> subprocess.CompletedProcess[str]:
    helper = str(PUBLIC_SCAFFOLD_HELPER).replace("'", "''")
    repo_arg = str(repo).replace("'", "''")
    data_arg = str(data).replace("'", "''")
    command = (
        f". '{helper}'; "
        f"Connect-PublicScaffoldRoots -RepoRoot '{repo_arg}' -DataRoot '{data_arg}'"
    )
    return subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_manifest_matches_tracked_public_scaffold() -> None:
    manifest = _production_manifest()
    tracked = subprocess.run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "ls-files",
            "--",
            *[f"{root}/**" for root in manifest],
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    expected = sorted(
        f"{root}/{relative}"
        for root, files in EXPECTED_PUBLIC_SCAFFOLD_FILES.items()
        for relative in files
    )

    assert manifest == EXPECTED_PUBLIC_SCAFFOLD_FILES
    assert sorted(tracked) == expected


def test_runtime_allowlists_derive_from_manifest() -> None:
    manifest = _production_manifest()
    all_paths = {
        f"{root}/{relative}"
        for root, files in manifest.items()
        for relative in files
    }

    assert broker.LAYER1_SCAFFOLD_FILES == manifest["01-strategy-storage"]
    assert validation.ALLOWED_PRIVATE_SCAFFOLD_FILES == all_paths


def test_private_scaffold_uses_case_sensitive_uncategorized_name() -> None:
    assert "01-strategy-storage/04 References/06 Uncategorized" in scaffold_module.DIRECTORIES
    assert "01-strategy-storage/04 References/06 uncategorized" not in scaffold_module.DIRECTORIES


@pytest.mark.parametrize("public_path", EXPECTED_PUBLIC_SCAFFOLD_PATHS)
def test_gitignore_allows_every_manifest_path(public_path: str) -> None:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "check-ignore",
            "--quiet",
            "--no-index",
            "--",
            public_path,
        ],
        check=False,
    )

    assert result.returncode == 1


@pytest.mark.parametrize(
    "relative",
    ["README.md", "02-skills-projects/skills/second-self-wiki/SKILL.md"],
)
def test_public_guidance_uses_canonical_uncategorized_case(relative: str) -> None:
    text = (REPO_ROOT / relative).read_text(encoding="utf-8")

    assert "06 Uncategorized" in text
    assert "06 uncategorized" not in text


@pytest.mark.parametrize(
    "private_path",
    [
        "01-strategy-storage/01 Notes/.gitkeep",
        "01-strategy-storage/04 References/00 books/.gitkeep",
        "01-strategy-storage/01 Capture/private.md",
        "02-skills-projects/projects/example/private.md",
        "03-wiki/topics/private.md",
    ],
)
def test_gitignore_rejects_non_manifest_private_paths(private_path: str) -> None:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "check-ignore",
            "--quiet",
            "--no-index",
            "--",
            private_path,
        ],
        check=False,
    )

    assert result.returncode == 0


@pytest.mark.skipif(os.name != "nt", reason="bootstrap junctions require Windows")
def test_clean_clone_scaffold_is_preserved_when_junctions_are_created(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    data.mkdir()
    _write_manifest(repo)
    _write_public_scaffold(repo)
    sentinel = data / "01-strategy-storage/Private.md"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("private\n", encoding="utf-8")

    result = _run_scaffold_helper(repo, data)

    assert result.returncode == 0, result.stderr
    for root, files in EXPECTED_PUBLIC_SCAFFOLD_FILES.items():
        source = repo / root
        target = data / root
        assert os.path.isjunction(source)
        for relative in files:
            assert (target / relative).is_file()
    assert sentinel.read_text(encoding="utf-8") == "private\n"


@pytest.mark.skipif(os.name != "nt", reason="bootstrap junctions require Windows")
def test_bootstrap_preflights_every_root_before_replacing_any_scaffold(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    data.mkdir()
    _write_manifest(repo)
    _write_public_scaffold(repo)
    unexpected = repo / "03-wiki/private.md"
    unexpected.write_text("private\n", encoding="utf-8")

    result = _run_scaffold_helper(repo, data)

    assert result.returncode != 0
    assert "unexpected files" in result.stderr
    assert unexpected.is_file()
    for root in EXPECTED_PUBLIC_SCAFFOLD_FILES:
        assert not os.path.isjunction(repo / root)
