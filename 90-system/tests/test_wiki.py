from __future__ import annotations

import json
from pathlib import Path

import pytest

from second_self.broker.broker import (
    approve,
    propose,
    recover_wiki_transactions,
)
from second_self.cli import main
from second_self.core.paths import SecondSelfPaths
from second_self.wiki.wiki import (
    add_source,
    lint_wiki,
    references_destination,
    source_hash,
    source_id,
    wiki_status,
)


def _page(page_type: str, extra: str = "", body: str = "# Page\n") -> str:
    return f"""---
type: {page_type}
created: 2026-07-24
updated: 2026-07-24
status: active
verification: derived
tags: []
projects: []
related: []
{extra}---

{body}"""


def test_add_status_and_collision_safe_copy(
    second_self: SecondSelfPaths, tmp_path: Path
) -> None:
    source = tmp_path / "clip.md"
    source.write_text("# Clip\n", encoding="utf-8")

    first = add_source(second_self, source)
    second = add_source(second_self, source)
    status = wiki_status(second_self)

    assert first["copied"] is True
    assert first["source_id"] == second["source_id"]
    assert first["path"] != second["path"]
    assert len(status["pending"]) == 2


def test_source_id_truncates_to_12_chars() -> None:
    digest = "072958a2620bc0d4459fd8ac5ba6bee566ff39c76a6ba1d283a33be4fa0709dd"
    assert source_id(digest) == "072958a2620b"
    assert len(source_id(digest)) == 12


def test_bundle_hash_changes_with_relative_path(second_self: SecondSelfPaths) -> None:
    bundle = second_self.raw / "Article"
    bundle.mkdir()
    (bundle / "article.md").write_text("![](assets/shot.png)", encoding="utf-8")
    assets = bundle / "assets"
    assets.mkdir()
    (assets / "shot.png").write_bytes(b"image")
    first = source_hash(bundle)

    (assets / "shot.png").rename(assets / "renamed.png")

    assert source_hash(bundle) != first


def test_wiki_process_moves_source_to_references_and_updates_pages(
    second_self: SecondSelfPaths,
) -> None:
    source = second_self.raw / "idea.md"
    source.write_text("# Idea\nEvidence.", encoding="utf-8")
    digest = source_hash(source)
    destination = references_destination(second_self, source, "04 guides")
    move = {
        "from": source.relative_to(second_self.data_root).as_posix(),
        "to": destination.relative_to(second_self.data_root).as_posix(),
        "source_id": digest,
    }
    source_page = _page(
        "wiki-source",
        extra=(
            f"source_id: {source_id(digest)}\n"
            f"source_path: \"{move['to']}\"\n"
            f"source_sha256: {digest}\n"
            "source_kind: md\n"
            "processed_at: 2026-07-24T12:00:00+08:00\n"
        ),
        body="# Idea source\n\nSummary with evidence.\n",
    )
    proposal = propose(
        second_self,
        {
            "operation": "wiki_process",
            "changes": [
                {
                    "path": f"03-wiki/sources/{digest[:12]}-idea.md",
                    "content": source_page,
                }
            ],
            "moves": [move],
        },
    )
    approve(second_self, proposal["id"], "y", agent="pytest")

    assert not source.exists()
    assert destination.read_text(encoding="utf-8") == "# Idea\nEvidence."
    assert (second_self.wiki / "sources" / f"{digest[:12]}-idea.md").exists()
    journal = (
        second_self.wiki_transactions / proposal["id"] / "journal.json"
    )
    assert json.loads(journal.read_text(encoding="utf-8"))["status"] == "committed"


def test_stale_raw_source_blocks_wiki_process(second_self: SecondSelfPaths) -> None:
    source = second_self.raw / "changing.txt"
    source.write_text("first", encoding="utf-8")
    digest = source_hash(source)
    destination = references_destination(second_self, source, "05 docs")
    move = {
        "from": source.relative_to(second_self.data_root).as_posix(),
        "to": destination.relative_to(second_self.data_root).as_posix(),
        "source_id": digest,
    }
    proposal = propose(
        second_self,
        {
            "operation": "wiki_process",
            "changes": [
                {
                    "path": "03-wiki/sources/changing.md",
                    "content": _page(
                        "wiki-source",
                        extra=(
                            f"source_id: {source_id(digest)}\nsource_path: \"{move['to']}\"\n"
                            f"source_sha256: {digest}\n"
                        ),
                    ),
                }
            ],
            "moves": [move],
        },
    )
    source.write_text("changed", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Stale approval"):
        approve(second_self, proposal["id"], "yes")


def test_wiki_process_rolls_back_page_when_move_fails(
    second_self: SecondSelfPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    import second_self.broker.broker as broker_module

    source = second_self.raw / "rollback.txt"
    source.write_text("safe", encoding="utf-8")
    digest = source_hash(source)
    destination = references_destination(second_self, source, "05 docs")
    move = {
        "from": source.relative_to(second_self.data_root).as_posix(),
        "to": destination.relative_to(second_self.data_root).as_posix(),
        "source_id": digest,
    }
    target = second_self.wiki / "sources" / "rollback.md"
    proposal = propose(
        second_self,
        {
            "operation": "wiki_process",
            "changes": [
                {
                    "path": target.relative_to(second_self.data_root).as_posix(),
                    "content": _page(
                        "wiki-source",
                        extra=(
                            f"source_id: {source_id(digest)}\nsource_path: \"{move['to']}\"\n"
                            f"source_sha256: {digest}\n"
                        ),
                    ),
                }
            ],
            "moves": [move],
        },
    )
    def fail_move(source_path: str, destination_path: Path) -> None:
        raise OSError("simulated move failure")

    monkeypatch.setattr(broker_module.shutil, "move", fail_move)
    with pytest.raises(OSError, match="simulated move"):
        approve(second_self, proposal["id"], "y")

    assert source.read_text(encoding="utf-8") == "safe"
    assert not target.exists()
    journal = second_self.wiki_transactions / proposal["id"] / "journal.json"
    assert json.loads(journal.read_text(encoding="utf-8"))["status"] == "rolled-back"


def test_recover_interrupted_transaction_restores_source(
    second_self: SecondSelfPaths,
) -> None:
    original = second_self.raw / "recover.txt"
    destination = references_destination(second_self, original, "05 docs")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("recover me", encoding="utf-8")
    stage = second_self.wiki_transactions / "interrupted"
    stage.mkdir(parents=True)
    journal = {
        "id": "interrupted",
        "status": "applying",
        "changes": [],
        "moves": [
            {
                "from": original.relative_to(second_self.data_root).as_posix(),
                "to": destination.relative_to(second_self.data_root).as_posix(),
            }
        ],
    }
    (stage / "journal.json").write_text(json.dumps(journal), encoding="utf-8")

    assert recover_wiki_transactions(second_self) == ["interrupted"]
    assert original.read_text(encoding="utf-8") == "recover me"
    assert not destination.exists()


def test_lint_reports_broken_link_and_orphan(second_self: SecondSelfPaths) -> None:
    topic = second_self.wiki / "topics" / "orphan.md"
    topic.write_text(
        _page("wiki-topic", body="# Orphan\n\n[Missing](missing.md)\n"),
        encoding="utf-8",
    )

    errors = lint_wiki(second_self)

    assert any("broken link" in error for error in errors)
    assert any("orphan page" in error for error in errors)


def test_cli_wiki_status_does_not_print_absolute_root(
    second_self: SecondSelfPaths,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("second_self.cli.load_paths", lambda require_config=True: second_self)
    (second_self.raw / "source.txt").write_text("source", encoding="utf-8")

    assert main(["wiki", "status"]) == 0
    output = capsys.readouterr().out
    assert "source.txt" in output
    assert str(second_self.data_root) not in output


def test_status_detects_new_and_changed_curated_notes(
    second_self: SecondSelfPaths,
) -> None:
    note = second_self.layer1 / "00 Memory" / "Preference.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("# Preference\nFirst.", encoding="utf-8")
    first_hash = source_hash(note)
    relative = note.relative_to(second_self.data_root).as_posix()
    source_page = second_self.wiki / "sources" / "preference.md"
    source_page.write_text(
        _page(
            "wiki-source",
            extra=(
                f"source_id: {source_id(first_hash)}\nsource_path: \"{relative}\"\n"
                f"source_sha256: {first_hash}\n"
            ),
        ),
        encoding="utf-8",
    )
    note.write_text("# Preference\nChanged.", encoding="utf-8")
    new_note = second_self.layer1 / "03 Strategy" / "New.md"
    new_note.parent.mkdir(parents=True, exist_ok=True)
    new_note.write_text("# New\n", encoding="utf-8")

    status = wiki_status(second_self)

    assert [item["path"] for item in status["changed_curated"]] == [relative]
    assert new_note.relative_to(second_self.data_root).as_posix() in {
        item["path"] for item in status["unprocessed_curated"]
    }


def test_references_destination_preserves_filename(
    second_self: SecondSelfPaths,
) -> None:
    source = second_self.raw / "Screenshot.png"
    source.write_bytes(b"image")
    destination = references_destination(
        second_self, source, "03 research"
    )
    assert destination.parent == (second_self.layer1 / "04 References" / "03 research")
    assert destination.name == "Screenshot.png"


def test_references_destination_adds_minimal_collision_suffix(
    second_self: SecondSelfPaths,
) -> None:
    source = second_self.raw / "Screenshot.png"
    source.write_bytes(b"image")
    first = references_destination(second_self, source, "03 research")
    first.parent.mkdir(parents=True, exist_ok=True)
    first.write_bytes(b"first")

    second = references_destination(second_self, source, "03 research")

    assert second.parent == (second_self.layer1 / "04 References" / "03 research")
    assert second.name == "Screenshot-2.png"


def test_references_destination_rejects_invalid_subfolder(
    second_self: SecondSelfPaths,
) -> None:
    source = second_self.raw / "doc.md"
    source.write_text("doc", encoding="utf-8")
    with pytest.raises(ValueError, match="References subfolder"):
        references_destination(second_self, source, "invalid")