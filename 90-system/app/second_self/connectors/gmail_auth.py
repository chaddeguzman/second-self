"""Fail-closed Gmail OAuth and operating-system keyring helpers."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_KEYRING_SERVICE = "second-self.gmail"
GMAIL_KEYRING_USERNAME = "oauth"


class _KeyringBackend(Protocol):
    def get_password(self, service: str, username: str) -> str | None: ...

    def set_password(self, service: str, username: str, value: str) -> None: ...

    def delete_password(self, service: str, username: str) -> None: ...


class GmailAuthError(RuntimeError):
    """Safe public authentication failure without provider payloads."""


def redact_auth_error(_: object) -> str:
    return "Gmail authentication failed; reauthorization may be required."


def _keyring() -> _KeyringBackend:
    try:
        import keyring
    except ImportError as exc:  # pragma: no cover - depends on optional profile
        raise GmailAuthError("OS keyring support is unavailable") from exc
    return keyring  # type: ignore[return-value]


class GmailCredentialStore:
    """Persist OAuth material in the OS keyring, never in repository files."""

    def __init__(
        self,
        keyring_backend: _KeyringBackend | None = None,
        *,
        service: str = GMAIL_KEYRING_SERVICE,
        username: str = GMAIL_KEYRING_USERNAME,
    ) -> None:
        self._keyring = keyring_backend or _keyring()
        self._service = service
        self._username = username

    def load(self) -> dict[str, Any] | None:
        value = self._keyring.get_password(self._service, self._username)
        if not value:
            return None
        try:
            payload = json.loads(value)
        except (TypeError, ValueError) as exc:
            raise GmailAuthError("stored Gmail credentials are invalid") from exc
        if not isinstance(payload, dict):
            raise GmailAuthError("stored Gmail credentials are invalid")
        return payload

    def save(self, payload: Mapping[str, Any]) -> None:
        self._keyring.set_password(
            self._service,
            self._username,
            json.dumps(dict(payload), sort_keys=True),
        )

    def delete(self) -> None:
        try:
            self._keyring.delete_password(self._service, self._username)
        except Exception:
            return


def _validate_scopes(scopes: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(str(scope) for scope in scopes))
    if normalized != (GMAIL_READONLY_SCOPE,):
        raise GmailAuthError("only the Gmail read-only scope is permitted")
    return normalized


def _credentials_from_payload(payload: Mapping[str, Any]) -> Any:
    scopes = _validate_scopes(payload.get("scopes", ()))
    try:
        from google.oauth2.credentials import Credentials

        return Credentials(
            token=payload.get("token"),
            refresh_token=payload.get("refresh_token"),
            token_uri=payload.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=payload.get("client_id"),
            client_secret=payload.get("client_secret"),
            scopes=scopes,
        )
    except ImportError as exc:  # pragma: no cover - depends on optional profile
        raise GmailAuthError("Google OAuth support is unavailable") from exc
    except Exception as exc:
        raise GmailAuthError(redact_auth_error(exc)) from exc


def load_gmail_credentials(store: GmailCredentialStore) -> Any:
    payload = store.load()
    if payload is None:
        raise GmailAuthError("Gmail credentials are not configured")
    return _credentials_from_payload(payload)


def _credentials_payload(credentials: Any, scopes: Sequence[str]) -> dict[str, Any]:
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(_validate_scopes(scopes)),
    }


def authorize_gmail(
    client_config: Path,
    store: GmailCredentialStore,
    *,
    scopes: Sequence[str] = (GMAIL_READONLY_SCOPE,),
    flow_factory: Any | None = None,
) -> Any:
    """Run explicit local OAuth consent and save the refresh credential."""

    validated_scopes = _validate_scopes(scopes)
    if not client_config.is_file():
        raise GmailAuthError("Gmail OAuth client configuration unavailable")
    try:
        json.loads(client_config.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GmailAuthError("Gmail OAuth client configuration unavailable") from exc

    try:
        existing = store.load()
        if existing is not None:
            credentials = _credentials_from_payload(existing)
            if credentials.valid:
                return credentials
            if credentials.expired and credentials.refresh_token:
                from google.auth.transport.requests import Request

                credentials.refresh(Request())
                store.save(_credentials_payload(credentials, validated_scopes))
                return credentials

        if flow_factory is None:
            from google_auth_oauthlib.flow import InstalledAppFlow

            flow_factory = InstalledAppFlow.from_client_secrets_file
        flow = flow_factory(str(client_config), scopes=validated_scopes)
        credentials = flow.run_local_server(port=0)
        store.save(_credentials_payload(credentials, validated_scopes))
        return credentials
    except GmailAuthError:
        raise
    except Exception as exc:
        raise GmailAuthError(redact_auth_error(exc)) from exc
