"""Tests for the Drive OAuth/keyring boundary."""

import pytest

from second_self.connectors.drive_auth import (
    DRIVE_READONLY_SCOPE,
    DriveAuthError,
    DriveCredentialStore,
    _validate_scopes,
)


class FakeKeyring:
    def __init__(self):
        self.values = {}

    def get_password(self, service, username):
        return self.values.get((service, username))

    def set_password(self, service, username, value):
        self.values[(service, username)] = value

    def delete_password(self, service, username):
        self.values.pop((service, username), None)


def test_drive_credentials_are_stored_in_the_injected_keyring():
    keyring = FakeKeyring()
    store = DriveCredentialStore(keyring)
    payload = {"refresh_token": "synthetic", "scopes": [DRIVE_READONLY_SCOPE]}

    store.save(payload)

    assert store.load() == payload
    assert keyring.values[("second-self.drive", "oauth")].find("synthetic") >= 0


def test_drive_scope_is_exactly_read_only():
    assert _validate_scopes((DRIVE_READONLY_SCOPE,)) == (DRIVE_READONLY_SCOPE,)
    with pytest.raises(DriveAuthError, match="only the Drive read-only scope"):
        _validate_scopes(("https://www.googleapis.com/auth/drive",))


def test_invalid_stored_credentials_fail_closed():
    keyring = FakeKeyring()
    store = DriveCredentialStore(keyring)
    keyring.set_password("second-self.drive", "oauth", "not-json")

    with pytest.raises(DriveAuthError, match="stored Drive credentials are invalid"):
        store.load()
