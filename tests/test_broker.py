import json
from pathlib import Path

import pytest

from main_brain.broker import approve_exact, approve_intent, propose
from main_brain.paths import BrainPaths


def test_two_stage_edit_and_audit(brain: BrainPaths) -> None:
    target = brain.layer1 / "10-current" / "Current Identity.md"
    updated = target.read_text(encoding="utf-8") + "\nApproved value.\n"
    proposal = propose(
        brain,
        {
            "operation": "edit",
            "changes": [
                {
                    "path": str(target.relative_to(brain.data_root)),
                    "content": updated,
                }
            ],
        },
    )
    with pytest.raises(PermissionError):
        approve_intent(brain, proposal["id"], "yes")
    approve_intent(brain, proposal["id"], f"APPROVE INTENT {proposal['id']}")
    approve_exact(brain, proposal["id"], f"APPLY {proposal['id']}", agent="pytest")
    assert "Approved value." in target.read_text(encoding="utf-8")
    audit = (brain.audit / "agent-edits.jsonl").read_text(encoding="utf-8")
    assert '"agent": "pytest"' in audit


def test_stale_input_invalidates_approval(brain: BrainPaths) -> None:
    target = brain.layer1 / "10-current" / "Current Strategy.md"
    proposal = propose(
        brain,
        {
            "operation": "edit",
            "changes": [{"path": str(target), "content": "# replacement"}],
        },
    )
    approve_intent(brain, proposal["id"], f"APPROVE INTENT {proposal['id']}")
    target.write_text(target.read_text(encoding="utf-8") + "\nConcurrent edit.\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Stale approval"):
        approve_exact(brain, proposal["id"], f"APPLY {proposal['id']}")


def test_delete_moves_to_private_trash(brain: BrainPaths) -> None:
    target = brain.layer1 / "20-notes" / "Disposable.md"
    target.write_text("temporary", encoding="utf-8")
    proposal = propose(
        brain,
        {"operation": "delete", "paths": [str(target.relative_to(brain.data_root))]},
    )
    approve_intent(brain, proposal["id"], f"APPROVE INTENT {proposal['id']}")
    approve_exact(brain, proposal["id"], f"APPLY {proposal['id']}")
    assert not target.exists()
    assert list(brain.trash.rglob("Disposable.md"))

