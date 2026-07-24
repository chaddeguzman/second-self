import json
import os
from pathlib import Path

import pytest

from second_self.broker import approve_exact, approve_intent, propose
from second_self.paths import SecondSelfPaths


def test_two_stage_edit_and_audit(second_self: SecondSelfPaths) -> None:
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
        approve_intent(second_self, proposal["id"], "yes")
    approve_intent(second_self, proposal["id"], f"APPROVE INTENT {proposal['id']}")
    approve_exact(second_self, proposal["id"], f"APPLY {proposal['id']}", agent="pytest")
    assert "Approved value." in target.read_text(encoding="utf-8")
    audit = (second_self.audit / "agent-edits.jsonl").read_text(encoding="utf-8")
    assert '"agent": "pytest"' in audit


def test_stale_input_invalidates_approval(second_self: SecondSelfPaths) -> None:
    target = second_self.layer1 / "10-current" / "Current Strategy.md"
    proposal = propose(
        second_self,
        {
            "operation": "edit",
            "changes": [{"path": str(target), "content": "# replacement"}],
        },
    )
    approve_intent(second_self, proposal["id"], f"APPROVE INTENT {proposal['id']}")
    target.write_text(target.read_text(encoding="utf-8") + "\nConcurrent edit.\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Stale approval"):
        approve_exact(second_self, proposal["id"], f"APPLY {proposal['id']}")


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

    approve_intent(second_self, proposal["id"], f"APPROVE INTENT {proposal['id']}")
    applied = approve_exact(
        second_self, proposal["id"], f"APPLY {proposal['id']}", agent="pytest"
    )
    assert str(second_self.data_root) not in json.dumps(applied)


def test_delete_moves_to_private_trash(second_self: SecondSelfPaths) -> None:
    target = second_self.layer1 / "20-notes" / "Disposable.md"
    target.write_text("temporary", encoding="utf-8")
    proposal = propose(
        second_self,
        {"operation": "delete", "paths": [str(target.relative_to(second_self.data_root))]},
    )
    approve_intent(second_self, proposal["id"], f"APPROVE INTENT {proposal['id']}")
    approve_exact(second_self, proposal["id"], f"APPLY {proposal['id']}")
    assert not target.exists()
    assert list(second_self.trash.rglob("Disposable.md"))


@pytest.mark.skipif(os.name != "nt", reason="Windows junction behavior")
def test_two_stage_layer1_assembly(second_self: SecondSelfPaths) -> None:
    scaffold = second_self.repo_root / "01-strategy-storage"
    memory = scaffold / "00 Memory"
    memory.mkdir(parents=True)
    (memory / ".gitkeep").write_text("", encoding="utf-8")
    private_memory = second_self.layer1 / "00 Memory"
    private_memory.mkdir(parents=True)
    (private_memory / "Private.md").write_text("private", encoding="utf-8")

    proposal = propose(second_self, {"operation": "assemble_layer1"})
    approve_intent(second_self, proposal["id"], f"APPROVE INTENT {proposal['id']}")
    approve_exact(second_self, proposal["id"], f"APPLY {proposal['id']}", agent="pytest")

    assert os.path.isjunction(scaffold)
    assert (scaffold / "00 Memory" / "Private.md").read_text(encoding="utf-8") == "private"
