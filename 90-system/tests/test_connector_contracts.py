"""Tests for DOC-002 provider-neutral connector contracts."""

import pytest

from second_self.connectors import (
    ConnectorItem,
    ConnectorKind,
    ConnectorRequest,
    ConnectorResult,
    ConnectorState,
)


def test_request_is_bounded_and_provider_scoped():
    request = ConnectorRequest(ConnectorKind.GMAIL, "from:team", limit=5)
    assert request.kind is ConnectorKind.GMAIL
    assert request.limit == 5


@pytest.mark.parametrize("limit", [0, 101])
def test_request_rejects_unbounded_limits(limit):
    with pytest.raises(ValueError, match="between 1 and 100"):
        ConnectorRequest(ConnectorKind.DRIVE, "architecture", limit=limit)


def test_result_preserves_source_attribution_without_credentials_or_paths():
    item = ConnectorItem(
        ConnectorKind.DRIVE,
        "file-1",
        "Architecture",
        "drive:item:file-1",
        {"mime_type": "text/markdown"},
    )
    result = ConnectorResult(ConnectorKind.DRIVE, ConnectorState.AVAILABLE, (item,))
    assert result.items[0].source_uri == "drive:item:file-1"
    assert "token" not in repr(result).casefold()
    assert "C:\\Users" not in repr(result)


def test_degraded_result_is_explicit_and_empty():
    result = ConnectorResult(
        ConnectorKind.GMAIL,
        ConnectorState.DEGRADED,
        message="provider unavailable; local recall remains available",
    )
    assert result.items == ()
    assert result.state is ConnectorState.DEGRADED


def test_credential_like_metadata_is_rejected():
    with pytest.raises(ValueError, match="credential-like"):
        ConnectorItem(
            ConnectorKind.GMAIL,
            "message-1",
            "Subject",
            "gmail:message:message-1",
            {"access_token": "redacted"},
        )
