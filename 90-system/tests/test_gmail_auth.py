"""Tests for the Gmail OAuth and keyring boundary."""

import json
from pathlib import Path

import pytest

from second_self.connectors.gmail_auth import (
    GMAIL_READONLY_SCOPE,
    GmailAuthError,
    GmailCredentialStore,
    authorize_gmail,
    load_gmail_credentials,
    redact_auth_error,
)


class FakeKeyring:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.values.get((service, username))

    def set_password(self, service: str, username: str, value: str) -> None:
        self.values[(service, username)] = value

    def delete_password(self, service: str, username: str) -> None:
        self.values.pop((service, username), None)


def test_credential_store_round_trip_uses_keyring_only():
    keyring = FakeKeyring()
    store = GmailCredentialStore(keyring_backend=keyring)

    store.save({"refresh_token": "synthetic-refresh", "scopes": [GMAIL_READONLY_SCOPE]})

    assert store.load() == {
        "refresh_token": "synthetic-refresh",
        "scopes": [GMAIL_READONLY_SCOPE],
    }
    assert "synthetic-refresh" not in str(store)
    assert "synthetic-refresh" not in redact_auth_error("token=synthetic-refresh")


def test_load_credentials_requires_read_only_scope(tmp_path: Path):
    keyring = FakeKeyring()
    store = GmailCredentialStore(keyring_backend=keyring)
    store.save({"refresh_token": "synthetic", "scopes": ["gmail.modify"]})

    with pytest.raises(GmailAuthError, match="read-only"):
        load_gmail_credentials(store)


def test_authorize_requires_existing_client_configuration(tmp_path: Path):
    with pytest.raises(GmailAuthError, match="configuration unavailable"):
        authorize_gmail(tmp_path / "missing-client.json", GmailCredentialStore(FakeKeyring()))


def test_authorize_rejects_write_capable_flow_scope(tmp_path: Path):
    client = tmp_path / "client.json"
    client.write_text(json.dumps({"installed": {"client_id": "synthetic"}}), encoding="utf-8")

    with pytest.raises(GmailAuthError, match="read-only"):
        authorize_gmail(
            client,
            GmailCredentialStore(FakeKeyring()),
            scopes=("https://www.googleapis.com/auth/gmail.modify",),
        )
