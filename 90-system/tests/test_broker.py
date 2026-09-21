import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from second_self.broker.broker import approve, propose
from second_self.cli import main
from second_self.core.paths import SecondSelfPaths


def _ensure_note(path: Path, title: str = "Note") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ntype: note\ncreated: 2026-07-24\nstatus: active\n---\n\n# {title}\n",
        encoding="utf-8",
    )


def _proposal_path(paths: SecondSelfPaths, proposal_id: str) -> Path:
    return paths.audit / "proposals" / f"{proposal_id}.json"


def _approval_digest(proposal: dict[str, object]) -> str:
    payload = {
        "specification": proposal["specification"],
        "input_hashes": proposal["input_hashes"],
        "exact_preview": proposal["exact_preview"],
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@pytest.mark.parametrize("confirmation", ["Y", "y", "Yes", "YES", " yes "])
def test_single_approval_edit_and_audit(
    second_self: SecondSelfPaths, confirmation: str
) -> None:
    target = second_self.layer1 / "01 Capture/01 Current" / "Current Identity.md"
    _ensure_note(target, "Current Identity")
    updated = target.read_text(encoding="utf-8") + "\nApproved value.\n"
    proposal = propose(
        second_self,
        {
            "operation": "edit",
            "changes": [
                {
                    "path": str(target.relative_to(second_self.data_root)),
                    "content": updated,
                }
            ],
        },
    )
    with pytest.raises(PermissionError):
        approve(second_self, proposal["id"], "approve")
    approve(second_self, proposal["id"], confirmation, agent="pytest")
    assert "Approved value." in target.read_text(encoding="utf-8")
    audit = (second_self.audit / "agent-edits.jsonl").read_text(encoding="utf-8")
    assert '"agent": "pytest"' in audit


def test_multi_file_edit_failure_restores_every_original(
    second_self: SecondSelfPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = second_self.layer1 / "01 Capture/01 Current" / "First.md"
    second = second_self.layer1 / "01 Capture/01 Current" / "Second.md"
    _ensure_note(first, "First")
    _ensure_note(second, "Second")
    first_original = first.read_text(encoding="utf-8")
    second_original = second.read_text(encoding="utf-8")
    proposal = propose(
        second_self,
        {
            "operation": "edit",
            "changes": [
                {"path": str(first), "content": "# First replacement"},
                {"path": str(second), "content": "# Second replacement"},
            ],
        },
    )
    original_write_text = Path.write_text
    writes = 0

    def fail_on_second_write(path: Path, data: str, *args: object, **kwargs: object) -> None:
        nonlocal writes
        if path in {first, second}:
            writes += 1
            if writes == 2:
                raise OSError("simulated second write failure")
        original_write_text(path, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_on_second_write)
    with pytest.raises(OSError, match="simulated second write failure"):
        approve(second_self, proposal["id"], "yes")

    assert first.read_text(encoding="utf-8") == first_original
    assert second.read_text(encoding="utf-8") == second_original


def test_multi_file_move_failure_restores_sources_and_destinations(
    second_self: SecondSelfPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = second_self.layer1 / "01 Capture/02 Notes/First.md"
    second = second_self.layer1 / "01 Capture/02 Notes/Second.md"
    first_destination = second_self.layer1 / "04 References/04 guides/First.md"
    second_destination = second_self.layer1 / "04 References/04 guides/Second.md"
    _ensure_note(first, "First")
    _ensure_note(second, "Second")
    proposal = propose(
        second_self,
        {
            "operation": "move",
            "moves": [
                {"from": str(first), "to": str(first_destination)},
                {"from": str(second), "to": str(second_destination)},
            ],
        },
    )
    original_move = shutil.move
    moves = 0

    def fail_on_second_move(source: str, destination: str) -> str:
        nonlocal moves
        moves += 1
        if moves == 2:
            raise OSError("simulated second move failure")
        return original_move(source, destination)

    monkeypatch.setattr("second_self.broker.broker.shutil.move", fail_on_second_move)
    with pytest.raises(OSError, match="simulated second move failure"):
        approve(second_self, proposal["id"], "yes")

    assert first.exists()
    assert second.exists()
    assert not first_destination.exists()
    assert not second_destination.exists()


def test_multi_file_delete_failure_restores_sources_and_trash(
    second_self: SecondSelfPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = second_self.layer1 / "01 Capture/02 Notes/First.md"
    second = second_self.layer1 / "01 Capture/02 Notes/Second.md"
    _ensure_note(first, "First")
    _ensure_note(second, "Second")
    proposal = propose(
        second_self,
        {
            "operation": "delete",
            "paths": [str(first), str(second)],
        },
    )
    original_move = shutil.move
    moves = 0

    def fail_on_second_delete_move(source: str, destination: str) -> str:
        nonlocal moves
        moves += 1
        if moves == 2:
            raise OSError("simulated second delete failure")
        return original_move(source, destination)

    monkeypatch.setattr("second_self.broker.broker.shutil.move", fail_on_second_delete_move)
    with pytest.raises(OSError, match="simulated second delete failure"):
        approve(second_self, proposal["id"], "yes")

    assert first.exists()
    assert second.exists()
    assert not list(second_self.trash.rglob("First.md"))


@pytest.mark.parametrize("operation", ["migration", "link_fix"])
def test_multi_file_text_operation_failure_restores_every_original(
    second_self: SecondSelfPaths,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    first = second_self.layer1 / "01 Capture/02 Notes/First.md"
    second = second_self.layer1 / "01 Capture/02 Notes/Second.md"
    _ensure_note(first, "First")
    _ensure_note(second, "Second")
    originals = {first: first.read_text(encoding="utf-8"), second: second.read_text(encoding="utf-8")}
    if operation == "migration":
        specification = {
            "operation": operation,
            "changes": [
                {"path": str(first), "content": "# Migrated first"},
                {"path": str(second), "content": "# Migrated second"},
            ],
        }
    else:
        specification = {
            "operation": operation,
            "fixes": [
                {"path": str(first), "replacements": [{"old": "# First", "new": "# Fixed first"}]},
                {"path": str(second), "replacements": [{"old": "# Second", "new": "# Fixed second"}]},
            ],
        }
    proposal = propose(second_self, specification)
    original_write_text = Path.write_text
    writes = 0

    def fail_on_second_write(path: Path, data: str, *args: object, **kwargs: object) -> None:
        nonlocal writes
        if path in originals:
            writes += 1
            if writes == 2:
                raise OSError("simulated second text operation failure")
        original_write_text(path, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_on_second_write)
    with pytest.raises(OSError, match="simulated second text operation failure"):
        approve(second_self, proposal["id"], "yes")

    assert {path: path.read_text(encoding="utf-8") for path in originals} == originals


def test_export_failure_leaves_no_destination(
    second_self: SecondSelfPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = second_self.repo_root / "export.md"
    proposal = propose(
        second_self,
        {
            "operation": "export",
            "destination": str(destination),
            "content": "exported",
            "sources": [],
        },
    )
    original_write_text = Path.write_text

    def fail_export(path: Path, data: str, *args: object, **kwargs: object) -> None:
        if path == destination:
            raise OSError("simulated export failure")
        original_write_text(path, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_export)
    with pytest.raises(OSError, match="simulated export failure"):
        approve(second_self, proposal["id"], "yes")

    assert not destination.exists()


def test_proposal_binds_canonical_reviewed_payload(
    second_self: SecondSelfPaths,
) -> None:
    target = second_self.layer1 / "01 Capture/01 Current" / "Current Identity.md"
    _ensure_note(target, "Current Identity")

    proposal = propose(
        second_self,
        {
            "operation": "edit",
            "changes": [{"content": "# Updated", "path": str(target)}],
        },
    )

    assert proposal["schema"] == "second-self-broker-proposal"
    assert proposal["version"] == 1
    assert proposal["approval_digest"] == _approval_digest(proposal)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        (
            "specification",
            {"operation": "edit", "changes": []},
        ),
        ("input_hashes", {}),
        ("exact_preview", "tampered preview"),
    ],
)
def test_approval_rejects_tampered_bound_payload(
    second_self: SecondSelfPaths,
    field: str,
    replacement: object,
) -> None:
    target = second_self.layer1 / "01 Capture/01 Current" / "Current Strategy.md"
    _ensure_note(target, "Current Strategy")
    original = target.read_text(encoding="utf-8")
    proposal = propose(
        second_self,
        {
            "operation": "edit",
            "changes": [{"path": str(target), "content": "# replacement"}],
        },
    )
    proposal[field] = replacement
    proposal_path = _proposal_path(second_self, proposal["id"])
    proposal_path.write_text(json.dumps(proposal), encoding="utf-8")

    with pytest.raises(RuntimeError, match="integrity"):
        approve(second_self, proposal["id"], "yes")

    assert target.read_text(encoding="utf-8") == original
    assert not proposal_path.with_suffix(".lock").exists()


@pytest.mark.parametrize(
    ("field", "replacement"),
    [("schema", "other-schema"), ("version", 2)],
)
def test_approval_rejects_unsupported_proposal_schema(
    second_self: SecondSelfPaths,
    field: str,
    replacement: object,
) -> None:
    target = second_self.layer1 / "01 Capture/01 Current" / "Current Strategy.md"
    _ensure_note(target, "Current Strategy")
    proposal = propose(
        second_self,
        {
            "operation": "edit",
            "changes": [{"path": str(target), "content": "# replacement"}],
        },
    )
    proposal[field] = replacement
    proposal_path = _proposal_path(second_self, proposal["id"])
    proposal_path.write_text(json.dumps(proposal), encoding="utf-8")

    with pytest.raises(RuntimeError, match="schema"):
        approve(second_self, proposal["id"], "yes")


def test_approval_rejects_digestless_proposal_and_requires_reproposal(
    second_self: SecondSelfPaths,
) -> None:
    target = second_self.layer1 / "01 Capture/01 Current" / "Current Strategy.md"
    _ensure_note(target, "Current Strategy")
    original = target.read_text(encoding="utf-8")
    proposal = propose(
        second_self,
        {
            "operation": "edit",
            "changes": [{"path": str(target), "content": "# replacement"}],
        },
    )
    proposal.pop("approval_digest")
    _proposal_path(second_self, proposal["id"]).write_text(
        json.dumps(proposal), encoding="utf-8"
    )

    with pytest.raises(RuntimeError, match="Create a new proposal"):
        approve(second_self, proposal["id"], "yes")

    assert target.read_text(encoding="utf-8") == original


def test_approval_recomputes_exact_preview_before_apply(
    second_self: SecondSelfPaths,
) -> None:
    target = second_self.layer1 / "01 Capture/01 Current" / "Current Strategy.md"
    _ensure_note(target, "Current Strategy")
    original = target.read_text(encoding="utf-8")
    proposal = propose(
        second_self,
        {
            "operation": "edit",
            "changes": [{"path": str(target), "content": "# replacement"}],
        },
    )
    proposal["exact_preview"] = "fabricated reviewed preview"
    proposal["approval_digest"] = _approval_digest(proposal)
    _proposal_path(second_self, proposal["id"]).write_text(
        json.dumps(proposal), encoding="utf-8"
    )

    with pytest.raises(RuntimeError, match="exact preview"):
        approve(second_self, proposal["id"], "yes")

    assert target.read_text(encoding="utf-8") == original


def test_affirmative_approval_requires_exclusive_proposal_lock(
    second_self: SecondSelfPaths,
) -> None:
    target = second_self.layer1 / "01 Capture/01 Current" / "Current Strategy.md"
    _ensure_note(target, "Current Strategy")
    original = target.read_text(encoding="utf-8")
    proposal = propose(
        second_self,
        {
            "operation": "edit",
            "changes": [{"path": str(target), "content": "# replacement"}],
        },
    )
    lock = _proposal_path(second_self, proposal["id"]).with_suffix(".lock")
    lock.touch()

    with pytest.raises(RuntimeError, match="already active"):
        approve(second_self, proposal["id"], "yes")

    assert target.read_text(encoding="utf-8") == original


def test_digestless_proposal_can_still_be_explicitly_rejected(
    second_self: SecondSelfPaths,
) -> None:
    target = second_self.layer1 / "01 Capture/01 Current" / "Current Strategy.md"
    _ensure_note(target, "Current Strategy")
    proposal = propose(
        second_self,
        {
            "operation": "edit",
            "changes": [{"path": str(target), "content": "# replacement"}],
        },
    )
    proposal.pop("approval_digest")
    _proposal_path(second_self, proposal["id"]).write_text(
        json.dumps(proposal), encoding="utf-8"
    )

    rejected = approve(second_self, proposal["id"], "no")

    assert rejected["status"] == "rejected"


@pytest.mark.parametrize("confirmation", ["N", "n", "No", "NO", " no "])
def test_single_rejection_leaves_content_unchanged(
    second_self: SecondSelfPaths, confirmation: str
) -> None:
    target = second_self.layer1 / "01 Capture/01 Current" / "Current Identity.md"
    _ensure_note(target, "Current Identity")
    original = target.read_text(encoding="utf-8")
    proposal = propose(
        second_self,
        {
            "operation": "edit",
            "changes": [{"path": str(target), "content": "# replacement"}],
        },
    )

    rejected = approve(second_self, proposal["id"], confirmation)

    assert rejected["status"] == "rejected"
    assert target.read_text(encoding="utf-8") == original
    with pytest.raises(ValueError, match="rejected"):
        approve(second_self, proposal["id"], "yes")


@pytest.mark.parametrize("legacy_status", ["intent-pending", "exact-pending"])
def test_legacy_pending_proposal_accepts_one_simple_decision(
    second_self: SecondSelfPaths, legacy_status: str
) -> None:
    target = second_self.layer1 / "01 Capture/01 Current" / "Current Strategy.md"
    _ensure_note(target, "Current Strategy")
    proposal = propose(
        second_self,
        {
            "operation": "edit",
            "changes": [{"path": str(target), "content": "# Legacy updated"}],
        },
    )
    proposal["status"] = legacy_status
    proposal_path = second_self.audit / "proposals" / f"{proposal['id']}.json"
    proposal_path.write_text(json.dumps(proposal), encoding="utf-8")

    applied = approve(second_self, proposal["id"], "Y")

    assert applied["status"] == "applied"
    assert target.read_text(encoding="utf-8") == "# Legacy updated"


def test_stale_input_invalidates_approval(second_self: SecondSelfPaths) -> None:
    target = second_self.layer1 / "01 Capture/01 Current" / "Current Strategy.md"
    _ensure_note(target, "Current Strategy")
    proposal = propose(
        second_self,
        {
            "operation": "edit",
            "changes": [{"path": str(target), "content": "# replacement"}],
        },
    )
    target.write_text(target.read_text(encoding="utf-8") + "\nConcurrent edit.\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Stale approval"):
        approve(second_self, proposal["id"], "y")


def test_proposal_and_result_never_expose_absolute_private_root(
    second_self: SecondSelfPaths,
) -> None:
    target = second_self.layer1 / "01 Capture/01 Current" / "Current Strategy.md"
    _ensure_note(target, "Current Strategy")
    proposal = propose(
        second_self,
        {
            "operation": "edit",
            "changes": [
                {
                    "path": target.relative_to(second_self.data_root).as_posix(),
                    "content": target.read_text(encoding="utf-8") + "\nSafe.\n",
                }
            ],
        },
    )
    serialized = json.dumps(proposal)
    assert str(second_self.data_root) not in serialized
    assert "01-strategy-storage/01 Capture/01 Current/Current Strategy.md" in serialized

    applied = approve(second_self, proposal["id"], "yes", agent="pytest")
    assert str(second_self.data_root) not in json.dumps(applied)


def test_delete_moves_to_private_trash(second_self: SecondSelfPaths) -> None:
    target = second_self.layer1 / "01 Capture/02 Notes" / "Disposable.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("temporary", encoding="utf-8")
    proposal = propose(
        second_self,
        {"operation": "delete", "paths": [str(target.relative_to(second_self.data_root))]},
    )
    approve(second_self, proposal["id"], "y")
    assert not target.exists()
    assert list(second_self.trash.rglob("Disposable.md"))


def test_cli_broker_uses_one_simple_confirmation(
    second_self: SecondSelfPaths,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = second_self.layer1 / "01 Capture/01 Current" / "Current Strategy.md"
    _ensure_note(target, "Current Strategy")
    proposal = propose(
        second_self,
        {
            "operation": "edit",
            "changes": [{"path": str(target), "content": "# Updated"}],
        },
    )
    monkeypatch.setattr("second_self.cli.load_paths", lambda require_config=True: second_self)

    result = main(
        ["broker", "approve", proposal["id"], "--confirm", "Y", "--agent", "pytest"]
    )

    assert result == 0
    assert target.read_text(encoding="utf-8") == "# Updated"
    output = capsys.readouterr().out
    assert "APPROVE" not in output
    assert "APPLY " not in output


def test_single_approval_layer1_assembly(second_self: SecondSelfPaths) -> None:
    scaffold = second_self.repo_root / "01-strategy-storage"
    memory = scaffold / "00 Memory"
    memory.mkdir(parents=True)
    (memory / ".gitkeep").write_text("", encoding="utf-8")
    private_memory = second_self.layer1 / "00 Memory"
    private_memory.mkdir(parents=True, exist_ok=True)
    (private_memory / "Private.md").write_text("private", encoding="utf-8")

    proposal = propose(second_self, {"operation": "assemble_layer1"})
    approve(second_self, proposal["id"], "yes", agent="pytest")

    assert os.path.isjunction(scaffold)
    assert (scaffold / "00 Memory" / "Private.md").read_text(encoding="utf-8") == "private"
