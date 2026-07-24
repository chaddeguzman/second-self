import json
import os
from pathlib import Path

import pytest

from second_self.broker import approve, propose
from second_self.cli import main
from second_self.paths import SecondSelfPaths


@pytest.mark.parametrize("confirmation", ["Y", "y", "Yes", "YES", " yes "])
def test_single_approval_edit_and_audit(
    second_self: SecondSelfPaths, confirmation: str
) -> None:
    target = second_self.layer1 / "10-current" / "Current Identity.md"
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


@pytest.mark.parametrize("confirmation", ["N", "n", "No", "NO", " no "])
def test_single_rejection_leaves_content_unchanged(
    second_self: SecondSelfPaths, confirmation: str
) -> None:
    target = second_self.layer1 / "10-current" / "Current Identity.md"
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
    target = second_self.layer1 / "10-current" / "Current Strategy.md"
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
    target = second_self.layer1 / "10-current" / "Current Strategy.md"
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
    target = second_self.layer1 / "10-current" / "Current Strategy.md"
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
    assert "01-strategy-storage/10-current/Current Strategy.md" in serialized

    applied = approve(second_self, proposal["id"], "yes", agent="pytest")
    assert str(second_self.data_root) not in json.dumps(applied)


def test_delete_moves_to_private_trash(second_self: SecondSelfPaths) -> None:
    target = second_self.layer1 / "20-notes" / "Disposable.md"
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
    target = second_self.layer1 / "10-current" / "Current Strategy.md"
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


@pytest.mark.skipif(os.name != "nt", reason="Windows junction behavior")
def test_single_approval_layer1_assembly(second_self: SecondSelfPaths) -> None:
    scaffold = second_self.repo_root / "01-strategy-storage"
    memory = scaffold / "00 Memory"
    memory.mkdir(parents=True)
    (memory / ".gitkeep").write_text("", encoding="utf-8")
    private_memory = second_self.layer1 / "00 Memory"
    private_memory.mkdir(parents=True)
    (private_memory / "Private.md").write_text("private", encoding="utf-8")

    proposal = propose(second_self, {"operation": "assemble_layer1"})
    approve(second_self, proposal["id"], "yes", agent="pytest")

    assert os.path.isjunction(scaffold)
    assert (scaffold / "00 Memory" / "Private.md").read_text(encoding="utf-8") == "private"
