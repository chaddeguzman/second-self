"""Tests for the bounded, read-only Drive metadata adapter."""

from second_self.connectors import ConnectorKind, ConnectorRequest, ConnectorState
from second_self.connectors.drive import DriveConnector


class FakeRequest:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class FakeFiles:
    def __init__(self, listed):
        self.listed = listed
        self.list_args = None
        self.download_called = False

    def list(self, **kwargs):
        self.list_args = kwargs
        return FakeRequest(self.listed)

    def get_media(self, **kwargs):
        self.download_called = True
        raise AssertionError("Drive content download must not be used")


class FakeService:
    def __init__(self, files):
        self._files = files

    def files(self):
        return self._files


def test_disabled_connector_refuses_provider_execution():
    called = False

    def service_factory():
        nonlocal called
        called = True
        return None

    result = DriveConnector(service_factory, enabled=False).search(
        ConnectorRequest(ConnectorKind.DRIVE, "name contains 'plan'", limit=5)
    )

    assert result.state is ConnectorState.DISABLED
    assert result.items == ()
    assert called is False


def test_search_maps_bounded_metadata_without_content_download():
    files = FakeFiles(
        {
            "files": [
                {
                    "id": "file-1",
                    "name": "Plan",
                    "mimeType": "text/markdown",
                    "modifiedTime": "2026-09-23T10:00:00Z",
                    "webViewLink": "https://drive.google.com/open?id=file-1",
                    "size": "42",
                    "parents": ["folder-1"],
                    "description": "must not escape",
                }
            ]
        }
    )
    result = DriveConnector(lambda: FakeService(files), enabled=True).search(
        ConnectorRequest(ConnectorKind.DRIVE, "name contains 'plan'", limit=1)
    )

    assert result.state is ConnectorState.AVAILABLE
    assert result.items[0].item_id == "file-1"
    assert result.items[0].title == "Plan"
    assert result.items[0].metadata == {
        "mime_type": "text/markdown",
        "modified_time": "2026-09-23T10:00:00Z",
        "parents": "folder-1",
        "size": "42",
    }
    assert "description" not in result.items[0].metadata
    assert files.list_args == {
        "q": "name contains 'plan'",
        "pageSize": 1,
        "spaces": "drive",
        "includeItemsFromAllDrives": False,
        "supportsAllDrives": False,
        "fields": "files(id,name,mimeType,modifiedTime,webViewLink,size,parents)",
    }
    assert files.download_called is False


def test_provider_failure_is_redacted_and_returns_no_items():
    def service_factory():
        raise RuntimeError("access_token=secret-value provider body")

    result = DriveConnector(service_factory, enabled=True).search(
        ConnectorRequest(ConnectorKind.DRIVE, "name contains 'x'")
    )

    assert result.state is ConnectorState.UNAVAILABLE
    assert result.items == ()
    assert "secret-value" not in result.message
    assert "access_token" not in result.message


def test_oversized_query_is_rejected_before_provider_execution():
    called = False

    def service_factory():
        nonlocal called
        called = True
        return None

    result = DriveConnector(service_factory, enabled=True).search(
        ConnectorRequest(ConnectorKind.DRIVE, "x" * 2049)
    )

    assert result.state is ConnectorState.DEGRADED
    assert result.items == ()
    assert "query" in result.message.casefold()
    assert called is False


def test_malformed_provider_payload_degrades_without_content():
    files = FakeFiles({"files": [{"unexpected": "shape"}]})

    result = DriveConnector(lambda: FakeService(files), enabled=True).search(
        ConnectorRequest(ConnectorKind.DRIVE, "name contains 'x'")
    )

    assert result.state is ConnectorState.DEGRADED
    assert result.items == ()
