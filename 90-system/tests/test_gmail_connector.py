"""Tests for the bounded Gmail metadata adapter."""

from second_self.connectors import ConnectorKind, ConnectorRequest, ConnectorState
from second_self.connectors.gmail import GmailConnector


class FakeRequest:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class FakeMessages:
    def __init__(self, listed, details):
        self.listed = listed
        self.details = details
        self.list_args = None
        self.get_args = []

    def list(self, **kwargs):
        self.list_args = kwargs
        return FakeRequest(self.listed)

    def get(self, **kwargs):
        self.get_args.append(kwargs)
        return FakeRequest(self.details[kwargs["id"]])


class FakeUsers:
    def __init__(self, messages):
        self._messages = messages

    def messages(self):
        return self._messages


class FakeService:
    def __init__(self, messages):
        self._users = FakeUsers(messages)

    def users(self):
        return self._users


def test_disabled_connector_refuses_provider_execution():
    called = False

    def service_factory():
        nonlocal called
        called = True
        return None

    result = GmailConnector(service_factory, enabled=False).search(
        ConnectorRequest(ConnectorKind.GMAIL, "from:team", limit=5)
    )

    assert result.state is ConnectorState.DISABLED
    assert result.items == ()
    assert called is False


def test_search_maps_bounded_metadata_and_never_returns_body():
    messages = FakeMessages(
        {"messages": [{"id": "m1"}, {"id": "m2"}]},
        {
            "m1": {
                "id": "m1",
                "threadId": "t1",
                "labelIds": ["INBOX"],
                "internalDate": "1700000000000",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Hello"},
                        {"name": "From", "value": "team@example.test"},
                    ]
                },
                "snippet": "must not escape",
            },
            "m2": {"id": "m2", "payload": {"headers": []}},
        },
    )
    result = GmailConnector(lambda: FakeService(messages), enabled=True).search(
        ConnectorRequest(ConnectorKind.GMAIL, "from:team", limit=2)
    )

    assert result.state is ConnectorState.AVAILABLE
    assert [item.item_id for item in result.items] == ["m1", "m2"]
    assert result.items[0].metadata == {
        "from": "team@example.test",
        "internal_date": "1700000000000",
        "labels": "INBOX",
        "subject": "Hello",
        "thread_id": "t1",
    }
    assert "snippet" not in result.items[0].metadata
    assert messages.list_args == {
        "userId": "me",
        "q": "from:team",
        "maxResults": 2,
        "includeSpamTrash": False,
    }
    assert all(call["format"] == "metadata" for call in messages.get_args)
    assert all("metadataHeaders" in call for call in messages.get_args)


def test_provider_failure_is_redacted_and_returns_no_items():
    def service_factory():
        raise RuntimeError("access_token=secret-value provider body")

    result = GmailConnector(service_factory, enabled=True).search(
        ConnectorRequest(ConnectorKind.GMAIL, "subject:hello")
    )

    assert result.state is ConnectorState.UNAVAILABLE
    assert result.items == ()
    assert "secret-value" not in result.message
    assert "access_token" not in result.message


def test_malformed_provider_payload_degrades_without_content():
    messages = FakeMessages({"messages": [{"unexpected": "shape"}]}, {})

    result = GmailConnector(lambda: FakeService(messages), enabled=True).search(
        ConnectorRequest(ConnectorKind.GMAIL, "subject:hello")
    )

    assert result.state is ConnectorState.DEGRADED
    assert result.items == ()
