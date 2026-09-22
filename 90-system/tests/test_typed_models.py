from __future__ import annotations

import pytest

from second_self.broker.models import BrokerProposal, BrokerSpecification, BrokerResult
from second_self.wiki.models import WikiProposal, WikiResult


def test_broker_specification_rejects_unknown_operation_and_malformed_changes():
    with pytest.raises(ValueError, match="unsupported operation"):
        BrokerSpecification.from_payload({"operation": "format_disk"})
    with pytest.raises(ValueError, match="changes must be a list"):
        BrokerSpecification.from_payload({"operation": "edit", "changes": "bad"})


def test_broker_proposal_serializes_only_stable_public_fields():
    proposal = BrokerProposal.from_payload(
        {
            "id": "proposal-1",
            "created": "2026-09-22T00:00:00+08:00",
            "status": "approval-pending",
            "schema": "second-self-broker-proposal",
            "version": 1,
            "specification": {"operation": "edit", "changes": []},
            "input_hashes": {"01-strategy-storage/Note.md": "abc"},
            "exact_preview": "edit 0 files",
            "approval_digest": "digest",
        }
    )
    assert proposal.specification.operation == "edit"
    assert "approval_digest" not in BrokerResult("applied", ("Note.md",)).as_dict()
    assert proposal.as_dict()["specification"]["operation"] == "edit"


def test_wiki_proposal_rejects_non_string_content_and_serializes_result():
    with pytest.raises(ValueError, match="content must be a string"):
        WikiProposal.from_payload(
            {"operation": "wiki_process", "changes": [{"path": "03-wiki/a.md", "content": 3}]}
        )
    result = WikiResult("applied", ("03-wiki/a.md",), 1)
    assert result.as_dict() == {
        "status": "applied",
        "changed_paths": ["03-wiki/a.md"],
        "changed_count": 1,
    }
