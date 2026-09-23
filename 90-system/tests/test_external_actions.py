"""Tests for the disabled, approval-gated external action contract."""

from datetime import datetime, timedelta, timezone

import pytest

from second_self.external_actions import (
    ActionApproval,
    ActionAudit,
    ActionKind,
    ActionRequest,
    ActionStatus,
    allowed_scopes,
)

NOW = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)
PAYLOAD_DIGEST = "a" * 64


def _request(**overrides):
    values = {
        "request_id": "request-1",
        "kind": ActionKind.DRAFT_EMAIL,
        "scope": "email.draft",
        "target": "recipient@example.test",
        "payload_digest": PAYLOAD_DIGEST,
        "preview": "Draft email to recipient@example.test",
    }
    values.update(overrides)
    return ActionRequest(**values)


def test_action_request_is_typed_bounded_and_execution_free():
    request = _request()

    assert request.status is ActionStatus.PENDING
    assert request.as_dict()["payload_digest"] == PAYLOAD_DIGEST
    assert allowed_scopes(ActionKind.DRAFT_EMAIL) == ("email.draft",)
    assert not hasattr(request, "execute")


@pytest.mark.parametrize(
    "overrides",
    [
        {"kind": "send_email"},
        {"scope": "email.send"},
        {"payload_digest": "not-a-digest"},
        {"preview": ""},
        {"target": "x" * 513},
    ],
)
def test_invalid_requests_fail_closed(overrides):
    with pytest.raises(ValueError):
        _request(**overrides)


def test_approval_binds_exact_request_and_expires():
    approval = ActionApproval(
        request_id="request-1",
        kind=ActionKind.DRAFT_EMAIL,
        scope="email.draft",
        payload_digest=PAYLOAD_DIGEST,
        approved_by="Chad",
        approved_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
    )

    assert approval.is_valid_for(_request(), now=NOW + timedelta(minutes=4))
    assert not approval.is_valid_for(
        _request(payload_digest="b" * 64), now=NOW + timedelta(minutes=4)
    )
    assert not approval.is_valid_for(_request(), now=NOW + timedelta(minutes=5))


def test_audit_record_contains_metadata_only():
    audit = ActionAudit(
        request_id="request-1",
        kind=ActionKind.UPLOAD_FILE,
        scope="drive.upload",
        payload_digest=PAYLOAD_DIGEST,
        status=ActionStatus.APPROVAL_REQUIRED,
        actor="ECHO",
        recorded_at=NOW,
    )

    payload = audit.as_dict()
    assert payload["status"] == "approval_required"
    assert "content" not in payload
    assert "token" not in repr(payload).casefold()
