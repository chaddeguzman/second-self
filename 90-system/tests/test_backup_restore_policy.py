"""Synthetic-only tests for archive validation and authenticated manifests."""

import importlib.util
import io
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "90-system/automation/scripts/backup_archive.py"
spec = importlib.util.spec_from_file_location("backup_archive", MODULE_PATH)
assert spec and spec.loader
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


def _write_tar(path: Path, member: str, *, symlink: bool = False) -> None:
    with tarfile.open(path, "w") as output:
        info = tarfile.TarInfo(member)
        if symlink:
            info.type = tarfile.SYMTYPE
            info.linkname = "outside"
            output.addfile(info)
        else:
            content = b"synthetic"
            info.size = len(content)
            output.addfile(info, io.BytesIO(content))


@pytest.mark.parametrize("member", ["../../outside.md", "/absolute.md", "C:/drive.md"])
def test_archive_policy_rejects_unsafe_members(tmp_path, member):
    path = tmp_path / "unsafe.tar"
    _write_tar(path, member)
    with pytest.raises(ValueError, match="unsafe archive member"):
        archive.validate_archive(path)


def test_archive_policy_rejects_symlink_and_manifest_detects_same_size_change(tmp_path):
    path = tmp_path / "link.tar"
    _write_tar(path, "vault/link", symlink=True)
    with pytest.raises(ValueError, match="link member"):
        archive.validate_archive(path)
    source = tmp_path / "source"
    source.mkdir()
    (source / "note.md").write_text("alpha", encoding="utf-8")
    manifest = archive.build_manifest(source, "archive.age", "a" * 64)
    (source / "note.md").write_text("bravo", encoding="utf-8")
    with pytest.raises(ValueError, match="inventory digest mismatch"):
        archive.verify_inventory(source, manifest)
